"""
Model listing API endpoint.

Supports both legacy (MODEL_REGISTRY) and new (YAML config) systems.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from src.llm.models import MODEL_REGISTRY


router = APIRouter()


class ModelInfo(BaseModel):
    """Model information."""
    alias: str
    name: str
    description: str
    supports_thinking: bool
    priority: int
    available: bool


class ProviderInfo(BaseModel):
    """Provider information with grouped models."""
    id: str
    name: str
    description: str
    models: List[ModelInfo]


class ModelListResponse(BaseModel):
    """Response for model list endpoint (grouped by provider)."""
    providers: List[ProviderInfo]


class LegacyModelInfo(BaseModel):
    """Legacy model information (flat list)."""
    alias: str
    provider: str
    real_model: str
    description: str
    supports_thinking: bool


class LegacyModelListResponse(BaseModel):
    """Legacy response for model list endpoint (flat list)."""
    models: List[LegacyModelInfo]


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """
    List all available LLM models (grouped by provider).

    Returns a list of providers with their models, including availability status.
    Uses new YAML config system if available, falls back to legacy MODEL_REGISTRY.
    """
    # Try new config system first
    try:
        from src.llm.config_loader import get_config_loader
        import yaml

        config_loader = get_config_loader()
        config = config_loader.load()

        providers = []
        for provider_id, provider in config.providers.items():
            if not provider.enabled:
                continue

            models = []
            for model in provider.models:
                if not model.enabled:
                    continue

                # Check if there's at least one valid API key
                has_valid_key = any(k.enabled and k.key for k in provider.api_keys)

                models.append(
                    ModelInfo(
                        alias=model.alias,
                        name=model.name,
                        description=model.description,
                        supports_thinking=model.supports_thinking,
                        priority=model.priority,
                        available=has_valid_key,
                    )
                )

            # Sort models by priority
            models.sort(key=lambda m: m.priority)

            providers.append(
                ProviderInfo(
                    id=provider_id,
                    name=provider.name,
                    description=provider.description,
                    models=models,
                )
            )

        # Sort providers by group_priority
        providers.sort(key=lambda p: config.providers[p.id].group_priority)

        return ModelListResponse(providers=providers)

    except (FileNotFoundError, yaml.YAMLError, ValueError, KeyError) as e:
        # Expected errors - fall back to legacy system
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[Models API] New config system failed, using legacy: {e}")

        # Group legacy models by provider
        provider_map = {}
        for alias, config in MODEL_REGISTRY.items():
            provider_name = config["provider"]
            if provider_name not in provider_map:
                provider_map[provider_name] = {
                    "id": provider_name,
                    "name": provider_name.capitalize(),
                    "description": f"{provider_name.capitalize()} models",
                    "models": [],
                }

            provider_map[provider_name]["models"].append(
                ModelInfo(
                    alias=alias,
                    name=alias,
                    description=config["description"],
                    supports_thinking=config.get("supports_thinking", False),
                    priority=1,
                    available=True,  # Assume available in legacy mode
                )
            )

        providers = [
            ProviderInfo(**provider_data)
            for provider_data in provider_map.values()
        ]

        return ModelListResponse(providers=providers)

    except Exception as e:
        # Unexpected errors - log and re-raise
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[Models API] Unexpected error: {e}", exc_info=True)
        raise


@router.get("/models/legacy", response_model=LegacyModelListResponse)
async def list_models_legacy():
    """
    List all available LLM models (legacy flat list format).

    Kept for backward compatibility.
    """
    models = []
    for alias, config in MODEL_REGISTRY.items():
        models.append(
            LegacyModelInfo(
                alias=alias,
                provider=config["provider"],
                real_model=config["real_model"],
                description=config["description"],
                supports_thinking=config.get("supports_thinking", False),
            )
        )

    # Sort by provider, then by alias
    models.sort(key=lambda m: (m.provider, m.alias))

    return LegacyModelListResponse(models=models)
