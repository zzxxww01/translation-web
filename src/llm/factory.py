"""
LLM provider factory and registry.

Keeps provider selection centralized so new model vendors can be
added without touching API/service call sites.

Supports both legacy (env-based) and new (YAML config-based) configuration.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

from src.config import settings

from .base import LLMProvider
from .gemini import create_gemini_provider
from .vectorengine import create_vectorengine_provider
from .models import resolve_model_alias, get_model_provider


logger = logging.getLogger(__name__)

# Flag to enable new config system
USE_NEW_CONFIG = True

LLMProviderFactory = Callable[..., LLMProvider]

_PROVIDER_FACTORIES: dict[str, LLMProviderFactory] = {
    "gemini": create_gemini_provider,
    "vectorengine": create_vectorengine_provider,
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


def get_task_model_alias(task_type: str) -> str:
    """Return the canonical model alias for a task type."""
    alias = None

    if USE_NEW_CONFIG:
        try:
            from .config_loader import get_config_loader

            config_loader = get_config_loader()
            llm_config = config_loader.load()
            alias = llm_config.task_defaults.get(task_type)
            if alias:
                resolved_alias = config_loader.resolve_config_model_alias(alias)
                if resolved_alias:
                    return resolved_alias
                logger.warning(
                    "[LLM Factory] Invalid task default alias %s for task=%s, falling back to legacy settings",
                    alias,
                    task_type,
                )
        except Exception as e:
            logger.warning(f"[LLM Factory] Failed to resolve task alias from new config: {e}")

    task_model_map = {
        "longform": settings.llm_model_longform,
        "post": settings.llm_model_post,
        "analysis": settings.llm_model_analysis,
        "title": settings.llm_model_title,
        "metadata": settings.llm_model_metadata,
    }

    alias = task_model_map.get(task_type, settings.llm_default_model)

    try:
        from .config_loader import get_config_loader

        config_loader = get_config_loader()
        resolved_alias = config_loader.resolve_config_model_alias(alias)
        if resolved_alias:
            return resolved_alias
    except Exception:
        pass

    return alias.strip().lower()


def get_llm_provider_for_task(task_type: str) -> LLMProvider:
    """Get LLM provider configured for a specific task type.

    Args:
        task_type: Task type (longform, post, analysis, title, metadata)

    Returns:
        LLMProvider instance with the appropriate model

    Examples:
        >>> provider = get_llm_provider_for_task("longform")  # Uses deepseek-relay
        >>> provider = get_llm_provider_for_task("post")      # Uses flash-official
    """
    model_alias = get_task_model_alias(task_type)

    logger.info(
        "[LLM Factory] task=%s → model_alias=%s",
        task_type,
        model_alias,
    )

    return create_llm_provider(model_alias)


def create_llm_provider(provider: str | None = None, model: str | None = None, **kwargs) -> LLMProvider:
    """Create an LLM provider instance.

    Args:
        provider: Provider name or model alias (e.g., "gemini", "vectorengine", "deepseek-relay")
        model: Optional model name to pass to the provider
        **kwargs: Additional arguments passed to provider factory

    Returns:
        LLMProvider instance

    Examples:
        >>> create_llm_provider("gemini")  # Direct provider name
        >>> create_llm_provider("deepseek-relay")  # Model alias → routes to vectorengine
        >>> create_llm_provider("pro-official")  # Model alias → routes to gemini
        >>> create_llm_provider("vectorengine", model="deepseek-v3.2")  # Explicit model
    """
    # Try new config system first
    if USE_NEW_CONFIG:
        try:
            from .provider_adapter import create_provider_from_config

            # If provider looks like a model alias, use new config system
            if provider and not provider.lower() in _PROVIDER_FACTORIES:
                logger.info(f"[LLM Factory] Using new config system for model alias: {provider}")
                return create_provider_from_config(provider)
        except Exception as e:
            logger.warning(f"[LLM Factory] New config system failed, falling back to legacy: {e}")

    # Legacy system
    # Try to resolve as model alias first
    resolved_provider = None
    resolved_model = model

    if provider:
        try:
            # Check if it's a model alias
            alias_provider = get_model_provider(provider)
            if alias_provider in _PROVIDER_FACTORIES:
                resolved_provider = alias_provider
                # Get the real model name from the alias
                from .models import get_real_model_name
                resolved_model = get_real_model_name(provider)
        except:
            pass

    # Fall back to direct provider name resolution
    if not resolved_provider or resolved_provider not in _PROVIDER_FACTORIES:
        resolved_provider = resolve_llm_provider_name(provider)

    logger.info(
        "[LLM Factory] creating provider=%s (from input=%s, model=%s)",
        resolved_provider,
        provider,
        resolved_model,
    )

    # Pass model to provider if specified
    if resolved_model:
        kwargs["model"] = resolved_model

    factory = _PROVIDER_FACTORIES[resolved_provider]
    return factory(**kwargs)
