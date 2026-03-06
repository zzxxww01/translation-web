"""Slack sync and optimize endpoints."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_models import (
    SlackOptimizeRequest,
    SlackOptimizeResponse,
    SlackSyncRequest,
    SlackSyncResponse,
)


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/sync",
    response_model=SlackSyncResponse,
    summary="Translate an edited Chinese reply back to English",
    description="Sync a manually edited Chinese reply with a fresh English version.",
    tags=["slack"],
)
async def sync_reply(request: SlackSyncRequest):
    """Translate an edited Chinese reply back to English."""
    if not request.chinese_reply.strip():
        raise BadRequestException(detail="chinese_reply cannot be empty")

    prompt = prompt_manager.get(
        "slack_sync",
        chinese_reply=request.chinese_reply,
    )

    try:
        response_text = generate_with_fallback(prompt)
        return SlackSyncResponse(english_reply=response_text.strip())
    except Exception as exc:
        raise ServiceUnavailableException(detail=f"sync failed: {exc}") from exc


@router.post(
    "/slack/optimize",
    response_model=SlackOptimizeResponse,
    summary="Optimize Slack text",
    description="Polish translation, grammar, tone, or formality for a Slack draft.",
    tags=["slack"],
)
async def optimize_text(request: SlackOptimizeRequest):
    """Optimize Slack text without any conversation context."""
    if not request.content.strip():
        raise BadRequestException(detail="content cannot be empty")

    if request.target_language not in ["en", "cn"]:
        raise BadRequestException(detail="target_language must be 'en' or 'cn'")

    if request.context_type not in ["translation", "grammar", "tone", "formality"]:
        raise BadRequestException(detail="context_type is invalid")

    prompt_template_map = {
        "translation": "slack_optimize_translation",
        "grammar": "slack_optimize_grammar",
        "tone": "slack_optimize_tone",
        "formality": "slack_optimize_formality",
    }
    prompt_name = prompt_template_map[request.context_type]

    prompt = prompt_manager.get(
        prompt_name,
        context_section="",
        content=request.content,
        target_language=request.target_language,
        original_text=request.original_text if request.original_text else "N/A",
    )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        optimized_text = data.get("optimized_text", request.content)
        improvements = data.get("improvements", ["Text optimized"])
        confidence = float(data.get("confidence", 0.8))
        confidence = max(0.0, min(1.0, confidence))

        return SlackOptimizeResponse(
            optimized_text=optimized_text,
            improvements=improvements,
            confidence=confidence,
        )
    except Exception as exc:
        raise ServiceUnavailableException(detail=f"optimize failed: {exc}") from exc
