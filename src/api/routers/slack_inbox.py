"""
Slack 收件箱：展示「我」所在的频道、私信和 thread，支持附件下载和导出。

只读：后端只调白名单里的查询接口，从不发送。唯一的写操作是把我自己的已读位置往前推
（和在 Slack 里看过一样）。见 src/services/slack_inbox.py。
"""

from __future__ import annotations

import json
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


class SlackTitlesRequest(BaseModel):
    # thread_ts -> 根消息原文
    items: Dict[str, str] = Field(..., max_length=MAX_BATCH)


@router.post("/ai/translate")
@limiter.limit("60/minute")
async def translate_messages(request: Request, body: SlackTranslateRequest):
    """逐条翻成中文；不需要翻的（中文、只有链接）返回 null。按内容缓存。"""
    texts = [t[:MAX_TEXT_CHARS] for t in body.texts]
    return {"translations": await _run_ai(get_slack_ai().translate(texts), "Slack 消息翻译")}


@router.post("/ai/titles")
@limiter.limit("30/minute")
async def thread_titles(request: Request, body: SlackTitlesRequest):
    items = {k[:32]: v[:MAX_TEXT_CHARS] for k, v in body.items.items()}
    return {"titles": await _run_ai(get_slack_ai().titles_for(items), "Slack thread 标题")}


@router.get("/conversations/{channel_id}/threads/{thread_ts}/summary")
@limiter.limit("30/minute")
async def thread_summary(request: Request, channel_id: str, thread_ts: str):
    ctx = await _run(get_slack_inbox().agent_context, channel_id, thread_ts)
    key = f"{channel_id}:{thread_ts}:{ctx['latest_ts']}"
    return await _run_ai(get_slack_ai().summary(key, ctx["markdown"]), "Slack thread 摘要")
