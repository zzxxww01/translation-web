"""Slack compose endpoint."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_models import SlackComposeRequest, SlackComposeResponse, normalize_variants


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

    prompt = prompt_manager.get(
        "slack_compose",
        context_section="",
        content=content,
    )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)
        versions = normalize_variants(data.get("versions", []), chinese_fallback=content)
        return SlackComposeResponse(versions=versions)
    except Exception as exc:
        raise ServiceUnavailableException(detail=f"generation failed: {exc}") from exc
