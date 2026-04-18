"""Slack compose endpoint."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_models import (
    ConversationMessage,
    SlackComposeRequest,
    SlackComposeResponse,
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
    "/slack/compose",
    response_model=SlackComposeResponse,
    summary="Translate a Chinese reply draft into English",
    description="Return 3 English reply versions for internal workplace chat.",
    tags=["slack"],
)
async def compose_slack_message(
    request: SlackComposeRequest,
):
    """Translate a Chinese reply draft into 3 English versions."""
    content = request.content.strip()
    if not content:
        raise BadRequestException(detail="content cannot be empty")

    conversation_history_section = format_conversation_history(request.conversation_history)
    prompt = prompt_manager.get(
        "slack_compose",
        context_section="",
        conversation_history_section=conversation_history_section,
        content=content,
    )

    try:
        response_text = generate_with_fallback(prompt, task_type="slack")
        data = parse_llm_json_response(response_text)
        versions = normalize_variants(data.get("versions", []), chinese_fallback=content)
        return SlackComposeResponse(versions=versions)
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack compose", exc=exc)
