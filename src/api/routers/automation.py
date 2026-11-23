"""
Muse 自动化接口：给本机 CLI（src/cli/automation.py，命令名 translation-agent）用。

挂在 /internal/automation 下，不在 /api 下：nginx 只把 /api/、/ws/ 转给后端，公网到不了这里；
接口本身再拒绝一切带转发头或不是本机来的请求。凭证只在这个进程里用，响应里从不出现。

- updates：先同步（Substack 最新一页 + Slack 只读同步），再查 since 之后的新文章和 @我。
  不导入、不翻译、不改 Slack 和翻译服务本地的已读。
- translate-article：导入（已导入复用）→ 按 engines 起翻译，可多选：web = 网页版四步法（自动采用术语建议）；
  claude / codex / antigravity = 交给 Claude 页的 Agent 跑 four-step-translate，后台轮询，翻完自动导回成该 Agent 的译本
  （services/agent_translate.py）。各引擎在跑 / 已译完就返回已有的，不重复起。
- translate-slack：一条 Slack 消息（或整个 thread）走帖子翻译链路（GPT Sol），同步返回译文；
  结果按内容缓存，同样的内容再调直接返回，不重复花钱。Slack 端照旧只读。
- status / health：只读。
- dms：还没回的私信，每条带英文原话、找我干什么、中文理解和 3 版英文回复（网页私信回复面板同一套，
  结果也存进面板的历史；对方没发新消息就直接用存着的，不重复花钱）。
- slack-todos：和网页「我的待办」同一份（会调一次轻量模型概括每件事，Slack 端只读）。
- drafts / draft：翻译记录（网页「我翻译的」/「全部翻译记录」）。draft 带原始配图（base64），只读。
- translate-slack-post：一个 thread 走网页「翻译这个帖子」同一条流程（提取 → 翻译 → 标题），存成翻译稿。
- drafts/{id}/optimize：翻译稿快捷优化（网页帖子翻译的 4 个快捷项 +「更多…」6 项 + 自定义），存成新版本。
- translate-post：直接给一段帖子原文，走网页「帖子翻译」同一条链路，同步返回译文（不存翻译稿）。
- slack-reply：网页「Slack 回复」同一套：对方英文消息 → 中文理解 + 3 版英文回复；中文草稿 → 3 版英文。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import ipaddress
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking
from src.core.file_utils import read_json, write_json_atomic
from src.services import article_primary, article_sent, article_variants
from src.services.agent_translate import AGENTS, STALL_GRACE_S, WORKING, AgentRunError, AgentRunStore, SkillRunnerClient, \
    find_outputs
from src.services.post_drafts import DraftError, current_translation
from src.services.slack_inbox import SlackInboxError
from src.services.substack_service import SubstackError, article_key
from src.prompts.editing_options import OPTION_VERSION, OPTIONS_BY_ID
from src.settings import settings

from ..dependencies import get_batch_service, get_longform_llm_provider, get_project_manager, \
    get_translation_status_service
from ..middleware import APIException, NotFoundException
from .confirmation_translation import start_longform_workflow
from .post_drafts import _add_version, _draft_error, _thread_locks, get_draft_store, run_slack_pipeline
from .slack_inbox import _reply_state_path, _run_ai, build_todos
from .slack_inbox import _to_api_error as _slack_api_error
from .slack_inbox import get_slack_inbox
from .slack_compose import compose_slack_message
from .slack_models import ConversationMessage, SlackComposeRequest, SlackProcessRequest
from .slack_models import STYLE_MAP as REPLY_STYLES
from .slack_process import process_slack_message
from .translate_utils import validate_path_component
from .workbench import set_sent
from .substack import (
    _imported_projects,
    _to_api_error,
    _translation_state,
    article_state,
    get_substack_client,
    get_substack_library,
    import_substack_article,
)
from .translate_models import MAX_POST_CONTENT_LENGTH, LongformWorkflowStartRequest, PostOptimizeRequest, \
    PostTranslateRequest
from .translate_posts import optimize_post_translation, translate_post

logger = logging.getLogger(__name__)

_FORWARD_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded", "cf-connecting-ip")


def require_local(request: Request) -> None:
    """只接本机直连：经过 nginx / Cloudflare 的请求都带转发头。"""
    host = request.client.host if request.client else ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if not local or any(h in request.headers for h in _FORWARD_HEADERS):
        raise APIException(status_code=403, detail="只允许本机调用", error_code="FORBIDDEN")


router = APIRouter(prefix="/internal/automation", dependencies=[Depends(require_local)])

# 同一篇文章同时只处理一次 translate-article，避免并发调用导入出两个项目
_translate_lock = asyncio.Lock()
_slack_lock = asyncio.Lock()
# Slack 这边的模型调用一律走官方 GPT Sol（docs/Slack收件箱.md「模型」）
SLACK_MODEL = "gpt-6.2-sol"
SLACK_PREFIX = "slack-"


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
        status, project_id, sent_at = "not_imported", None, None
        if project is not None:
            status, _, sent_at = await asyncio.to_thread(article_state, pm, project, variants.get(project.id, []))
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
            "sent_at": sent_at,
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


ENGINES = ("web", *AGENTS)


class TranslateArticleRequest(BaseModel):
    article: str = Field(..., min_length=1, max_length=2000)  # slug 或 Substack 文章链接
    target_lang: str = Field("zh", max_length=10)
    engines: List[str] = Field(default_factory=lambda: ["web"], min_length=1, max_length=len(ENGINES))


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
    engines = list(dict.fromkeys(body.engines))
    if any(e not in ENGINES for e in engines):
        raise APIException(status_code=400, detail=f"engines 只能是：{', '.join(ENGINES)}", error_code="BAD_REQUEST")
    async with _translate_lock:
        try:
            url = await run_blocking(_resolve_article_url, body.article.strip())
        except SubstackError as error:
            raise _to_api_error(error) from error
        pm = get_project_manager()
        project, _already = await import_substack_article(pm, get_substack_client(), url)
        result = {"project_id": project.id, "article": project.title, "url": _article_link(project.id)}
        out: Dict[str, Dict[str, Any]] = {}
        for engine in engines:
            out[engine] = (await _start_web(request, pm, project.id) if engine == "web"
                           else await _start_agent(pm, project.id, project.title, engine))
    if engines == ["web"]:  # 老调用方式：结果平铺在顶层
        return {**result, **out["web"], "engines": out}
    statuses = {v["status"] for v in out.values()}
    status = ("started" if statuses & {"started", "resumed"} else "failed" if statuses == {"failed"}
              else "already_exists")
    return {**result, "status": status, "engines": out}


async def _start_web(request: Request, pm, project_id: str) -> Dict[str, Any]:
    """网页版四步法；只看主项目自己（Agent 译本不算）。"""
    state, progress = await asyncio.to_thread(_translation_state, pm, project_id, [], project_id)
    if state in {"translating", "awaiting_terms", "translated"}:
        return {"status": "already_exists", "translation_status": state, "progress": progress}
    try:
        started = await start_longform_workflow.__wrapped__(  # 绕过网页用的 3 次/分钟限流，并发由上面的锁管
            request=request,
            project_id=project_id,
            service=get_batch_service(),
            body=LongformWorkflowStartRequest(method="four-step", auto_accept_terms=True),
        )
    except APIException as error:
        if error.status_code == 409:  # 刚好有人在网页上点了开始
            return {"status": "already_exists", "translation_status": "translating", "progress": progress}
        raise
    return {"status": "resumed" if started.get("resumed") else "started", "run_id": started.get("run_id")}


# ---------------------------------------------------------------- Agent 翻译（Claude / Codex / agy）


def get_agent_store() -> AgentRunStore:
    return AgentRunStore(Path(settings.automation_agent_runs_file))


def get_skill_runner() -> SkillRunnerClient:
    return SkillRunnerClient(settings.skill_runner_url, Path(settings.skill_runner_env_file))


def _agent_variant(pm, project_id: str, agent: str) -> Optional[Dict[str, Any]]:
    """这个 Agent 已经导进来的译本：{variant_id, run_id, ...}；没有返回 None。"""
    for variant in article_variants.list_variants(pm, project_id):
        record = article_variants.read_import_record(pm, variant.id)
        if record and (record.get("agent") or "claude") == agent:
            return {**record, "variant_id": variant.id}
    return None


async def _start_agent(pm, project_id: str, title: str, agent: str) -> Dict[str, Any]:
    store = get_agent_store()
    record = (await asyncio.to_thread(store.get, project_id)).get(agent)
    if record and record.get("status") == "running":
        return {"status": "already_exists", "translation_status": "translating", "run_id": record.get("run_id")}
    variant = await asyncio.to_thread(_agent_variant, pm, project_id, agent)
    if variant:
        return {"status": "already_exists", "translation_status": "translated", "variant_id": variant["variant_id"]}
    html_path = pm._project_dir(project_id) / "source.html"
    if not html_path.is_file():
        return {"status": "failed", "error": "这篇没有原文 HTML，Agent 只能翻 HTML"}
    try:
        run = await run_blocking(get_skill_runner().start, html=html_path.read_bytes(), filename=f"{project_id}.html",
                                 harness=agent, title=f"精翻：{title}")
    except AgentRunError as error:
        return {"status": "failed", "error": error.message}
    await asyncio.to_thread(store.update, project_id, agent, run_id=run["id"], status="running",
                            started_at=time.time(), error=None, variant_id=None, stalled_at=None)
    # 网页文章工作台也显示这个任务的进度（和网页点「交给 Agent」一样）
    await run_blocking(lambda: pm.merge_meta_fields(project_id, fields={"claude_run_id": run["id"]}))
    return {"status": "started", "run_id": run["id"]}


async def poll_agent_runs() -> int:
    """看一遍在跑的 Agent 任务：一轮结束、不在等确认就取回 zh.md / en.md 导成译本。返回这次导入了几篇。"""
    store, client, pm = get_agent_store(), get_skill_runner(), get_project_manager()
    imported = 0
    for project_id, agent, record in await asyncio.to_thread(store.to_poll):
        run_id = record.get("run_id") or ""
        stalled = record.get("status") == "failed"  # 停在半路判过失败的：只看后来有没有人把它翻完

        def fail(message: str, stalled_at: Optional[float] = None) -> None:
            store.update(project_id, agent, status="failed", error=message, stalled_at=stalled_at)

        try:
            run = await run_blocking(client.run, run_id)
            if run.get("status") == "error":
                await asyncio.to_thread(fail, run.get("error") or "Agent 出错停下了")
                continue
            if run.get("status") in WORKING or run.get("awaiting_reply") or run.get("busy"):
                if stalled:  # 有人在 Claude 页让它接着翻了
                    await asyncio.to_thread(store.update, project_id, agent, status="running", error=None,
                                            stalled_at=None)
                continue  # 在跑 / 等术语确认（10 分钟没人回会自动继续）/ 这一轮结束了但后台子代理还在跑
            existing = await asyncio.to_thread(_agent_variant, pm, project_id, agent)
            if existing and existing.get("run_id") == run_id:  # 网页那边已经导过了
                await asyncio.to_thread(store.update, project_id, agent, status="done",
                                        variant_id=existing["variant_id"], error=None, stalled_at=None)
                continue
            outputs = find_outputs(await run_blocking(client.files, run_id))
            if not outputs:
                if not stalled and time.time() - (run.get("updated_at") or 0) > STALL_GRACE_S:
                    await asyncio.to_thread(fail, "Agent 停在半路，没产出 zh.md 和 en.md（在 Claude 页发「继续」"
                                                  "接着翻完会自动导回）", time.time())
                continue
            zh = await run_blocking(client.read, run_id, outputs["zh"])
            en = await run_blocking(client.read, run_id, outputs["en"])
            result = await run_blocking(
                article_primary.import_agent_version, pm, project_id, zh_markdown=zh, en_markdown=en,
                run_id=run_id, agent=agent, model=run.get("actual_model") or run.get("model") or None)
        except AgentRunError as error:
            if error.status_code == 404:
                await asyncio.to_thread(fail, "Claude 页里这个任务不见了（被删了？）")
            else:
                logger.warning("Agent 任务 %s 查询失败，下次再试：%s", run_id, error.message)
            continue
        except article_variants.AlignmentTooLow as error:
            await asyncio.to_thread(fail, f"Agent 的英文稿和原文对不上，没导入：{error}")
            continue
        except (ValueError, FileNotFoundError) as error:
            await asyncio.to_thread(fail, f"导入失败：{error}")
            continue
        await asyncio.to_thread(store.update, project_id, agent, status="done", variant_id=result["variant_id"],
                                model=run.get("actual_model") or run.get("model"), error=None, stalled_at=None)
        imported += 1
    return imported


async def agent_translate_loop(interval_s: float = 60) -> None:
    while True:
        try:
            await poll_agent_runs()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 后台任务不能因为一次异常就停
            logger.exception("Agent 翻译轮询出错")
        await asyncio.sleep(interval_s)


async def _engine_statuses(pm, project_id: str) -> Dict[str, Dict[str, Any]]:
    """每个引擎各自的进度：web 看主项目；Agent 看任务记录和导进来的译本。没起过的 Agent 不列。"""
    state, progress = await asyncio.to_thread(_translation_state, pm, project_id, [], project_id)
    web_status = ("running" if state in {"translating", "awaiting_terms"} else "done" if state == "translated"
                  else "failed" if state == "partial" else "not_started")
    out: Dict[str, Dict[str, Any]] = {"web": {"status": web_status, "progress": progress}}
    records = await asyncio.to_thread(get_agent_store().get, project_id)
    for agent in AGENTS:
        record = records.get(agent) or {}
        variant = await asyncio.to_thread(_agent_variant, pm, project_id, agent)
        if record.get("status") == "running":
            out[agent] = {"status": "running", "run_id": record.get("run_id")}
        elif record.get("status") == "failed":
            out[agent] = {"status": "failed", "error": record.get("error"), "run_id": record.get("run_id")}
        elif variant:
            out[agent] = {"status": "done", "variant_id": variant["variant_id"], "model": variant.get("model")}
    return out


# ---------------------------------------------------------------- status


def _last_error(payload: Dict[str, Any]) -> Optional[str]:
    errors = payload.get("errors") or []
    if errors and isinstance(errors[-1], dict):
        return str(errors[-1].get("error") or "")[:500] or None
    return None


@router.get("/projects/{project_id}/status")
async def project_status(project_id: str, with_markdown: bool = False,
                         engine: Optional[str] = Query(None, pattern="^(web|claude|codex|antigravity)$")):
    if project_id.startswith(SLACK_PREFIX):
        return await slack_status(project_id)
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
        "sent_at": None,
    }
    sent = await asyncio.to_thread(article_sent.read, pm, project_id)
    if sent:
        result["sent_at"] = sent["at"]
    if status == "failed":
        result["error"] = _last_error(payload) or f"翻译停在 {progress}%（状态 {payload.get('status') or state}）"
    engines = await _engine_statuses(pm, project_id)
    result["engines"] = engines
    if with_markdown:
        # 指定了引擎就给那一版的全文，否则给网页上显示的主译本
        if engine:
            chosen = engines.get(engine) or {}
            export_id = (project_id if engine == "web" else chosen.get("variant_id")) if chosen.get("status") == "done" else None
        else:
            export_id = project_id if status == "done" else None
        if export_id:
            try:
                result["markdown"] = await run_blocking(pm.export, export_id, format="zh")
            except ValueError as error:
                result["markdown_error"] = str(error)
        elif engine:
            result["markdown_error"] = f"{engine} 这一版还没翻完"
    return result


# ---------------------------------------------------------------- 已发送


@router.get("/articles")
async def articles(status: str = Query("unsent", pattern="^(unsent|sent)$"),
                   limit: int = Query(50, ge=1, le=200)):
    """导入过的文章里：unsent 译完还没标已发送 / sent 已发送（按标记时间从新到旧）。不去 Substack 同步。"""
    pm = get_project_manager()

    def collect() -> List[Dict[str, Any]]:
        imported, variants = _imported_projects(pm)
        posts = {article_key(post.url): post for post in get_substack_library().posts()}
        items = []
        for key, project in imported.items():
            state, _, sent_at = article_state(pm, project, variants.get(project.id, []))
            if state != ("sent" if status == "sent" else "translated"):
                continue
            post = posts.get(key)
            items.append({
                "project_id": project.id,
                "title": project.title,
                "zh_title": post.zh_title if post else "",
                "url": project.original_url,
                "published_at": post.post_date if post else None,
                "sent_at": sent_at,
                "result": _article_link(project.id),
            })
        sort_key = "sent_at" if status == "sent" else "published_at"
        items.sort(key=lambda item: item[sort_key] or "", reverse=True)
        return items

    items = await asyncio.to_thread(collect)
    return {"status": status, "total": len(items), "articles": items[:limit]}


class MarkSentRequest(BaseModel):
    sent: bool = True  # false = 撤销


@router.post("/drafts/{draft_id}/sent")
async def mark_draft_sent(draft_id: str, body: MarkSentRequest):
    """翻译稿标记 / 撤销「已发送」，和网页上的按钮同一个记录。"""
    try:
        doc = await run_blocking(get_draft_store().set_sent, draft_id, body.sent)
    except DraftError as error:
        raise _draft_error(error) from error
    return {"draft_id": draft_id, "sent": body.sent, "sent_at": _iso(doc["sent_at"]) if doc.get("sent_at") else None}


@router.post("/projects/{project_id}/sent")
async def mark_sent(project_id: str, body: MarkSentRequest):
    """标记 / 撤销「已发送」，和工作台上的按钮同一个记录。"""
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    try:
        sent = await run_blocking(set_sent, get_project_manager(), project_id, body.sent)
    except FileNotFoundError as exc:
        raise NotFoundException(detail="Project not found") from exc
    return {"project_id": project_id, "sent": body.sent, "sent_at": sent["at"] if sent else None}


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

    inbox = get_slack_inbox()
    status = await run_blocking(inbox.status)
    checks["slack"] = "ok" if status.get("ok") else f"error: {status.get('error_code')}"

    try:
        await asyncio.to_thread(get_longform_llm_provider)  # 只看配置能不能建出客户端，不发请求、不花钱
        checks["models"] = "ok"
    except Exception as error:
        checks["models"] = f"error: {type(error).__name__}"

    try:  # Claude 页（Agent 翻译用）：能不能用口令签的 cookie 调通
        await run_blocking(get_skill_runner().me)
        checks["agents"] = "ok"
    except AgentRunError as error:
        checks["agents"] = f"error: {error.message}"

    healthy = all(v == "ok" for v in checks.values())
    groups = await run_blocking(inbox.my_groups) if status.get("ok") else []
    # 用户组：自动识别到几个、手配了几个（group 类 @ 靠它们）
    return {"status": "healthy" if healthy else "degraded", **checks,
            "slack_groups": {"detected": len(groups), "configured": len(_group_ids())}}


# ---------------------------------------------------------------- translate-slack


class TranslateSlackRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=30)
    message_ts: str = Field(..., min_length=1, max_length=30)
    thread_ts: Optional[str] = Field(None, max_length=30)  # thread 里的回复：本地没有时靠它去拉
    with_thread: bool = False


def _slack_store_path() -> Path:
    return Path(settings.slack_cache_dir) / "automation_translations.json"


def _slack_results() -> Dict[str, Any]:
    path = _slack_store_path()
    try:
        return read_json(path) if path.exists() else {}
    except (OSError, ValueError):
        return {}


@router.post("/translate-slack")
async def translate_slack(request: Request, body: TranslateSlackRequest):
    inbox = get_slack_inbox()
    try:
        source = await run_blocking(inbox.translation_source, body.conversation_id, body.message_ts,
                                    body.thread_ts, body.with_thread)
    except SlackInboxError as error:
        raise _slack_api_error(error) from error
    text = source["source_text"].strip()
    if not text:
        raise APIException(status_code=400, detail="这条消息没有可翻译的文字", error_code="EMPTY_MESSAGE")
    if len(text) > MAX_POST_CONTENT_LENGTH:
        raise APIException(status_code=400, detail=f"原文超过 {MAX_POST_CONTENT_LENGTH} 字符，太长了",
                           error_code="TOO_LONG")
    key = f"{SLACK_PREFIX}{body.conversation_id}-{body.message_ts}" + ("-thread" if body.with_thread else "")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    async with _slack_lock:
        cached = (await asyncio.to_thread(_slack_results)).get(key)
        if cached and cached.get("source_hash") == digest:
            return {"project_id": key, "status": "already_exists", **_slack_view(cached)}
        result = await translate_post.__wrapped__(  # 绕过网页用的限流，并发由锁管
            request=request,
            body=PostTranslateRequest(content=text, model=SLACK_MODEL, include_hashtags=False),
        )
        record = {
            "source_hash": digest,
            "source_text": text,
            "translation": result.translation,
            "messages": source["messages"],
            "permalink": source["permalink"],
            "model": result.model_used,
            "translated_at": _iso(time.time()),
        }

        def save():
            results = _slack_results()
            results[key] = record
            _slack_store_path().parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(_slack_store_path(), results)

        await asyncio.to_thread(save)
    # 帖子翻译几十秒就完，直接同步返回结果；status 也能查到
    return {"project_id": key, "status": "done", **_slack_view(record)}


def _slack_view(record: Dict[str, Any]) -> Dict[str, Any]:
    return {key: record.get(key) for key in ("translation", "source_text", "messages", "permalink", "translated_at")}


async def slack_status(project_id: str) -> Dict[str, Any]:
    record = (await asyncio.to_thread(_slack_results)).get(project_id)
    if record is None:
        raise NotFoundException(detail="没有这条 Slack 翻译")
    return {"project_id": project_id, "status": "done", "progress": 100, "stage": None,
            "result": record.get("translation"), "error": None, **_slack_view(record)}


# ---------------------------------------------------------------- slack-todos / drafts / draft / translate-slack-post

# 配图按原图返回（base64）。单张、合计都设上限，超了只给元数据，Muse 可以去网页下载
MAX_IMAGE_BYTES = 30_000_000
MAX_IMAGES_TOTAL_BYTES = 100_000_000


def _draft_link(doc: Dict[str, Any]) -> str:
    base = settings.automation_public_url.rstrip("/")
    slack = doc.get("slack")
    if doc.get("source") == "slack" and slack:
        return f"{base}/slack?mode=translate&tc={slack['channel_id']}&t={slack['thread_ts']}"
    return f"{base}/post?draft={doc['id']}"


def _todo_view(item: Dict[str, Any]) -> Dict[str, Any]:
    draft = item.get("draft")
    return {
        "kind": item["kind"],  # dm 私信 / mention thread 里 @我
        "action": item["action"],  # reply 要回复 / do 要做事（多半是翻译）/ read 看看就行
        "task": item["task"],
        "title": item["title"],
        "where": ("私信 · " if item["kind"] == "dm" else "#") + item["channel_name"],
        "from": item["from"],
        "count": item["count"],
        "conversation_id": item["channel_id"],
        "thread_ts": item["thread_ts"],
        "latest_at": _iso(float(item["latest_ts"])),
        "draft": {"draft_id": draft["id"], "status": draft["status"], "versions": draft["versions"],
                  "no_post": draft["no_post"]} if draft else None,
    }


@router.get("/slack-todos")
async def slack_todos():
    try:
        todos = await build_todos()
    except SlackInboxError as error:
        raise _slack_api_error(error) from error
    return {"items": [_todo_view(i) for i in todos["items"]],
            "fyi": [_todo_view(i) for i in todos["fyi"]]}


# ---------------------------------------------------------------- dms

MAX_DM_REPLIES_PER_CALL = 10  # 一次最多新生成几条，其余下次再生成（每条一次模型调用）
_dm_lock = asyncio.Lock()


def _read_reply_state(channel_id: str) -> Dict[str, Any]:
    try:
        state = json.loads(_reply_state_path(channel_id).read_text(encoding="utf-8"))
        return state if isinstance(state, dict) and isinstance(state.get("groups"), list) else {"groups": [], "current": -1}
    except (OSError, ValueError):
        return {"groups": [], "current": -1}


def _push_reply_group(channel_id: str, group: Dict[str, Any]) -> None:
    """和网页私信回复面板 push 一样：追加一组、设为当前，最多留 20 组。"""
    state = _read_reply_state(channel_id)
    groups = [*state["groups"], group][-20:]
    path = _reply_state_path(channel_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, {"groups": groups, "current": len(groups) - 1})


async def _dm_replies(request: Request, channel_id: str, allow_new: bool) -> Optional[Dict[str, Any]]:
    """对方在我最后一次发言之后发的消息 → 中文理解 + 3 版回复。和 DmReplyPanel.generate 同样的输入。"""
    ctx = await run_blocking(get_slack_inbox().agent_context, channel_id)
    history, latest_ts = ctx["history"], ctx["latest_ts"]
    roles = [h["role"] for h in history]
    last_me = len(roles) - 1 - roles[::-1].index("me") if "me" in roles else -1
    pending = [h["content"] for h in history[last_me + 1:] if h["role"] == "them"]
    if not pending:
        return None
    for group in reversed(_read_reply_state(channel_id)["groups"]):
        if group.get("kind") == "generate" and group.get("based_on_ts") == latest_ts:
            return {"translation": group.get("understanding") or "", "replies": group.get("replies") or [],
                    "generated": False}
    if not allow_new:
        return {"translation": "", "replies": [], "generated": False, "note": "这次生成的条数到上限了，下次再拉"}
    result = await process_slack_message.__wrapped__(request=request, body=SlackProcessRequest(
        message="\n\n".join(pending)[:50000], conversation_history=history[:last_me + 1][-20:]))
    replies = [{"version": r.version, "english": r.english.strip(), "chinese": (r.chinese or "").strip()}
               for r in result.suggested_replies if r.english.strip()]
    await run_blocking(_push_reply_group, channel_id, {
        "created_at": int(time.time() * 1000), "kind": "generate", "understanding": result.translation,
        "pending": True, "replies": replies, "based_on_ts": latest_ts})
    return {"translation": result.translation, "replies": replies, "generated": True}


@router.get("/dms")
async def dms(request: Request):
    try:
        todos = await build_todos()
    except SlackInboxError as error:
        raise _slack_api_error(error) from error
    material = {m["channel_id"]: m for m in await run_blocking(get_slack_inbox().todo_material) if m["kind"] == "dm"}
    items, generated = [], 0
    async with _dm_lock:  # Muse 并发拉两次也只生成一遍
        for todo in todos["items"]:
            if todo["kind"] != "dm":
                continue
            cid = todo["channel_id"]
            try:
                reply = await _dm_replies(request, cid, generated < MAX_DM_REPLIES_PER_CALL)
            except SlackInboxError as error:
                reply = {"translation": "", "replies": [], "generated": False, "note": error.message}
            except APIException as error:  # 模型失败：这一条给原因，不影响别的
                reply = {"translation": "", "replies": [], "generated": False, "note": str(error.detail)}
            generated += bool(reply and reply.get("generated"))
            items.append({
                **_todo_view(todo),
                "messages": (material.get(cid) or {}).get("messages", []),  # 英文原话：还没读的那几条
                "translation": (reply or {}).get("translation", ""),  # 中文理解
                "replies": [{**r, "style": REPLY_STYLES.get(r.get("version"), "")} for r in (reply or {}).get("replies", [])],
                **({"note": reply["note"]} if reply and reply.get("note") else {}),
                "link": f"{settings.automation_public_url.rstrip('/')}/slack?c={cid}",
            })
    return {"items": items}


def _summary_view(item: Dict[str, Any]) -> Dict[str, Any]:
    slack = item.get("slack")
    return {
        "draft_id": item["id"],
        "status": item["status"],  # draft 还没点「标记完成」/ done 已完成
        "sent_at": _iso(item["sent_at"]) if item.get("sent_at") else None,  # 标记已发送的时间，和 status 无关
        "sent_changed": item.get("sent_changed", False),  # 标了已发送之后译文又改过
        "source": item["source"],  # slack / manual（帖子翻译页手动粘贴的）
        "auto": item["auto"],  # 后台或 Muse 自动翻的
        "title": item["title"],
        "preview": item["preview"],
        "versions": item["versions"],
        "image_count": item["image_count"],
        "slack": {"conversation_id": slack["channel_id"], "thread_ts": slack["thread_ts"],
                  "channel_name": slack["channel_name"]} if slack else None,
        "updated_at": _iso(item["updated_at"] or 0),
    }


@router.get("/drafts")
async def drafts(status: str = Query("draft", pattern="^(draft|done|all)$"),
                 source: str = Query("", pattern="^(|slack|manual)$"),
                 q: str = Query("", max_length=200), limit: int = Query(50, ge=1, le=300),
                 sent: str = Query("", pattern="^(|yes|no)$")):
    try:
        items = await run_blocking(get_draft_store().list, q, source)
    except DraftError as error:
        raise _draft_error(error) from error
    if status != "all":
        items = [i for i in items if i["status"] == status]
    if sent in ("yes", "no"):  # 直接调用时 Query 默认值不生效
        items = [i for i in items if bool(i.get("sent_at")) == (sent == "yes")]
    return {"total": len(items), "items": [_summary_view(i) for i in items[:limit]]}


def _load_images(doc: Dict[str, Any], with_data: bool) -> List[Dict[str, Any]]:
    """按发帖顺序给配图；with_data 时带原图 base64。拿不到的给 error，不影响别的。"""
    images = doc.get("images") or []
    if not images:
        return []
    inbox = get_slack_inbox()
    slack = doc.get("slack") or {}
    if slack:
        try:
            inbox.replies(slack["channel_id"], slack["thread_ts"])  # 登记文件下载地址（重启后内存里没有）
        except SlackInboxError as error:
            logger.warning("automation draft: 登记配图失败：%s", error.message)
    out, total = [], 0
    for n, img in enumerate(images, start=1):
        entry: Dict[str, Any] = {"n": n, "id": img["id"], "name": img.get("name") or img["id"]}
        try:
            path, mimetype, name = inbox.file(img["id"])
        except SlackInboxError as error:
            out.append({**entry, "error": error.message})
            continue
        data = path.read_bytes()
        entry.update({"name": name, "mimetype": mimetype, "size": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
        if with_data:
            if len(data) > MAX_IMAGE_BYTES or total + len(data) > MAX_IMAGES_TOTAL_BYTES:
                entry["error"] = "图太大，没放进返回结果，去网页下载"
            else:
                entry["data_base64"] = base64.b64encode(data).decode("ascii")
                total += len(data)
        out.append(entry)
    return out


def _draft_view(doc: Dict[str, Any], images: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = doc.get("state") or {}
    titles = [t for t in state.get("generatedTitles") or [] if isinstance(t, str)]
    extraction = doc.get("extraction") or {}
    slack = doc.get("slack")
    no_post = extraction.get("has_post") is False
    return {
        "draft_id": doc["id"],
        "status": doc.get("status", "draft"),
        "source": doc.get("source"),
        "auto": bool(doc.get("auto")),
        "selected_title": state.get("selectedTitle") or "",
        "titles": titles,
        "source_text": state.get("originalText") or "",
        "translation": current_translation(state),
        "versions": len(state.get("versions") or []),
        "no_post": no_post,
        "note": (extraction.get("note") or "") if no_post else "",
        "images": images,
        "slack": {"conversation_id": slack["channel_id"], "thread_ts": slack["thread_ts"],
                  "channel_name": slack.get("channel_name"), "title": slack.get("title"),
                  "permalink": slack.get("permalink")} if slack else None,
        "link": _draft_link(doc),
        "updated_at": _iso(doc.get("updated_at") or 0),
    }


async def _draft_result(doc: Dict[str, Any], with_images: bool) -> Dict[str, Any]:
    images = await run_blocking(_load_images, doc, with_images)
    return _draft_view(doc, images)


@router.get("/drafts/{draft_id}")
async def draft(draft_id: str, images: bool = True):
    try:
        doc = await run_blocking(get_draft_store().get, draft_id)
    except DraftError as error:
        raise _draft_error(error) from error
    if not doc:
        raise NotFoundException(detail="找不到这份翻译稿")
    return await _draft_result(doc, images)


# 帖子翻译「更多…」的 6 项，和网页 OptimizationPanel 读同一份
MORE_OPTIONS = {item["id"]: item for item in json.loads(
    (Path(__file__).resolve().parents[3] / "config" / "post_more_options.json").read_text(encoding="utf-8"))["options"]}
OPTIMIZE_OPTIONS = [*OPTIONS_BY_ID, *MORE_OPTIONS]


class OptimizeDraftRequest(BaseModel):
    option: Optional[str] = Field(None, max_length=40)
    instruction: Optional[str] = Field(None, max_length=1000)


def _optimize_lineage(state: Dict[str, Any], base: Dict[str, Any], limit: int = 3) -> List[Dict[str, str]]:
    """和前端 getOptimizationHistory 一致：沿 parentVersionId 往上，同一份原文上做过的最近几次要求。"""
    by_id = {v.get("id"): v for v in state.get("versions") or [] if isinstance(v, dict)}
    lineage, seen, current = [], set(), base
    while current and current.get("id") not in seen:
        seen.add(current.get("id"))
        if current.get("sourceRevision") == base.get("sourceRevision") and current.get("sourceText") == base.get("sourceText"):
            lineage.append(current)
        current = by_id.get(current.get("parentVersionId"))
    asks = [str(v["instruction"]).strip() for v in reversed(lineage) if str(v.get("instruction") or "").strip()]
    return [{"role": "user", "content": a} for a in asks[-limit:]]


@router.post("/drafts/{draft_id}/optimize")
async def optimize_draft(request: Request, draft_id: str, body: OptimizeDraftRequest):
    custom = (body.instruction or "").strip()
    if bool(custom) == bool(body.option):
        raise APIException(status_code=400, detail="option 和 instruction 二选一", error_code="BAD_ARGUMENT")
    if body.option and body.option not in OPTIMIZE_OPTIONS:
        raise APIException(status_code=400, detail=f"option 只能是：{', '.join(OPTIMIZE_OPTIONS)}",
                           error_code="BAD_ARGUMENT")
    store = get_draft_store()
    try:
        doc = await run_blocking(store.get, draft_id)
    except DraftError as error:
        raise _draft_error(error) from error
    if not doc:
        raise NotFoundException(detail="找不到这份翻译稿")
    slack = doc.get("slack") or {}
    key = f"{slack['channel_id']}:{slack['thread_ts']}" if slack else draft_id
    async with _thread_locks.setdefault(key, asyncio.Lock()):  # 和网页「重新提取」、后台自动翻译互斥
        doc = await run_blocking(store.get, draft_id) or doc
        state = doc.get("state") or {}
        versions = [v for v in state.get("versions") or [] if isinstance(v, dict)]
        base = next((v for v in versions if v.get("id") == state.get("currentVersionId")), versions[-1] if versions else None)
        if not base or not str(base.get("content") or "").strip():
            raise APIException(status_code=400, detail="这份稿子还没有译文，先翻译再优化", error_code="NO_TRANSLATION")
        source = str(base.get("sourceText") or state.get("originalText") or "")
        if not source.strip():
            raise APIException(status_code=400, detail="缺少对应原文，没法优化", error_code="NO_SOURCE")
        base = {**base, "sourceText": source}
        if body.option in OPTIONS_BY_ID:
            option_id, instruction = body.option, None
            label = f"[{OPTION_VERSION}] {OPTIONS_BY_ID[body.option]['description']}"  # 和网页 describeOptimizeOption 一致
        else:
            option_id, instruction = None, MORE_OPTIONS[body.option]["instruction"] if body.option else custom
            label = instruction
        result = await optimize_post_translation.__wrapped__(request=request, body=PostOptimizeRequest(
            original_text=source[:MAX_POST_CONTENT_LENGTH], current_translation=str(base["content"])[:MAX_POST_CONTENT_LENGTH],
            instruction=instruction, option_id=option_id, conversation_history=_optimize_lineage(state, base)))
        _add_version(state, result.optimized_translation, result.model_used, label, optimized_from=base)
        doc["state"] = state
        doc = await run_blocking(store.put_system, doc)
    return await _draft_result(doc, False)


class TranslateSlackPostRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=30)
    thread_ts: str = Field(..., min_length=1, max_length=30)
    instruction: Optional[str] = Field(None, max_length=500)  # 挑错了时告诉 AI 要翻哪条
    with_images: bool = True


@router.post("/translate-slack-post")
async def translate_slack_post(body: TranslateSlackPostRequest):
    try:
        doc = await _run_ai(run_slack_pipeline(body.conversation_id, body.thread_ts,
                                               instruction=body.instruction, auto=True), "帖子提取")
    except SlackInboxError as error:
        raise _slack_api_error(error) from error
    except DraftError as error:
        raise _draft_error(error) from error
    return await _draft_result(doc, body.with_images)


# ---------------------------------------------------------------- translate-post / slack-reply


class TranslatePostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_POST_CONTENT_LENGTH)
    hashtags: bool = False  # 网页默认带小红书话题标签；给机器人默认不带


@router.post("/translate-post")
async def translate_post_text(request: Request, body: TranslatePostRequest):
    if not body.content.strip():
        raise APIException(status_code=400, detail="原文是空的", error_code="EMPTY_MESSAGE")
    result = await translate_post.__wrapped__(  # 绕过网页用的限流
        request=request, body=PostTranslateRequest(content=body.content, include_hashtags=body.hashtags))
    return {"translation": result.translation, "model": result.model_used}


class SlackReplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    mode: str = Field("auto", pattern="^(auto|incoming|compose)$")
    history: List[ConversationMessage] = Field(default_factory=list, max_length=100)


def resolve_reply_mode(text: str, mode: str) -> str:
    """auto：中文占三成以上算自己的中文草稿（compose），否则算对方发来的消息（incoming）。"""
    if mode != "auto":
        return mode
    compact = "".join(text.split())
    if not compact:
        return "incoming"
    chinese = sum("\u4e00" <= char <= "\u9fff" for char in compact)
    return "compose" if chinese / len(compact) > 0.3 else "incoming"


@router.post("/slack-reply")
async def slack_reply(request: Request, body: SlackReplyRequest):
    if not body.text.strip():
        raise APIException(status_code=400, detail="内容是空的", error_code="EMPTY_MESSAGE")
    mode = resolve_reply_mode(body.text, body.mode)
    if mode == "compose":
        result = await compose_slack_message.__wrapped__(
            request=request, body=SlackComposeRequest(content=body.text, conversation_history=body.history))
        replies, translation = result.versions, None
    else:
        result = await process_slack_message.__wrapped__(
            request=request, body=SlackProcessRequest(message=body.text, conversation_history=body.history))
        replies, translation = result.suggested_replies, result.translation
    return {
        "mode": mode,
        "translation": translation,  # incoming 时是对方消息的中文理解
        "replies": [{"version": r.version, "style": r.style, "english": r.english, "chinese": r.chinese}
                    for r in replies],
        "model": result.model_used,
    }
