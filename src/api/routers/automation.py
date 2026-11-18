"""
Muse 自动化接口：给本机 CLI（src/cli/automation.py，命令名 translation-agent）用。

挂在 /internal/automation 下，不在 /api 下：nginx 只把 /api/、/ws/ 转给后端，公网到不了这里；
接口本身再拒绝一切带转发头或不是本机来的请求。凭证只在这个进程里用，响应里从不出现。

- updates：先同步（Substack 最新一页 + Slack 只读同步），再查 since 之后的新文章和 @我。
  不导入、不翻译、不改 Slack 和 momo 本地的已读。
- translate-article：导入（已导入复用）→ 起四步法翻译（自动采用术语建议）；在跑 / 已译完就返回已有项目。
- status / health：只读。
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking
from src.services.substack_service import SubstackError, article_key
from src.settings import settings

from ..dependencies import get_batch_service, get_longform_llm_provider, get_project_manager, \
    get_translation_status_service
from ..middleware import APIException, NotFoundException
from .confirmation_translation import start_longform_workflow
from .slack_inbox import get_slack_inbox
from .substack import (
    _imported_projects,
    _to_api_error,
    _translation_state,
    get_substack_client,
    get_substack_library,
    import_substack_article,
)
from .translate_models import LongformWorkflowStartRequest

logger = logging.getLogger(__name__)

_FORWARD_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded", "cf-connecting-ip")


def require_local(request: Request) -> None:
    """只接本机直连：经过 nginx / Cloudflare 的请求都带转发头。"""
    host = request.client.host if request.client else ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host in {"localhost", "testclient"}  # TestClient 的 client.host 是 testclient
    if not local or any(h in request.headers for h in _FORWARD_HEADERS):
        raise APIException(status_code=403, detail="只允许本机调用", error_code="FORBIDDEN")


router = APIRouter(prefix="/internal/automation", dependencies=[Depends(require_local)])

# 同一篇文章同时只处理一次 translate-article，避免并发调用导入出两个项目
_translate_lock = asyncio.Lock()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_post_date(value: str) -> float:
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _group_ids() -> List[str]:
    return [g.strip() for g in settings.automation_slack_group_ids.split(",") if g.strip()]


def _article_link(project_id: str) -> str:
    return f"{settings.automation_public_url.rstrip('/')}/articles/{project_id}"


# ---------------------------------------------------------------- updates


@router.get("/updates")
async def updates(since: float = Query(..., ge=0)):
    # 先记时间再同步：同步期间新到的内容 ts 晚于水位线，下次还会返回，不会漏
    started_at = time.time()
    errors: Dict[str, str] = {}

    library = get_substack_library()
    articles: List[Dict[str, Any]] = []
    try:
        await run_blocking(library.ensure_synced)
        await run_blocking(library.sync)
    except SubstackError as error:
        errors["substack"] = error.message  # 同步失败照样从本地清单里查
    library.start_digest_worker()
    pm = get_project_manager()
    imported, variants = await asyncio.to_thread(_imported_projects, pm)
    for post in await asyncio.to_thread(library.posts):
        if _parse_post_date(post.post_date) <= since:
            break  # posts() 按发布时间从新到旧
        project = imported.get(article_key(post.url) or "")
        status, project_id = "not_imported", None
        if project is not None:
            status, _ = await asyncio.to_thread(
                _translation_state, pm, project.id, variants.get(project.id, []), project.primary_target)
            project_id = project.id if status != "not_imported" else None
        articles.append({
            "slug": post.slug,
            "title": post.title,
            "zh_title": post.zh_title,
            "zh_summary": post.zh_summary,
            "url": post.url,
            "published_at": post.post_date,
            "paid": post.is_paid,
            "word_count": post.wordcount,
            "status": status,
            "project_id": project_id,
        })

    inbox = get_slack_inbox()
    mentions: List[Dict[str, Any]] = []
    try:
        if inbox.store.load() is None:
            errors["slack"] = "还没有配置 Slack 凭证"
        else:
            await run_blocking(inbox.sync_all)
            mentions = await run_blocking(inbox.mentions_since, since, _group_ids())
    except Exception as error:  # SlackInboxError 及网络错误：只影响 mentions，文章照常返回
        logger.warning("automation updates: Slack 失败：%s", error)
        errors["slack"] = getattr(error, "message", None) or type(error).__name__
        # 拿不到最新的就别推进水位线，下次从同一个 since 再查（文章会重复出现，Muse 按 slug 去重）
        started_at = since

    result: Dict[str, Any] = {
        "new_articles": articles,
        "mentions": mentions,
        "watermark": _iso(max(started_at, since)),
    }
    if errors:
        result["warnings"] = errors
    return result


# ---------------------------------------------------------------- translate-article


class TranslateArticleRequest(BaseModel):
    article: str = Field(..., min_length=1, max_length=2000)  # slug 或 Substack 文章链接
    target_lang: str = Field("zh", max_length=10)


def _resolve_article_url(article: str) -> str:
    if article.startswith(("http://", "https://")):
        return article
    library = get_substack_library()
    for post in library.posts():
        if post.slug == article:
            return post.url
    library.sync()  # 可能是刚发的，清单里还没有
    for post in library.posts():
        if post.slug == article:
            return post.url
    raise NotFoundException(detail=f"文章库里没有 slug 为 {article} 的文章")


@router.post("/translate-article")
async def translate_article(request: Request, body: TranslateArticleRequest):
    if body.target_lang != "zh":
        raise APIException(status_code=400, detail="目前只支持翻译成中文（zh）", error_code="BAD_REQUEST")
    async with _translate_lock:
        try:
            url = await run_blocking(_resolve_article_url, body.article.strip())
        except SubstackError as error:
            raise _to_api_error(error) from error
        pm = get_project_manager()
        project, _already = await import_substack_article(pm, get_substack_client(), url)
        project_id = project.id
        summaries = await asyncio.to_thread(pm.list_summaries, include_variants=True)
        summary = next((s for s in summaries if s.id == project_id), None)
        variant_ids = [s.id for s in summaries if s.variant_of == project_id]
        state, progress = await asyncio.to_thread(
            _translation_state, pm, project_id, variant_ids, summary.primary_target if summary else None)
        result = {"project_id": project_id, "article": project.title, "url": _article_link(project_id)}
        if state in {"translating", "awaiting_terms", "translated"}:
            return {**result, "status": "already_exists", "translation_status": state, "progress": progress}

        try:
            started = await start_longform_workflow.__wrapped__(  # 绕过网页用的 3 次/分钟限流，并发由上面的锁管
                request=request,
                project_id=project_id,
                service=get_batch_service(),
                body=LongformWorkflowStartRequest(method="four-step", auto_accept_terms=True),
            )
        except APIException as error:
            if error.status_code == 409:  # 刚好有人在网页上点了开始
                return {**result, "status": "already_exists", "translation_status": "translating",
                        "progress": progress}
            raise
        return {**result, "status": "resumed" if started.get("resumed") else "started",
                "run_id": started.get("run_id")}


# ---------------------------------------------------------------- status


def _last_error(payload: Dict[str, Any]) -> Optional[str]:
    errors = payload.get("errors") or []
    if errors and isinstance(errors[-1], dict):
        return str(errors[-1].get("error") or "")[:500] or None
    return None


@router.get("/projects/{project_id}/status")
async def project_status(project_id: str, with_markdown: bool = False):
    pm = get_project_manager()
    summaries = await asyncio.to_thread(pm.list_summaries, include_variants=True)
    summary = next((s for s in summaries if s.id == project_id), None)
    if summary is None:
        raise NotFoundException(detail="Project not found")
    variant_ids = [s.id for s in summaries if s.variant_of == project_id]
    state, progress = await asyncio.to_thread(
        _translation_state, pm, project_id, variant_ids, summary.primary_target)
    payload = await get_translation_status_service().get_translation_progress(project_id)

    if state in {"translating", "awaiting_terms"}:
        status = "running"
    elif state == "translated":
        status = "done"
    elif payload.get("status") in {"failed", "cancelled", "incomplete"} or state == "partial":
        status = "failed"
    else:
        status = "not_started"

    post = None
    key = article_key(summary.original_url)
    if key:
        post = next((p for p in get_substack_library().posts() if article_key(p.url) == key), None)
    result: Dict[str, Any] = {
        "project_id": project_id,
        "status": status,
        "progress": progress,
        "stage": payload.get("current_step") if status == "running" else None,
        "title": summary.title,
        "zh_title": post.zh_title if post else "",
        "zh_summary": post.zh_summary if post else "",
        "result": _article_link(project_id) if status == "done" else None,
        "error": None,
    }
    if status == "failed":
        result["error"] = _last_error(payload) or f"翻译停在 {progress}%（状态 {payload.get('status') or state}）"
    if status == "done" and with_markdown:
        try:
            result["markdown"] = await run_blocking(pm.export, project_id, format="zh")
        except ValueError as error:
            result["markdown_error"] = str(error)
    return result


# ---------------------------------------------------------------- health


@router.get("/health")
async def health():
    checks: Dict[str, str] = {}

    client = get_substack_client()
    if not await asyncio.to_thread(client.cookie_store.is_configured):
        checks["substack"] = "cookie_missing"
    else:
        try:
            await run_blocking(client.list_archive, cursor=None, limit=1)
            checks["substack"] = "ok"
        except SubstackError as error:
            checks["substack"] = f"error: {error.code}"

    status = await run_blocking(get_slack_inbox().status)
    checks["slack"] = "ok" if status.get("ok") else f"error: {status.get('error_code')}"

    try:
        await asyncio.to_thread(get_longform_llm_provider)  # 只看配置能不能建出客户端，不发请求、不花钱
        checks["models"] = "ok"
    except Exception as error:
        checks["models"] = f"error: {type(error).__name__}"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if healthy else "degraded", **checks}
