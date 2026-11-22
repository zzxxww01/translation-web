"""
Tools chatbot endpoints: multi-turn chat with an LLM, conversations kept on the server.

- /chat/sessions...：会话存在 data/chat_sessions（src/services/chat_sessions.py），可列出、切换、改名、删除。
  发消息时先存下用户的话，再生成回复；回复失败用户的话还在，页面上点重试走 /reply。
- web_search=true 时用模型自带的联网搜索（src/llm/web_search.py，官方 OpenAI / Gemini），搜不搜由模型决定；
  模型不能联网或搜索失败就照常回答，并在回复下面注明。
- /chat：旧接口（整段对话由页面带来），给还开着旧页面的浏览器用。
History is flattened into one prompt so every configured provider (and the task fallback) works the same way.
"""

from __future__ import annotations

import asyncio
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking, run_llm_blocking
from src.llm.factory import get_task_model_alias
from src.llm.web_search import generate_with_web_search
from src.prompts import get_prompt_manager
from src.services.chat_sessions import ChatSessionError, ChatSessionStore
from src.settings import settings

from ..middleware import APIException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.llm_factory import generate_with_fallback_budget
from .tools_models import MAX_CHAT_MESSAGE_LENGTH, ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()
prompt_manager = get_prompt_manager()

# Only the most recent turns go to the model; long chats stay usable without growing the prompt forever.
MAX_HISTORY_CHARS = 60_000
ROLE_LABELS = {"user": "用户", "assistant": "助手"}
# 联网回答要多等一会儿（搜索 + 读网页常见 20~40 秒）；失败后不联网再答一次
SEARCH_TIMEOUT_SECONDS = 110
SEARCH_HINT = "你可以联网搜索。问题涉及最新消息、新闻、价格、日期或你不确定的事实时，先搜索再回答，并在相关句子后标出来源。\n"
NOTE_NO_SEARCH_MODEL = "这个模型不能联网，回答没有用搜索"
NOTE_SEARCH_FAILED = "联网搜索没成功，这次是不联网回答的"


def build_conversation(messages: List[ChatMessage]) -> str:
    """Render the most recent messages that fit the budget, oldest first."""
    kept: list[str] = []
    used = 0
    for message in reversed(messages):
        block = f"【{ROLE_LABELS[message.role]}】\n{message.content.strip()}"
        if kept and used + len(block) > MAX_HISTORY_CHARS:
            break
        kept.append(block)
        used += len(block)
    return "\n\n".join(reversed(kept))


def render_prompt(messages: List[ChatMessage], web_search: bool = False) -> str:
    return prompt_manager.render(
        "tools_chat",
        conversation=build_conversation(messages),
        today=time.strftime("%Y-%m-%d"),
        search_hint=SEARCH_HINT if web_search else "",
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest):
    """Reply to the last user message. Default model comes from task_defaults.chat."""
    prompt = render_prompt(body.messages)
    try:
        reply = (await generate_with_fallback_budget(prompt, task_type="chat", model=body.model or None)).strip()
    except Exception as e:
        raise_llm_service_unavailable(operation="Chat", exc=e)
    return ChatResponse(reply=reply)


# ---------------------------------------------------------------- 会话


@lru_cache(maxsize=1)
def get_chat_store() -> ChatSessionStore:
    return ChatSessionStore(Path(settings.chat_sessions_dir))


async def _store(func, *args, **kwargs):
    try:
        return await run_blocking(func, *args, **kwargs)
    except ChatSessionError as error:
        raise APIException(status_code=error.status_code, detail=error.message, error_code=error.code) from error


class ImportedMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=MAX_CHAT_MESSAGE_LENGTH * 3)


class CreateSessionRequest(BaseModel):
    # 导入以前存在浏览器里的那段对话
    messages: List[ImportedMessage] = Field(default_factory=list, max_length=400)


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ReplyRequest(BaseModel):
    # 不传 = 用 task_defaults.chat（GPT-6.2 Sol）
    model: Optional[str] = Field(default=None, max_length=100)
    web_search: bool = True


class SendRequest(ReplyRequest):
    content: str = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGE_LENGTH)


async def generate_reply(messages: List[Dict[str, Any]], model: Optional[str], web_search: bool) -> Dict[str, Any]:
    """对最后一条用户消息生成回复：{"content", "model", "sources", "note"}。"""
    history = [ChatMessage.model_construct(role=m["role"], content=m["content"]) for m in messages]
    alias = model or get_task_model_alias("chat")
    note = ""
    if web_search and alias:
        try:
            result = await asyncio.wait_for(
                run_llm_blocking(generate_with_web_search, render_prompt(history, True), alias, SEARCH_TIMEOUT_SECONDS),
                timeout=SEARCH_TIMEOUT_SECONDS + 5)
        except Exception as exc:  # noqa: BLE001 — 搜索失败就不联网再答一次
            logger.warning("[Chat] web search failed for model=%s: %s", alias, type(exc).__name__)
            note = NOTE_SEARCH_FAILED
        else:
            if result is not None:
                return {"content": result["text"].strip(), "model": alias, "sources": result.get("sources") or [], "note": ""}
            note = NOTE_NO_SEARCH_MODEL
    try:
        reply = await generate_with_fallback_budget(render_prompt(history), task_type="chat", model=model or None)
    except Exception as e:
        raise_llm_service_unavailable(operation="Chat", exc=e)
    return {"content": reply.strip(), "model": alias or "", "sources": [], "note": note}


async def _answer(session_id: str, doc: Dict[str, Any], model: Optional[str], web_search: bool) -> Dict[str, Any]:
    reply = await generate_reply(doc["messages"], model, web_search)
    return await _store(get_chat_store().add_reply, session_id, doc["messages"][-1]["id"], reply["content"],
                        model=reply["model"], sources=reply["sources"], note=reply["note"])


@router.get("/chat/sessions")
async def list_sessions():
    return {"sessions": await _store(get_chat_store().list)}


@router.post("/chat/sessions")
async def create_session(body: CreateSessionRequest):
    return await _store(get_chat_store().create, [m.model_dump() for m in body.messages])


@router.get("/chat/sessions/{session_id}")
async def get_session(session_id: str):
    return await _store(get_chat_store().get, session_id)


@router.patch("/chat/sessions/{session_id}")
async def rename_session(session_id: str, body: RenameSessionRequest):
    return await _store(get_chat_store().rename, session_id, body.title)


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    return {"deleted": await _store(get_chat_store().delete, session_id)}


@router.post("/chat/sessions/{session_id}/messages")
@limiter.limit("30/minute")
async def send_message(request: Request, session_id: str, body: SendRequest):
    """存下用户的话，再回复；回复失败时用户的话已经存下了，页面上重试走 /reply。"""
    doc = await _store(get_chat_store().add_user, session_id, body.content)
    return await _answer(session_id, doc, body.model, body.web_search)


@router.post("/chat/sessions/{session_id}/reply")
@limiter.limit("30/minute")
async def reply_again(request: Request, session_id: str, body: ReplyRequest):
    """重新回答最后一个问题（也用于出错后重试）：去掉它后面的回复，再答一次。"""
    doc = await _store(get_chat_store().drop_trailing_replies, session_id)
    return await _answer(session_id, doc, body.model, body.web_search)
