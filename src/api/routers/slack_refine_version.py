"""Slack refine version endpoint."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.llm_factory import generate_with_fallback
from .slack_models import SlackReplyVariant

router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/refine-version",
    response_model=SlackReplyVariant,
    summary="Refine a single reply version",
    description="Translate updated Chinese text to English while preserving the style.",
    tags=["slack"],
)
async def refine_version(
    version: str,
    chinese: str,
    style: str,
):
    """Refine a single reply version based on updated Chinese text."""
    chinese = chinese.strip()
    if not chinese:
        raise BadRequestException(detail="chinese cannot be empty")

    if version not in ("A", "B", "C"):
        raise BadRequestException(detail="version must be A, B, or C")

    if style not in ("简洁", "正式", "友好"):
        raise BadRequestException(detail="style must be 简洁, 正式, or 友好")

    prompt = prompt_manager.get(
        "slack_refine_version",
        chinese=chinese,
        style=style,
    )

    try:
        english = generate_with_fallback(prompt, task_type="slack").strip()

        return SlackReplyVariant(
            version=version,
            english=english,
            chinese=chinese,
            style=style,
        )
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack refine version", exc=exc)
