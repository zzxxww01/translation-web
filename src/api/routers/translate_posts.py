"""
Translate post/title endpoints.
"""

import asyncio
import os

from fastapi import APIRouter

from src.prompts import get_prompt_manager
from ..middleware import BadRequestException
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.glossary import build_glossary_context
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .translate_models import (
    GenerateTitleRequest,
    GenerateTitleResponse,
    PostOptimizeRequest,
    PostOptimizeResponse,
    PostTranslateRequest,
    PostTranslateResponse,
    resolve_post_optimize_instruction,
)


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post("/translate/post", response_model=PostTranslateResponse)
async def translate_post(request: PostTranslateRequest):
    """Translate a post to Chinese."""
    if not request.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    glossary_context = build_glossary_context(request.content)

    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{content}", request.content)
        prompt = prompt.replace("{glossary}", glossary_context)
    else:
        prompt = prompt_manager.get(
            "post_translation",
            text=request.content,
            dynamic_sections=glossary_context.strip(),
        )

    timeout_s = int(
        os.getenv("POST_TRANSLATE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "60"))
    )
    try:
        translation = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt, model=request.model),
            timeout=timeout_s,
        )
        return PostTranslateResponse(translation=translation.strip())
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Translation", exc=e, timeout_s=timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Translation", exc=e, timeout_s=timeout_s)


@router.post("/translate/post/optimize", response_model=PostOptimizeResponse)
async def optimize_post_translation(request: PostOptimizeRequest):
    """Optimize an existing translation."""
    if not request.current_translation.strip():
        raise BadRequestException(detail="Current translation cannot be empty")

    resolved_instruction = resolve_post_optimize_instruction(
        request.instruction, request.option_id
    )
    if not resolved_instruction:
        raise BadRequestException(
            detail="Either instruction or a valid option_id must be provided"
        )

    glossary_context = build_glossary_context(request.original_text)

    prompt = prompt_manager.get(
        "post_optimize",
        glossary_section=glossary_context.strip(),
        original_text=request.original_text,
        current_translation=request.current_translation,
        instruction=resolved_instruction,
    )

    timeout_s = int(
        os.getenv("POST_OPTIMIZE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "60"))
    )
    try:
        optimized = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt, model=request.model),
            timeout=timeout_s,
        )
        return PostOptimizeResponse(optimized_translation=optimized.strip())
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Optimization", exc=e, timeout_s=timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Optimization", exc=e, timeout_s=timeout_s)


@router.post("/generate/title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest):
    """Generate 6 title options in JSON format."""
    if not request.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    normalized_instruction = (
        (request.instruction or "").strip()
        or "在忠实内容的前提下，尽量更有吸引力、更有记忆点。"
    )
    prompt = prompt_manager.get(
        "post_title",
        content=request.content,
        instruction=normalized_instruction,
    )

    timeout_s = int(os.getenv("POST_TITLE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "30")))
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt, model=request.model),
            timeout=timeout_s,
        )
        data = parse_llm_json_response(result)
        titles = [
            data.get("suspense", ""),
            data.get("data", ""),
            data.get("counter_intuitive", ""),
            data.get("pain_point", ""),
            data.get("minimal", ""),
            data.get("contrast", ""),
            data.get("free_1", ""),
            data.get("free_2", ""),
        ]
        titles = [title for title in titles if title]
        return GenerateTitleResponse(title="\n".join(titles))
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Title generation", exc=e, timeout_s=timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Title generation", exc=e, timeout_s=timeout_s)
