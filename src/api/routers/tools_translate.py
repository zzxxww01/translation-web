"""
Tools text-translation endpoint.
"""

import re

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.llm_factory import generate_with_fallback
from .tools_models import TranslateRequest, TranslateResponse


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit("20/minute")
async def translate_text(request: Request, body: TranslateRequest):
    """
    文本翻译 API

    支持:
    - 中英互译
    - 自动检测语言
    """
    if not body.text.strip():
        raise BadRequestException(detail="文本不能为空")

    if body.source_lang == "auto":
        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", body.text))
        target_lang = "en" if has_chinese else "zh"
    else:
        target_lang = body.target_lang

    if target_lang == "zh":
        prompt = prompt_manager.get("tools_translate_en2cn", text=body.text)
    else:
        prompt = prompt_manager.get("tools_translate_cn2en", text=body.text)

    try:
        translation = generate_with_fallback(prompt).strip()
        for prefix in ["翻译结果", "译文:", "Translation:", "翻译:", "译文：", "Translation："]:
            if translation.startswith(prefix):
                translation = translation[len(prefix):].strip()
        return TranslateResponse(translation=translation)
    except Exception as e:
        raise_llm_service_unavailable(operation="Translation", exc=e)
