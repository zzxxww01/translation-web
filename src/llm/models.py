"""
LLM Model Registry

Centralized model alias management for multi-provider support.
Maps user-facing model aliases to provider and real model names.
"""

from typing import Dict, Any, Optional, Tuple


# Model Registry: alias → {provider, real_model, description}
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Gemini Official API
    "flash-official": {
        "provider": "gemini",
        "real_model": "gemini-flash-latest",
        "description": "Gemini Flash 官方 API - 快速低成本",
        "supports_thinking": False,
    },
    "pro-official": {
        "provider": "gemini",
        "real_model": "gemini-3-pro-preview",
        "description": "Gemini Pro 官方 API - 平衡质量与成本",
        "supports_thinking": True,
    },
    "preview-official": {
        "provider": "gemini",
        "real_model": "gemini-3.1-pro-preview",
        "description": "Gemini Preview 官方 API - 预览版更强能力",
        "supports_thinking": True,
    },

    # VectorEngine Relay API
    "deepseek-relay": {
        "provider": "vectorengine",
        "real_model": "deepseek-v3.2",
        "description": "DeepSeek v3.2 中转 - 高性价比推理模型",
        "supports_thinking": True,
    },
    "gpt4-relay": {
        "provider": "vectorengine",
        "real_model": "gpt-4o",
        "description": "GPT-4o 中转 - OpenAI 旗舰模型",
        "supports_thinking": False,
    },
    "claude-relay": {
        "provider": "vectorengine",
        "real_model": "claude-sonnet-4-20250514",
        "description": "Claude Sonnet 4 中转 - Anthropic 高质量模型",
        "supports_thinking": False,
    },
}


# Legacy aliases for backward compatibility
LEGACY_ALIASES = {
    "flash": "flash-official",
    "pro": "pro-official",
    "preview": "preview-official",
    "gemini": "pro-official",
    "default": "pro-official",
    "reasoning": "pro-official",
}


def resolve_model_alias(alias: Optional[str]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Resolve model alias to (provider, real_model, config).

    Args:
        alias: Model alias (e.g., "deepseek-relay", "pro-official")

    Returns:
        Tuple of (provider_name, real_model_name, model_config)

    Examples:
        >>> resolve_model_alias("deepseek-relay")
        ("vectorengine", "deepseek-v3.2", {...})

        >>> resolve_model_alias("pro-official")
        ("gemini", "gemini-3-pro-preview", {...})

        >>> resolve_model_alias("flash")  # legacy alias
        ("gemini", "gemini-flash-latest", {...})
    """
    if not alias:
        alias = "pro-official"  # default fallback

    alias = alias.strip().lower()

    # Check legacy aliases first
    if alias in LEGACY_ALIASES:
        alias = LEGACY_ALIASES[alias]

    # Look up in registry
    if alias in MODEL_REGISTRY:
        config = MODEL_REGISTRY[alias]
        return config["provider"], config["real_model"], config

    # If not found, assume it's a direct model name for gemini (backward compatibility)
    return "gemini", alias, {"description": f"Direct model name: {alias}"}


def list_available_models() -> Dict[str, str]:
    """List all available model aliases with descriptions."""
    result = {}
    for alias, config in MODEL_REGISTRY.items():
        result[alias] = config["description"]
    return result


def get_model_provider(alias: Optional[str]) -> str:
    """Get provider name for a model alias."""
    provider, _, _ = resolve_model_alias(alias)
    return provider


def get_real_model_name(alias: Optional[str]) -> str:
    """Get real model name for a model alias."""
    _, real_model, _ = resolve_model_alias(alias)
    return real_model
