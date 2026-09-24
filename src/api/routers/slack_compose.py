"""Slack compose endpoint."""

from fastapi import APIRouter, Request

from src.prompts import get_prompt_manager
from src.prompts.contracts import PromptContractError

from ..middleware import BadRequestException, ServiceUnavailableException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_empty_llm_result, raise_llm_service_unavailable
from ..utils.json_utils import normalize_control_keys, parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback_budget
from .slack_models import (
    ConversationMessage,
    SlackComposeRequest,
    SlackComposeResponse,
    normalize_variants,
)


def format_conversation_history(history: list[ConversationMessage]) -> str:
    """Format conversation history into a readable string."""
    if not history:
        return ""

    lines = ["## Conversation history", ""]
    for msg in history:
        role_label = "[Me]" if msg.role == "me" else "[Them]"
        lines.append(f"{role_label}: {msg.content}")
    lines.append("")

    return "\n".join(lines)


# 中转可能把键名拆行（"english\n"），只对白名单内的键做保守修复。
_VERSION_KEYS = ("versions", "version", "english", "chinese", "style")

router = APIRouter()
prompt_manager = get_prompt_manager()


@router.post(
    "/slack/compose",
    response_model=SlackComposeResponse,
    summary="Translate a Chinese reply draft into English",
    description="Return 3 English reply versions for internal workplace chat.",
    tags=["slack"],
)
@limiter.limit("20/minute")
async def compose_slack_message(
    request: Request,
    body: SlackComposeRequest,
):
    """Translate a Chinese reply draft into 3 English versions."""
    content = body.content.strip()
    if not content:
        raise BadRequestException(detail="content cannot be empty")

    conversation_history_section = format_conversation_history(body.conversation_history)
    prompt = prompt_manager.get(
        "slack_compose",
        context_section="",
        conversation_history_section=conversation_history_section,
        content=content,
    )

    try:
        response_text = await generate_with_fallback_budget(
            prompt,
            task_type="slack",
        )
        data = parse_llm_json_response(response_text)
        if isinstance(data, dict):
            data = normalize_control_keys(data, _VERSION_KEYS)
        if not isinstance(data, dict):
            raise ValueError("model response was not a JSON object")

        versions = normalize_variants(data.get("versions", []), chinese_fallback=content)
        if not any(version.english.strip() for version in versions):
            raise_empty_llm_result(operation="Slack compose")

        return SlackComposeResponse(versions=versions)
    except PromptContractError:
        raise_empty_llm_result(operation="Slack compose")
    except ServiceUnavailableException:
        raise
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack compose", exc=exc)
