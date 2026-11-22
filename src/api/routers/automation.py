"""
Muse 自动化接口：给本机 CLI（src/cli/automation.py，命令名 translation-agent）用。

挂在 /internal/automation 下，不在 /api 下：nginx 只把 /api/、/ws/ 转给后端，公网到不了这里；
接口本身再拒绝一切带转发头或不是本机来的请求。凭证只在这个进程里用，响应里从不出现。

- updates：先同步（Substack 最新一页 + Slack 只读同步），再查 since 之后的新文章和 @我。
  不导入、不翻译、不改 Slack 和 momo 本地的已读。
- translate-article：导入（已导入复用）→ 起四步法翻译（自动采用术语建议）；在跑 / 已译完就返回已有项目。
- translate-slack：一条 Slack 消息（或整个 thread）走帖子翻译链路（GPT Sol），同步返回译文；
  结果按内容缓存，同样的内容再调直接返回，不重复花钱。Slack 端照旧只读。
- status / health：只读。
- slack-todos：和网页「我的待办」同一份（会调一次轻量模型概括每件事，Slack 端只读）。
- drafts / draft：翻译记录（网页「我翻译的」/「全部翻译记录」）。draft 带原始配图（base64），只读。
- translate-slack-post：一个 thread 走网页「翻译这个帖子」同一条流程（提取 → 翻译 → 标题），存成翻译稿。
- translate-post：直接给一段帖子原文，走网页「帖子翻译」同一条链路，同步返回译文（不存翻译稿）。
- slack-reply：网页「Slack 回复」同一套：对方英文消息 → 中文理解 + 3 版英文回复；中文草稿 → 3 版英文。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
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
from src.services.post_drafts import DraftError, current_translation
from src.services.slack_inbox import SlackInboxError
from src.services.substack_service import SubstackError, article_key
from src.settings import settings

from ..dependencies import get_batch_service, get_longform_llm_provider, get_project_manager, \
    get_translation_status_service
from ..middleware import APIException, NotFoundException
from .confirmation_translation import start_longform_workflow
from .post_drafts import _draft_error, get_draft_store, run_slack_pipeline
from .slack_inbox import _run_ai, build_todos
from .slack_inbox import _to_api_error as _slack_api_error
from .slack_inbox import get_slack_inbox
from .slack_compose import compose_slack_message
from .slack_models import ConversationMessage, SlackComposeRequest, SlackProcessRequest
from .slack_process import process_slack_message
from .substack import (
    _imported_projects,
    _to_api_error,
    _translation_state,
    get_substack_client,
    get_substack_library,
    import_substack_article,
)
from .translate_models import MAX_POST_CONTENT_LENGTH, LongformWorkflowStartRequest, PostTranslateRequest
from .translate_posts import translate_post

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

    inbox = get_slack_inbox()
    status = await run_blocking(inbox.status)
    checks["slack"] = "ok" if status.get("ok") else f"error: {status.get('error_code')}"

    try:
        await asyncio.to_thread(get_longform_llm_provider)  # 只看配置能不能建出客户端，不发请求、不花钱
        checks["models"] = "ok"
    except Exception as error:
        checks["models"] = f"error: {type(error).__name__}"

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


def _summary_view(item: Dict[str, Any]) -> Dict[str, Any]:
    slack = item.get("slack")
    return {
        "draft_id": item["id"],
        "status": item["status"],  # draft 还没点「标记完成」/ done 已完成
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
                 q: str = Query("", max_length=200), limit: int = Query(50, ge=1, le=300)):
    try:
        items = await run_blocking(get_draft_store().list, q, source)
    except DraftError as error:
        raise _draft_error(error) from error
    if status != "all":
        items = [i for i in items if i["status"] == status]
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
