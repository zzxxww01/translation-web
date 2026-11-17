"""
Slack 收件箱：展示「我」所在的频道、私信和 thread，支持附件下载和导出。

只读：后端只调白名单里的查询接口，从不发送。唯一的写操作是把我自己的已读位置往前推
（和在 Slack 里看过一样）。见 src/services/slack_inbox.py。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking
from src.services.slack_inbox import (
    SlackCredentialStore,
    SlackInbox,
    SlackInboxError,
    export_to_markdown,
)
from src.settings import settings

from ..middleware import APIException
from ..middleware.rate_limit import limiter


router = APIRouter(prefix="/slack-inbox")

# 浏览器里直接内联显示的图片类型；其余一律当附件下载，避免 HTML/SVG 在 momo 域名下执行
_INLINE_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@lru_cache(maxsize=1)
def get_slack_inbox() -> SlackInbox:
    return SlackInbox(
        SlackCredentialStore(Path(settings.slack_credentials_file)),
        cache_dir=Path(settings.slack_cache_dir),
        dm_recent_days=settings.slack_dm_recent_days,
    )


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


@router.post("/conversations/{channel_id}/mark")
@limiter.limit("60/minute")
async def mark_conversation(request: Request, channel_id: str, body: SlackMarkRequest):
    return await _run(get_slack_inbox().mark_conversation, channel_id, body.ts)


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
