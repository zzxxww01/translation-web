"""Slack process endpoint."""

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_empty_llm_result, raise_llm_service_unavailable
from ..utils.json_utils import normalize_control_keys, parse_llm_json_response, unwrap_relay_lines
from ..utils.llm_factory import generate_with_fallback_budget
from .slack_models import (
    ConversationMessage,
    SlackProcessRequest,
    SlackProcessResponse,
    normalize_variants,
)


def format_conversation_history(history: list[ConversationMessage]) -> str:
    """Format conversation history into a readable string."""
    if not history:
        return ""

    lines = ["## Conversation history", ""]
    for msg in history:
        role_label = "[Me]" if msg.role == "me" else "[Them]"
        lines.append(f"{role_label}: {msg.content}")
    lines.append("")

    return "\n".join(lines)


# 中转可能把键名拆行（"english\n"），只对白名单内的键做保守修复。
_REPLY_KEYS = ("translation", "suggested_replies", "version", "english", "chinese", "style")

router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/process",
    response_model=SlackProcessResponse,
    summary="Analyze an incoming Slack message",
    description="Translate the other person's message into Chinese and suggest 3 English replies.",
    tags=["slack"],
)
@limiter.limit("20/minute")
async def process_slack_message(
    request: Request,
    body: SlackProcessRequest,
):
    """Analyze an incoming workplace chat message."""
    message = body.message.strip()
    if not message:
        raise BadRequestException(detail="message cannot be empty")

    if body.custom_prompt:
        prompt = body.custom_prompt.replace("{message}", message)
    else:
        conversation_history_section = format_conversation_history(body.conversation_history)
        prompt = prompt_manager.get(
            "slack_process",
            context_section="",
            conversation_history_section=conversation_history_section,
            message=message,
        )

    try:
        response_text = await generate_with_fallback_budget(
            prompt,
            task_type="slack",
        )
        data = parse_llm_json_response(response_text)
        if isinstance(data, dict):
            data = normalize_control_keys(data, _REPLY_KEYS)
        if not isinstance(data, dict):
            raise ValueError("model response was not a JSON object")

        translation = unwrap_relay_lines(str(data.get("translation", "")).strip())
        suggested_replies = normalize_variants(data.get("suggested_replies", []))
        if not translation or not any(reply.english.strip() for reply in suggested_replies):
            # 空结果必须显式失败：200 + 空字段会让 CLI/前端把失败当成成功。
            raise_empty_llm_result(operation="Slack process")

        return SlackProcessResponse(
            translation=translation,
            suggested_replies=suggested_replies,
        )
    except ServiceUnavailableException:
        raise
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack process", exc=exc)
