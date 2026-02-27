"""
Slack sync and optimize endpoints.
"""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_dependencies import ConversationManagerDep
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
    summary="同步中文回复到英文",
    description="当用户修改了中文回复后，重新翻译为英文",
    tags=["slack"],
    response_description="翻译后的英文回复",
    responses={
        200: {
            "description": "翻译成功",
            "content": {
                "application/json": {
                    "example": {"english_reply": "Sure, I'll finish it by Wednesday."}
                }
            },
        },
        400: {"description": "中文回复为空"},
        503: {"description": "LLM 服务不可用"},
    },
)
async def sync_reply(request: SlackSyncRequest):
    """同步中文回复到英文。"""
    if not request.chinese_reply.strip():
        raise BadRequestException(detail="中文回复不能为空")

    prompt = prompt_manager.get(
        "slack_sync",
        chinese_reply=request.chinese_reply,
    )

    try:
        response_text = generate_with_fallback(prompt)
        return SlackSyncResponse(english_reply=response_text.strip())
    except Exception as e:
        raise ServiceUnavailableException(detail=f"同步失败: {str(e)}")


@router.post(
    "/slack/optimize",
    response_model=SlackOptimizeResponse,
    summary="优化文本内容",
    description="对中文或英文文本进行翻译优化、语法纠正或语调调整",
    tags=["slack"],
    response_description="优化后的文本及改进说明",
    responses={
        200: {
            "description": "优化成功",
            "content": {
                "application/json": {
                    "example": {
                        "optimized_text": "Sure, I'll have it ready by tomorrow afternoon.",
                        "improvements": ["优化了语调使其更专业", "调整了时间表达更加准确"],
                        "confidence": 0.92,
                    }
                }
            },
        },
        400: {"description": "内容为空或参数不正确"},
        503: {"description": "LLM 服务不可用"},
    },
)
async def optimize_text(
    request: SlackOptimizeRequest,
    cm: ConversationManagerDep,
):
    """文本优化功能。"""
    if not request.content.strip():
        raise BadRequestException(detail="内容不能为空")

    if request.target_language not in ["en", "cn"]:
        raise BadRequestException(detail="目标语言必须是 'en' 或 'cn'")

    if request.context_type not in ["translation", "grammar", "tone", "formality"]:
        raise BadRequestException(detail="优化类型不正确")

    history_context = ""
    if request.conversation_id:
        conv = cm.get(request.conversation_id)
        if conv:
            history_context = conv.get_context_for_prompt(max_messages=3)

    context_section = ""
    if history_context:
        context_section = f"""
## 对话上下文
{history_context}
"""

    prompt_template_map = {
        "translation": "slack_optimize_translation",
        "grammar": "slack_optimize_grammar",
        "tone": "slack_optimize_tone",
        "formality": "slack_optimize_formality",
    }
    prompt_name = prompt_template_map[request.context_type]

    prompt = prompt_manager.get(
        prompt_name,
        context_section=context_section,
        content=request.content,
        target_language=request.target_language,
        original_text=request.original_text if request.original_text else "无",
    )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        optimized_text = data.get("optimized_text", request.content)
        improvements = data.get("improvements", ["文本已优化"])
        confidence = float(data.get("confidence", 0.8))
        confidence = max(0.0, min(1.0, confidence))

        return SlackOptimizeResponse(
            optimized_text=optimized_text,
            improvements=improvements,
            confidence=confidence,
        )
    except Exception as e:
        raise ServiceUnavailableException(detail=f"优化失败: {str(e)}")
