"""Slack refine endpoint - adjust previous results based on user feedback"""
import asyncio
import logging

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager
from src.api.routers.slack_models import SlackRefineRequest, SlackRefineResponse
from src.api.middleware.rate_limit import limiter

from ..utils.llm_factory import generate_with_fallback
from ..utils.llm_errors import raise_llm_service_unavailable

logger = logging.getLogger(__name__)
router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post("/refine")
@limiter.limit("20/minute")
async def refine_result(request: Request, body: SlackRefineRequest) -> SlackRefineResponse:
    """
    Refine a previous Slack result based on user's adjustment instruction.

    Supports two context types:
    - incoming: refining translation or suggested reply from English message
    - draft: refining English translation from Chinese draft
    """
    # Format conversation history
    history_text = ""
    if body.conversation_history:
        history_items = []
        for msg in body.conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_items.append(f"[{role}] {content}")
        history_text = "\n".join(history_items)

    # 通过统一的 prompt_manager 取模板(绝对定位 + 预加载),避免相对路径在不同
    # 工作目录下 FileNotFoundError;并复用 generate_with_fallback 的多 provider 容错。
    prompt = prompt_manager.get(
        "slack_refine",
        original_result=body.original_result,
        adjustment_instruction=body.adjustment_instruction,
        conversation_history=history_text or "无",
        context_type=body.context_type,
    )

    try:
        # 同步 LLM 调用放入线程池,避免阻塞事件循环
        refined_result = await asyncio.to_thread(
            generate_with_fallback, prompt, task_type="slack"
        )
        return SlackRefineResponse(refined_result=refined_result.strip())
    except Exception as exc:
        logger.error(f"Error refining result: {exc}", exc_info=True)
        raise_llm_service_unavailable(operation="Slack refine", exc=exc)
