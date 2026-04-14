"""
LLM Factory

Thin wrapper around provider registry — singleton creation and fallback generation.
Supports both legacy and new config-based systems with automatic fallback.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ...llm.base import LLMProvider
from ...llm.factory import create_llm_provider, get_llm_provider_for_task


logger = logging.getLogger(__name__)

# Flag to enable故障转移 (fallback) mechanism
USE_FALLBACK_STRATEGY = True


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
    # Determine which model to use
    target_model = model

    if not target_model:
        # Use task-specific default
        provider = get_llm_provider_for_task(task_type)
        return provider.generate(prompt, timeout=timeout, **kwargs)

    # Use fallback strategy if enabled
    if USE_FALLBACK_STRATEGY:
        try:
            from ...llm.provider_adapter import get_provider_adapter

            adapter = get_provider_adapter(target_model)
            return adapter.generate_with_fallback(
                prompt=prompt,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"[LLM Factory] Fallback strategy failed: {e}, using legacy method")

    # Legacy method: single provider
    provider = create_llm_provider(target_model)
    return provider.generate(prompt, model=target_model, timeout=timeout, **kwargs)
