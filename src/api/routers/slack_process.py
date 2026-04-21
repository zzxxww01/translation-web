"""Slack process endpoint."""

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
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
    http_request: Request,
    request: SlackProcessRequest,
):
    """Analyze an incoming workplace chat message."""
    message = request.message.strip()
    if not message:
        raise BadRequestException(detail="message cannot be empty")

    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{message}", message)
    else:
        conversation_history_section = format_conversation_history(request.conversation_history)
        prompt = prompt_manager.get(
            "slack_process",
            context_section="",
            conversation_history_section=conversation_history_section,
            message=message,
        )

    try:
        response_text = generate_with_fallback(prompt, task_type="slack")
        data = parse_llm_json_response(response_text)

        translation = str(data.get("translation", "")).strip()
        suggested_replies = normalize_variants(data.get("suggested_replies", []))

        return SlackProcessResponse(
            translation=translation,
            suggested_replies=suggested_replies,
        )
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack process", exc=exc)
