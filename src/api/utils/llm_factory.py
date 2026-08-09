"""
LLM Factory

Thin wrapper around provider registry — singleton creation and fallback generation.
Supports both legacy and new config-based systems with automatic fallback.
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from ...llm.base import LLMProvider
from ...llm.factory import create_llm_provider, get_task_model_alias
from ...llm.provider_adapter import get_provider_adapter
from .concurrency import run_llm_blocking


logger = logging.getLogger(__name__)

# Short-form endpoints need enough room for provider fallback, while still
# finishing before the browser's 180-second request budget.
SHORT_FORM_ATTEMPT_TIMEOUT_SECONDS = 60
SHORT_FORM_TOTAL_TIMEOUT_SECONDS = 170


@lru_cache(maxsize=8)
def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Return a singleton LLM provider (reads config from env vars)."""
    return create_llm_provider(provider=provider)


def get_gemini_provider() -> LLMProvider:
    """Backward-compatible helper for the Gemini provider."""
    return get_llm_provider("gemini")


def generate_with_fallback(
    prompt: str,
    task_type: str = "post",
    timeout: int = 60,
    model: str | None = None,
    **kwargs
) -> str:
    """Generate text with automatic fallback across providers and models.

    Args:
        prompt: The prompt to generate from
        task_type: Task type for default model selection (post, longform, analysis, etc.)
        timeout: Request timeout in seconds
        model: Optional model alias override (e.g., 'flash-official', 'deepseek-relay')
        **kwargs: Additional parameters passed to provider

    Returns:
        Generated text

    Raises:
        Exception: If all fallback attempts fail
    """
    target_model = model or get_task_model_alias(task_type)
    if not target_model:
        raise ValueError(f"No model alias could be resolved for task_type={task_type!r}")

    try:
        adapter = get_provider_adapter(target_model)
        return adapter.generate_with_fallback(
            prompt=prompt,
            timeout=timeout,
            **kwargs,
        )
    except Exception as e:
        logger.warning(f"[LLM Factory] Adapter routing failed for model={target_model}: {e}")
        raise


async def generate_with_fallback_budget(
    prompt: str,
    *,
    task_type: str,
    attempt_timeout: int = SHORT_FORM_ATTEMPT_TIMEOUT_SECONDS,
    total_timeout: int = SHORT_FORM_TOTAL_TIMEOUT_SECONDS,
    **kwargs,
) -> str:
    """Run a blocking short-form LLM call in the bounded pool with a total budget."""

    return await asyncio.wait_for(
        run_llm_blocking(
            generate_with_fallback,
            prompt,
            task_type=task_type,
            timeout=attempt_timeout,
            **kwargs,
        ),
        timeout=total_timeout,
    )
