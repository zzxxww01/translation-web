"""
Slack 收件箱：展示「我」所在的频道、私信和 thread，支持附件下载和导出。

完全只读：后端只调白名单里的查询接口，不发送、不改 Slack 里的已读状态。「已读」只记在 momo 本地。
见 src/services/slack_inbox.py。
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking
from src.api.utils.glossary import build_glossary_context
from src.api.utils.json_utils import parse_llm_json_response
from src.api.utils.llm_errors import raise_empty_llm_result, raise_llm_service_unavailable
from src.api.utils.llm_factory import generate_with_fallback_budget
from src.prompts.contracts import PromptContractError
from src.services.slack_ai import MAX_BATCH, MAX_TEXT_CHARS, SlackAI
from src.services.slack_inbox import (
    SlackCredentialStore,
    SlackInbox,
    SlackInboxError,
    export_to_markdown,
)
from src.settings import settings

from ..middleware import APIException, ServiceUnavailableException
from ..middleware.rate_limit import limiter


router = APIRouter(prefix="/slack-inbox")

# 浏览器里直接内联显示的图片类型；其余一律当附件下载，避免 HTML/SVG 在 momo 域名下执行
_INLINE_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@lru_cache(maxsize=1)
def get_slack_inbox() -> SlackInbox:
    inbox = SlackInbox(
        SlackCredentialStore(Path(settings.slack_credentials_file)),
        cache_dir=Path(settings.slack_cache_dir),
        dm_recent_days=settings.slack_dm_recent_days,
    )
    # 第一次有人用 Slack 页就起后台同步，之后一直把新消息拉进本地（测试里不起）
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        inbox.start_background_sync()
    return inbox


def _to_api_error(error: SlackInboxError) -> APIException:
    return APIException(status_code=error.status_code, detail=error.message, error_code=error.code)


async def _run(func, *args, **kwargs):
    try:
        return await run_blocking(func, *args, **kwargs)
    except SlackInboxError as error:
        raise _to_api_error(error) from error


class SlackCredentialsRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=2000)
    cookie_d: str = Field(..., min_length=1, max_length=4000)


@router.get("/status")
async def get_status():
    return await _run(get_slack_inbox().status)


@router.get("/activity")
async def get_activity():
    """「动态」：频道 thread 和私信各一行，按最近活动排序。thread 行带上翻译稿状态（草稿 / 已完成）。"""
    data = await _run(get_slack_inbox().activity)
    index = await run_blocking(_draft_index)
    for item in data["items"]:
        if item.get("thread_ts"):
            item["draft"] = index.get(f"{item['channel_id']}:{item['thread_ts']}")
    return data


@router.put("/credentials")
@limiter.limit("10/minute")
async def save_credentials(request: Request, body: SlackCredentialsRequest):
    # 只回状态，永不回显凭证
    return await _run(get_slack_inbox().save_credentials, body.token, body.cookie_d)


@router.get("/conversations")
async def list_conversations(refresh: bool = False):
    inbox = get_slack_inbox()
    conversations = await _run(inbox.conversations, refresh)
    return {"conversations": conversations, "threads": await _run(inbox.thread_badge)}


@router.get("/threads")
async def list_followed_threads():
    return await _run(get_slack_inbox().threads)


@router.get("/conversations/{channel_id}/threads")
async def list_channel_threads(channel_id: str):
    return await _run(get_slack_inbox().channel_threads, channel_id)


@router.get("/conversations/{channel_id}/agent-context")
async def get_agent_context(channel_id: str, thread_ts: Optional[str] = Query(None, max_length=32)):
    """交给 skill agent 的上下文：thread 全部消息或私信最近 30 条（Markdown + 对话历史）。"""
    return await _run(get_slack_inbox().agent_context, channel_id, thread_ts)


class SlackMarkRequest(BaseModel):
    ts: str = Field(..., min_length=1, max_length=32)


# 标记已读：只写 momo 本地的已读位置，不调 Slack
@router.post("/conversations/{channel_id}/mark")
@limiter.limit("60/minute")
async def mark_conversation(request: Request, channel_id: str, body: SlackMarkRequest):
    return await _run(get_slack_inbox().mark_conversation, channel_id, body.ts)


class SlackMarkItem(BaseModel):
    channel_id: str = Field(..., min_length=1, max_length=32)
    ts: str = Field(..., min_length=1, max_length=32)
    thread_ts: Optional[str] = Field(None, max_length=32)


class SlackMarkAllRequest(BaseModel):
    # 不传 items：动态里全部标已读；传了：只标这些（左栏某个分组的「全部已读」）
    items: Optional[List[SlackMarkItem]] = Field(None, max_length=500)


@router.post("/mark-all")
@limiter.limit("20/minute")
async def mark_all_read(request: Request, body: Optional[SlackMarkAllRequest] = None):
    inbox = get_slack_inbox()
    if body and body.items is not None:
        return await _run(inbox.mark_items_read, [i.model_dump() for i in body.items])
    return await _run(inbox.mark_all_read)


@router.post("/conversations/{channel_id}/threads/{thread_ts}/mark")
@limiter.limit("60/minute")
async def mark_thread(request: Request, channel_id: str, thread_ts: str, body: SlackMarkRequest):
    return await _run(get_slack_inbox().mark_thread, channel_id, thread_ts, body.ts)


@router.get("/conversations/{channel_id}/messages")
async def list_messages(
    channel_id: str,
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None, max_length=200),
):
    return await _run(get_slack_inbox().messages, channel_id, limit, cursor)


@router.get("/conversations/{channel_id}/replies/{thread_ts}")
async def list_replies(channel_id: str, thread_ts: str):
    return await _run(get_slack_inbox().replies, channel_id, thread_ts)


@router.get("/conversations/{channel_id}/export")
@limiter.limit("6/minute")
async def export_conversation(
    request: Request,
    channel_id: str,
    format: Literal["json", "md"] = "md",
):
    data = await _run(get_slack_inbox().export, channel_id)
    stem = f"slack-{data['conversation']['name'] or channel_id}"
    if format == "json":
        body = json.dumps(data, ensure_ascii=False, indent=2)
        media_type, filename = "application/json", f"{stem}.json"
    else:
        body = export_to_markdown(data)
        media_type, filename = "text/markdown; charset=utf-8", f"{stem}.md"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/files/{file_id}")
async def get_file(file_id: str, download: bool = False):
    path, mimetype, name = await _run(get_slack_inbox().file, file_id)
    inline = mimetype in _INLINE_IMAGE_TYPES and not download
    return FileResponse(
        path,
        media_type=mimetype if inline else "application/octet-stream",
        headers={
            "Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(name)}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "Cache-Control": "private, max-age=86400",
        },
    )


# ---------------------------------------------------------------- 轻量 AI：消息中文、thread 中文标题和摘要


@lru_cache(maxsize=1)
def get_slack_ai() -> SlackAI:
    async def llm(prompt: str) -> str:
        return await generate_with_fallback_budget(prompt, task_type="slack")

    async def glossary(text: str) -> str:
        return await run_blocking(build_glossary_context, text)

    return SlackAI(Path(settings.slack_cache_dir) / "ai", llm, parse_llm_json_response, glossary)


async def _run_ai(coro, operation: str):
    try:
        return await coro
    except SlackInboxError as error:
        raise _to_api_error(error) from error
    except ServiceUnavailableException:
        raise
    except (PromptContractError, ValueError):
        raise_empty_llm_result(operation=operation)
    except Exception as exc:  # noqa: BLE001 - 模型调用的任何失败都按服务不可用返回
        raise_llm_service_unavailable(operation=operation, exc=exc)


class SlackTranslateRequest(BaseModel):
    texts: List[str] = Field(..., max_length=MAX_BATCH)
    # thread 根帖：只帮模型理解回复里的指代，不翻译
    context: Optional[str] = Field(None, max_length=MAX_TEXT_CHARS)


@router.post("/ai/translate")
@limiter.limit("60/minute")
async def translate_messages(request: Request, body: SlackTranslateRequest):
    """逐条翻成中文；不需要翻的（中文、只有链接）返回 null。按内容缓存。"""
    texts = [t[:MAX_TEXT_CHARS] for t in body.texts]
    return {"translations": await _run_ai(get_slack_ai().translate(texts, body.context), "Slack 消息翻译")}


@router.get("/conversations/{channel_id}/threads/{thread_ts}/summary")
@limiter.limit("30/minute")
async def thread_summary(request: Request, channel_id: str, thread_ts: str):
    ctx = await _run(get_slack_inbox().agent_context, channel_id, thread_ts)
    key = f"{channel_id}:{thread_ts}:{ctx['latest_ts']}"
    return await _run_ai(get_slack_ai().summary(key, ctx["markdown"]), "Slack thread 摘要")




# ---------------------------------------------------------------- 设置（只存在 momo 本地）

SETTINGS_DEFAULTS = {"auto_translate_mentions": True}


def _settings_path() -> Path:
    return Path(settings.slack_cache_dir) / "settings.json"


def read_slack_settings() -> Dict[str, object]:
    try:
        saved = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return {k: saved.get(k, v) if isinstance(saved.get(k, v), type(v)) else v for k, v in SETTINGS_DEFAULTS.items()}


class SlackSettingsRequest(BaseModel):
    auto_translate_mentions: Optional[bool] = None


@router.get("/settings")
async def get_settings():
    return await run_blocking(read_slack_settings)


@router.put("/settings")
@limiter.limit("20/minute")
async def put_settings(request: Request, body: SlackSettingsRequest):
    def save():
        current = read_slack_settings()
        current.update({k: v for k, v in body.model_dump().items() if v is not None})
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return current

    return await run_blocking(save)


# ---------------------------------------------------------------- 我的待办：未读的 @我 和私信，一次调用


def _draft_index() -> Dict[str, Dict[str, object]]:
    from .post_drafts import get_draft_store  # 避免循环导入

    return get_draft_store().slack_index()


@router.get("/todos")
@limiter.limit("20/minute")
async def my_todos(request: Request):
    """每件找我的事一行「谁要我干什么」；只被群发 @ 到的放进 fyi（不用处理），不送模型。"""
    material = await _run(get_slack_inbox().todo_material)
    direct = [m for m in material if m["direct"]]
    llm_items = [
        {
            "id": i,
            "kind": m["kind"],
            "where": ("私信 · " if m["kind"] == "dm" else "#") + m["channel_name"],
            **({"root": m["root_text"][:800]} if m["kind"] == "mention" else {}),
            "messages": m["messages"],
        }
        for i, m in enumerate(direct)
    ]
    tasks = await _run_ai(get_slack_ai().todo_tasks(llm_items), "我的待办") if llm_items else []
    index = await run_blocking(_draft_index)

    def view(m, task=None):
        mark = {"channel_id": m["channel_id"], "ts": m["latest_ts"]}
        if m["kind"] == "mention":
            mark["thread_ts"] = m["thread_ts"]
        return {
            "kind": m["kind"],
            "channel_id": m["channel_id"],
            "channel_name": m["channel_name"],
            "conversation_kind": m["conversation_kind"],
            "thread_ts": m["thread_ts"],
            "title": m["title"],
            "from": sorted({msg["from"] for msg in m["messages"]}),
            "count": len(m["messages"]),
            "latest_ts": m["latest_ts"],
            "task": (task or {}).get("task") or "",
            "action": (task or {}).get("action") or "read",
            "mark": mark,
            "draft": index.get(f"{m['channel_id']}:{m['thread_ts']}") if m["thread_ts"] else None,
        }

    items = [view(m, tasks[i] if i < len(tasks) else None) for i, m in enumerate(direct)]
    rank = {"reply": 0, "do": 0, "read": 1}
    items.sort(key=lambda it: (rank.get(it["action"], 1), -float(it["latest_ts"])))
    fyi = [view(m) for m in material if not m["direct"]]
    return {"items": items, "fyi": fyi}


# ---------------------------------------------------------------- 私信回复面板的历史（每个私信一个文件）

MAX_REPLY_STATE_BYTES = 300_000


def _reply_state_path(channel_id: str) -> Path:
    if not re.fullmatch(r"[A-Z0-9]{8,12}", channel_id or ""):
        raise APIException(status_code=400, detail="会话 ID 不对", error_code="BAD_CHANNEL")
    return Path(settings.slack_cache_dir) / "dm_replies" / f"{channel_id}.json"


class SlackReplyStateRequest(BaseModel):
    state: Dict[str, object]


@router.get("/conversations/{channel_id}/reply-state")
async def get_reply_state(channel_id: str):
    path = _reply_state_path(channel_id)

    def load():
        try:
            return {"state": json.loads(path.read_text(encoding="utf-8"))}
        except (OSError, ValueError):
            return {"state": None}

    return await run_blocking(load)


@router.put("/conversations/{channel_id}/reply-state")
@limiter.limit("60/minute")
async def put_reply_state(request: Request, channel_id: str, body: SlackReplyStateRequest):
    path = _reply_state_path(channel_id)
    data = json.dumps(body.state, ensure_ascii=False)
    if len(data) > MAX_REPLY_STATE_BYTES:
        raise APIException(status_code=400, detail="回复历史太长了", error_code="REPLY_STATE_TOO_LARGE")

    def save():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
        return {"ok": True}

    return await run_blocking(save)
