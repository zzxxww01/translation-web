"""Slack process endpoint."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_models import (
    SlackProcessRequest,
    SlackProcessResponse,
    normalize_variants,
)


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/process",
    response_model=SlackProcessResponse,
    summary="Analyze an incoming Slack message",
    description="Translate the other person's message into Chinese and suggest 3 English replies.",
    tags=["slack"],
)
async def process_slack_message(
    request: SlackProcessRequest,
):
    """Analyze an incoming workplace chat message."""
    message = request.message.strip()
    if not message:
        raise BadRequestException(detail="message cannot be empty")

    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{message}", message)
    else:
        prompt = prompt_manager.get(
            "slack_process",
            context_section="",
            message=message,
        )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        translation = str(data.get("translation", "")).strip()
        suggested_replies = normalize_variants(data.get("suggested_replies", []))

        return SlackProcessResponse(
            translation=translation,
            suggested_replies=suggested_replies,
        )
    except Exception as exc:
        raise ServiceUnavailableException(detail=f"process failed: {exc}") from exc
