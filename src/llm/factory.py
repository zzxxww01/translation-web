"""
LLM provider factory and registry.

Keeps provider selection centralized so new model vendors can be
added without touching API/service call sites.
"""

from __future__ import annotations

import logging
from typing import Callable

from src.config import settings

from .base import LLMProvider
from .gemini import create_gemini_provider


logger = logging.getLogger(__name__)

LLMProviderFactory = Callable[..., LLMProvider]

_PROVIDER_FACTORIES: dict[str, LLMProviderFactory] = {
    "gemini": create_gemini_provider,
}


def register_llm_provider(name: str, factory: LLMProviderFactory) -> None:
    """Register an LLM provider factory."""
    provider_name = name.strip().lower()
    if not provider_name:
        raise ValueError("Provider name cannot be empty.")
    _PROVIDER_FACTORIES[provider_name] = factory


def list_llm_providers() -> list[str]:
    """List available provider names."""
    return sorted(_PROVIDER_FACTORIES)


def resolve_llm_provider_name(provider: str | None = None) -> str:
    """Resolve the active provider name from argument or settings."""
    provider_name = (provider or settings.llm_provider or "gemini").strip().lower()
    if provider_name not in _PROVIDER_FACTORIES:
        available = ", ".join(list_llm_providers())
        raise ValueError(
            f"Unsupported LLM provider '{provider_name}'. Available providers: {available}."
        )
    return provider_name


def create_llm_provider(provider: str | None = None, **kwargs) -> LLMProvider:
    """Create an LLM provider instance."""
    provider_name = resolve_llm_provider_name(provider)
    logger.info("[LLM Factory] creating provider=%s", provider_name)
    factory = _PROVIDER_FACTORIES[provider_name]
    return factory(**kwargs)
