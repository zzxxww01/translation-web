"""
Translate post/title endpoints.
"""

import asyncio
import os

from fastapi import APIRouter

from src.prompts import get_prompt_manager
from ..middleware import BadRequestException, ServiceUnavailableException
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
)


router = APIRouter()
prompt_manager = get_prompt_manager()


def _build_title_prompt(content: str, instruction: str) -> str:
    normalized_instruction = instruction.strip() or "在忠实内容的前提下，尽量更有吸引力、更有记忆点。"
    return f"""你是semiAnalysis中文编辑，负责生成高质量中文标题。

【内容】
{content}

【用户要求】
{normalized_instruction}

【固定要求】
1. 忠实原文：不能虚构事实、不能改变结论、不能夸张误导。
2. 长度约束：每个标题必须 <= 20 个汉字，建议 12-18 个字。
3. 风格约束：简洁有信息量，避免空泛口号和模板化措辞。
4. 表达要求：可适度增强可读性与吸引力，但不能偏离内容核心。
5. 禁止项：不要输出解释，不要输出Markdown，不要加编号前缀。

请返回严格 JSON，包含以下键：
{{
  "suspense": "...",
  "data": "...",
  "counter_intuitive": "...",
  "pain_point": "...",
  "minimal": "...",
  "metaphor": "..."
}}
"""


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
        prompt = prompt_manager.get(
            "post_translation",
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

    prompt = f"""你是semiAnalysis的中文编辑，优化semiAnalysis帖子的翻译质量。

## 原文
{request.original_text}

## 当前译文
{request.current_translation}
{context}
## 优化要求
{request.instruction}

## 优化原则
1. 以原文为准对照校对，发现与原文不一致或错误之处必须纠正
2. 保留分析师语气：原文的观点、判断、锐度不要弱化或磨平
3. 消除翻译腔：拆长句、去被动、减连接词、调中文语序、直接用动词
4. 术语处理：产品/技术代号保留英文（CoWoS、HBM、EUV），行业术语用中文（晶圆代工、良率、制程节点），金融术语用中文（营收、毛利率、资本支出）
5. 译文不要比原文更长，保持帖子的简洁和冲击力
6. 不要口水话、不要宣传腔、不遗漏信息

严禁使用任何Markdown语法标记。直接输出优化后的完整译文，不要任何解释。
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

    prompt = _build_title_prompt(request.content, request.instruction or "")

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
