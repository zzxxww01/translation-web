"""
LLM Factory

Thin wrapper around GeminiProvider — singleton creation and fallback generation.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ...llm.gemini import GeminiProvider, create_gemini_provider


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_gemini_provider() -> GeminiProvider:
    """Return a singleton GeminiProvider (reads config from env vars)."""
    logger.info("[LLM Factory] creating singleton GeminiProvider")
    return create_gemini_provider()


def generate_with_fallback(prompt: str, **_kwargs) -> str:
    """Generate text using the singleton provider.

    Kept as a convenience wrapper so that existing router code
    (``generate_with_fallback(prompt)``) continues to work unchanged.
    """
    provider = get_gemini_provider()
    return provider.generate(prompt)
