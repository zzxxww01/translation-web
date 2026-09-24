"""Slack sync and optimize endpoints."""

from fastapi import APIRouter

from src.prompts import get_prompt_manager
from src.prompts.contracts import PromptContractError

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.llm_errors import raise_empty_llm_result, raise_llm_service_unavailable
from ..utils.json_utils import normalize_control_keys, parse_llm_json_response

from ..utils.llm_factory import generate_with_fallback_budget
from .slack_models import (
    SlackOptimizeRequest,
    SlackOptimizeResponse,
    SlackSyncRequest,
    SlackSyncResponse,
)


# 中转可能把键名拆行，只对白名单内的键做保守修复。
_OPTIMIZE_KEYS = ("optimized_text", "improvements", "confidence")

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
        response_text = await generate_with_fallback_budget(
            prompt,
            task_type="slack",
        )
        english_reply = response_text.strip()
        if not english_reply:
            raise_empty_llm_result(operation="Slack sync")
        return SlackSyncResponse(english_reply=english_reply)
    except PromptContractError:
        raise_empty_llm_result(operation="Slack optimize")
    except ServiceUnavailableException:
        raise
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack sync", exc=exc)


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
        response_text = await generate_with_fallback_budget(
            prompt,
            task_type="slack",
        )
        data = parse_llm_json_response(response_text)
        if isinstance(data, dict):
            data = normalize_control_keys(data, _OPTIMIZE_KEYS)
        if not isinstance(data, dict):
            raise ValueError("model response was not a JSON object")


        optimized_text = data.get("optimized_text")
        improvements = data.get("improvements")
        if not isinstance(optimized_text, str) or not optimized_text.strip() or not isinstance(improvements, list) or any(not isinstance(x, str) for x in improvements):
            raise ValueError("Invalid optimization response")
        if request.context_type == "translation" and not request.original_text:
            improvements.append("未提供原文，仅作语言润色，未核验忠实性。")
        confidence = float(data.get("confidence", 0.0))

        import math
        if not math.isfinite(confidence):
            raise ValueError("Invalid confidence")
        confidence = max(0.0, min(1.0, confidence))

        return SlackOptimizeResponse(
            optimized_text=optimized_text,
            improvements=improvements,
            confidence=confidence,
        )
    except PromptContractError:
        raise_empty_llm_result(operation="Slack optimize")
    except ServiceUnavailableException:
        raise
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack optimize", exc=exc)
