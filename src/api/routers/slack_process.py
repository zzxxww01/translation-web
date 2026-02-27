"""
Slack process endpoint.
"""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_dependencies import ConversationManagerDep
from .slack_models import SlackProcessRequest, SlackProcessResponse


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/process",
    response_model=SlackProcessResponse,
    summary="处理 Slack 消息",
    description="接收 Slack 消息，提供翻译和回复建议（支持对话记忆）",
    tags=["slack"],
    response_description="包含翻译后的消息和建议回复（中英文）",
    responses={
        200: {
            "description": "处理成功",
            "content": {
                "application/json": {
                    "example": {
                        "translation": "嗨 Tom，项目进展顺利！预计周三完成。",
                        "suggested_reply_cn": "太棒了，期待你的成果！",
                        "suggested_reply_en": "Great! Looking forward to your results.",
                    }
                }
            },
        },
        400: {"description": "消息为空"},
        503: {"description": "LLM 服务不可用"},
    },
)
async def process_slack_message(
    request: SlackProcessRequest,
    cm: ConversationManagerDep,
):
    """处理 Slack 消息（带对话记忆）。"""
    if not request.message.strip():
        raise BadRequestException(detail="消息不能为空")

    history_context = ""
    conv_style = "casual"
    if request.conversation_id:
        conv = cm.get(request.conversation_id)
        if not conv:
            cm.create(
                conv_id=request.conversation_id,
                name=f"Conversation {request.conversation_id}",
                style="casual",
            )
            conv = cm.get(request.conversation_id)
        if conv:
            conv_style = conv.config.style
            history_context = conv.get_context_for_prompt(max_messages=5)

    context_parts = []
    if conv_style == "professional":
        context_parts.append(
            "## Tone Preference\n"
            "Use a polite professional but still relaxed workplace tone (礼貌专业，但不过于正式)."
        )
    if history_context:
        context_parts.append(
            f"""
## 对话历史（参考上下文）
{history_context}
"""
        )
    context_section = "\n\n".join(context_parts)

    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{message}", request.message)
    else:
        prompt = prompt_manager.get(
            "slack_process",
            context_section=context_section,
            message=request.message,
        )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        translation = data.get("translation", "")
        super_casual = data.get("super_casual", "")
        super_casual_cn = data.get("super_casual_cn", "")
        friendly_pro = data.get("friendly_pro", "")
        friendly_pro_cn = data.get("friendly_pro_cn", "")
        polite_casual = data.get("polite_casual", "")
        polite_casual_cn = data.get("polite_casual_cn", "")

        if request.conversation_id:
            cm.add_message(
                request.conversation_id,
                "them",
                request.message,
                translation,
            )

        return SlackProcessResponse(
            translation=translation,
            super_casual=super_casual,
            super_casual_cn=super_casual_cn,
            friendly_pro=friendly_pro,
            friendly_pro_cn=friendly_pro_cn,
            polite_casual=polite_casual,
            polite_casual_cn=polite_casual_cn,
        )
    except Exception as e:
        raise ServiceUnavailableException(detail=f"处理失败: {str(e)}")
