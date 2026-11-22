"""
Tools chatbot endpoint: plain multi-turn chat with an LLM.

The page keeps the conversation; each request sends the whole history (capped) and gets one reply.
History is flattened into one prompt so every configured provider (and the task fallback) works the same way.
"""

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager

from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.llm_factory import generate_with_fallback_budget
from .tools_models import ChatMessage, ChatRequest, ChatResponse

router = APIRouter()
prompt_manager = get_prompt_manager()

# Only the most recent turns go to the model; long chats stay usable without growing the prompt forever.
MAX_HISTORY_CHARS = 60_000
ROLE_LABELS = {"user": "用户", "assistant": "助手"}


def build_conversation(messages: list[ChatMessage]) -> str:
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


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest):
    """Reply to the last user message. Default model comes from task_defaults.chat."""
    prompt = prompt_manager.render("tools_chat", conversation=build_conversation(body.messages))
    try:
        reply = (await generate_with_fallback_budget(prompt, task_type="chat", model=body.model or None)).strip()
    except Exception as e:
        raise_llm_service_unavailable(operation="Chat", exc=e)
    return ChatResponse(reply=reply)
