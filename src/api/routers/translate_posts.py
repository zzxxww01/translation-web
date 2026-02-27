"""
Translate post/title endpoints.
"""

import asyncio
import os

from fastapi import APIRouter

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.glossary import build_glossary_context
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from src.prompts.prompt_builder import get_prompt_builder
from .translate_models import (
    GenerateTitleRequest,
    GenerateTitleResponse,
    PostOptimizeRequest,
    PostOptimizeResponse,
    PostTranslateRequest,
    PostTranslateResponse,
)


router = APIRouter()


@router.post("/translate/post", response_model=PostTranslateResponse)
async def translate_post(request: PostTranslateRequest):
    """Translate a post to Chinese."""
    if not request.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    glossary_context = build_glossary_context()

    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{content}", request.content)
        prompt = prompt.replace("{glossary}", glossary_context)
    else:
        prompt_builder = get_prompt_builder(style="original")
        prompt = prompt_builder.template.format(
            text=request.content,
            dynamic_sections=glossary_context.strip(),
        )

    timeout_s = int(os.getenv("POST_TRANSLATE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "60")))
    try:
        translation = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt),
            timeout=timeout_s,
        )
        return PostTranslateResponse(translation=translation.strip())
    except asyncio.TimeoutError:
        raise ServiceUnavailableException(detail=f"Translation timed out after {timeout_s}s")
    except Exception as e:
        raise ServiceUnavailableException(detail=f"Translation failed: {str(e)}")


@router.post("/translate/post/optimize", response_model=PostOptimizeResponse)
async def optimize_post_translation(request: PostOptimizeRequest):
    """Optimize an existing translation."""
    if not request.current_translation.strip():
        raise BadRequestException(detail="Current translation cannot be empty")
    if not request.instruction.strip():
        raise BadRequestException(detail="Instruction cannot be empty")

    context = ""
    if request.conversation_history:
        recent_history = request.conversation_history[-3:]
        if recent_history:
            context = "\n\nConversation History:\n"
            for msg in recent_history:
                role = "User" if msg.get("role") == "user" else "AI"
                content = msg.get("content", "")
                context += f"{role}: {content}\n"

    prompt = f"""You are a professional translation editor.
Improve the translation based on the user's instruction.

Original:
{request.original_text}

Current Translation:
{request.current_translation}

{context}

Instruction:
{request.instruction}

Do not use any Markdown tags or formatting (no headings, lists, code blocks, or bold markers).
Output only the improved translation.
"""

    timeout_s = int(os.getenv("POST_OPTIMIZE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "60")))
    try:
        optimized = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt),
            timeout=timeout_s,
        )
        return PostOptimizeResponse(optimized_translation=optimized.strip())
    except asyncio.TimeoutError:
        raise ServiceUnavailableException(detail=f"Optimization timed out after {timeout_s}s")
    except Exception as e:
        raise ServiceUnavailableException(detail=f"Optimization failed: {str(e)}")


@router.post("/generate/title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest):
    """Generate 6 title options in JSON format."""
    if not request.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    prompt = f"""You are a professional editor. Generate 6 distinct Chinese titles for the content.
Hard constraint: each title must be no more than 20 Chinese characters (20字以内). If a title exceeds 20 Chinese characters, it is invalid and must be rewritten to fit.
Keep them concise (prefer 12-18 characters), avoid long clauses, and avoid extra punctuation.
Titles should be more interesting and engaging. Prefer vivid, specific wording, curiosity gap, and light wordplay; avoid bland or generic titles.
Return strict JSON with keys: suspense, data, counter_intuitive, pain_point, minimal, metaphor. Do not use Markdown tags, code fences, or extra text.

Content:
{request.content}
"""

    timeout_s = int(os.getenv("POST_TITLE_TIMEOUT", os.getenv("GEMINI_TIMEOUT", "30")))
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(generate_with_fallback, prompt),
            timeout=timeout_s,
        )
        data = parse_llm_json_response(result)
        titles = [
            data.get("suspense", ""),
            data.get("data", ""),
            data.get("counter_intuitive", ""),
            data.get("pain_point", ""),
            data.get("minimal", ""),
            data.get("metaphor", ""),
        ]
        titles = [title for title in titles if title]
        return GenerateTitleResponse(title="\n".join(titles))
    except asyncio.TimeoutError:
        raise ServiceUnavailableException(detail=f"Title generation timed out after {timeout_s}s")
    except Exception as e:
        raise ServiceUnavailableException(detail=f"Title generation failed: {str(e)}")
