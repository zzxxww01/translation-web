from pathlib import Path

import pytest

from src.core.model_config import ModelConfig
from src.llm.config_loader import ConfigLoader


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def provider_loader() -> ConfigLoader:
    loader = ConfigLoader(str(ROOT / "config" / "llm_providers.yaml"))
    loader.load()
    return loader


@pytest.mark.parametrize(
    ("legacy_alias", "canonical_alias"),
    [
        ("flash-official", "gemini-flash"),
        ("pro-official", "gemini-pro"),
        ("preview-official", "gemini-preview"),
        ("deepseek-v3.2", "deepseek-v3"),
        ("grok-4", "grok-4-1-fast-non-reasoning"),
        ("grok-4-20-non-reasoning", "grok-4-1-fast-non-reasoning"),
    ],
)
def test_legacy_model_aliases_resolve_to_configured_models(
    provider_loader: ConfigLoader,
    legacy_alias: str,
    canonical_alias: str,
) -> None:
    assert provider_loader.resolve_config_model_alias(legacy_alias) == canonical_alias


def test_every_longform_profile_and_override_uses_a_configured_model(
    provider_loader: ConfigLoader,
) -> None:
    model_config = ModelConfig(str(ROOT / "config" / "translation_models.yaml"))

    aliases = [
        model_config.get_model_for_phase("phase0_prescan", model_override=name)["model"]
        for name in model_config.get_available_models()
    ]
    aliases.extend(
        model_config.get_model_for_phase("phase0_prescan", profile=profile)["model"]
        for profile in model_config.get_available_profiles()
    )

    assert aliases
    assert all(provider_loader.resolve_config_model_alias(alias) for alias in aliases)
