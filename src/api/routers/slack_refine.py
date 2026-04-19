"""Slack refine endpoint - adjust previous results based on user feedback"""
from fastapi import APIRouter
from src.api.routers.slack_models import SlackRefineRequest, SlackRefineResponse
from src.llm.llm import get_llm_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refine")
async def refine_result(request: SlackRefineRequest) -> SlackRefineResponse:
    """
    Refine a previous Slack result based on user's adjustment instruction.

    Supports two context types:
    - incoming: refining translation or suggested reply from English message
    - draft: refining English translation from Chinese draft
    """
    try:
        # Load prompt template
        with open("src/prompts/slack_refine.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Format conversation history
        history_text = ""
        if request.conversation_history:
            history_items = []
            for msg in request.conversation_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_items.append(f"[{role}] {content}")
            history_text = "\n".join(history_items)

        # Fill in the prompt
        prompt = prompt_template.format(
            original_result=request.original_result,
            adjustment_instruction=request.adjustment_instruction,
            conversation_history=history_text or "无",
            context_type=request.context_type
        )

        # Call LLM
        llm = get_llm_client()
        refined_result = await llm.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000
        )

        return SlackRefineResponse(refined_result=refined_result.strip())

    except Exception as e:
        logger.error(f"Error refining result: {e}", exc_info=True)
        raise
