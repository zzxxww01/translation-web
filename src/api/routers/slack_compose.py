"""
Slack compose endpoint.
"""

from fastapi import APIRouter

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException, ServiceUnavailableException
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .slack_dependencies import ConversationManagerDep
from .slack_models import SlackComposeRequest, SlackComposeResponse


router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/compose",
    response_model=SlackComposeResponse,
    summary="撰写 Slack 消息",
    description="将中文内容翻译为英文，提供 3 种风格（随意/专业/正式）",
    tags=["slack"],
    response_description="三种不同风格的英文版本",
    responses={
        200: {
            "description": "生成成功",
            "content": {
                "application/json": {
                    "example": {
                        "casual": "Hey! The bug's fixed, tested it and looks good.",
                        "professional": "Hi, the bug has been fixed and tested successfully.",
                        "formal": "Dear team, I am pleased to inform you that the bug has been resolved and thoroughly tested.",
                    }
                }
            },
        },
        400: {"description": "内容为空"},
        503: {"description": "LLM 服务不可用"},
    },
)
async def compose_slack_message(
    request: SlackComposeRequest,
    cm: ConversationManagerDep,
):
    """主动发送模式：中译英（3种风格）。"""
    if not request.content.strip():
        raise BadRequestException(detail="内容不能为空")

    allowed_tones = {"all", "casual", "professional", "formal"}
    if request.tone not in allowed_tones:
        raise BadRequestException(detail="tone 参数不正确")

    history_context = ""
    if request.conversation_id:
        conv = cm.get(request.conversation_id)
        if conv:
            history_context = conv.get_context_for_prompt(max_messages=5)

    context_section = ""
    if history_context:
        context_section = f"""
## Conversation History (Context)
{history_context}
"""

    prompt = prompt_manager.get(
        "slack_compose",
        context_section=context_section,
        content=request.content,
    )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        return SlackComposeResponse(
            casual=data.get("casual", ""),
            professional=data.get("professional", ""),
            formal=data.get("formal", ""),
        )
    except Exception as e:
        raise ServiceUnavailableException(detail=f"Generation failed: {str(e)}")
