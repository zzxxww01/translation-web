"""
Tools email-reply endpoint.
"""

import html
import re

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager

from ..middleware import BadRequestException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .tools_models import EmailReplyRequest, EmailReplyResponse


router = APIRouter()
prompt_manager = get_prompt_manager()


def sanitize_email_input(text: str) -> str:
    """清洗邮件输入，防止 prompt 注入"""
    if not text:
        return ""
    # HTML 转义
    text = html.escape(text)
    # 限制连续换行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return text


@router.post("/email-reply", response_model=EmailReplyResponse)
@limiter.limit("10/minute")
async def generate_email_reply(request: Request, body: EmailReplyRequest):
    """
    邮件回复建议 API

    根据收到的邮件内容生成多种风格的回复建议
    """
    if not body.content.strip():
        raise BadRequestException(detail="邮件内容不能为空")

    # 清洗输入，防止 prompt 注入
    content = sanitize_email_input(body.content)
    sender = sanitize_email_input(body.sender) if body.sender else ""
    subject = sanitize_email_input(body.subject) if body.subject else ""

    style_descriptions = {
        "professional": "专业正式 - 适合商务场合，表达得体、逻辑清晰",
        "polite": "礼貌友好 - 语气温和，注重关系维护",
        "casual": "随意亲切 - 适合熟悉的同事或合作伙伴",
    }
    style_desc = style_descriptions.get(body.style, "专业正式")

    context = []
    if sender:
        context.append(f"- 发件人: {sender}")
    if subject:
        context.append(f"- 主题: {subject}")
    context_info = "\n".join(context) if context else "（无额外信息）"

    prompt = prompt_manager.get(
        "tools_email_reply",
        context_info=context_info,
        content=content,
        style_desc=style_desc,
    )

    try:
        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        replies = data.get("replies", [])
        if not replies:
            replies = [
                {"type": "确认收到", "content": "您好，已收到您的邮件，我会尽快处理。如有问题会再与您联系。"},
                {"type": "简单回复", "content": "收到，谢谢。"},
                {"type": "需要时间", "content": "收到您的邮件。我需要一些时间查看相关信息，稍后给您回复。"},
            ]

        return EmailReplyResponse(replies=replies)
    except Exception as e:
        raise_llm_service_unavailable(operation="Email reply generation", exc=e)
