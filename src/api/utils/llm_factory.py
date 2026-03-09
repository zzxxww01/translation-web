"""
LLM Factory

Thin wrapper around provider registry — singleton creation and fallback generation.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ...llm.base import LLMProvider
from ...llm.factory import create_llm_provider


logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Return a singleton LLM provider (reads config from env vars)."""
    return create_llm_provider(provider=provider)


def get_gemini_provider() -> LLMProvider:
    """Backward-compatible helper for the Gemini provider."""
    return get_llm_provider("gemini")


def generate_with_fallback(prompt: str, **_kwargs) -> str:
    """Generate text using the singleton provider.

    Kept as a convenience wrapper so that existing router code
    (``generate_with_fallback(prompt)``) continues to work unchanged.
    """
    provider = get_llm_provider()
    return provider.generate(prompt)
