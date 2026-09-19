from pathlib import Path

import pytest
import yaml

from src.core.model_config import ModelConfig
from src.llm.config_loader import ConfigLoader
from src.llm.fallback_strategy import FallbackStrategy


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def provider_loader(monkeypatch: pytest.MonkeyPatch) -> ConfigLoader:
    # Build real attempt plans without requiring credentials or network calls.
    monkeypatch.setenv("GEMINI_API_KEY", "test-official-key")
    monkeypatch.setenv("VECTORENGINE_API_KEY", "test-relay-key")
    loader = ConfigLoader(str(ROOT / "config" / "llm_providers.yaml"))
    loader.load()
    return loader


@pytest.mark.parametrize(
    ("legacy_alias", "canonical_alias", "provider_id"),
    [
        ("flash-official", "gemini-flash-fallback", "gemini-official"),
        ("pro-official", "gemini-pro-fallback", "gemini-official"),
        ("preview-official", "gemini-preview-fallback", "gemini-official"),
        ("gemini-flash-official", "gemini-flash-fallback", "gemini-official"),
        ("gemini-pro-official", "gemini-pro-fallback", "gemini-official"),
        ("gemini-preview-official", "gemini-preview-fallback", "gemini-official"),
        ("flash", "gemini-flash", "vectorengine-relay"),
        ("pro", "gemini-pro", "vectorengine-relay"),
        ("preview", "gemini-preview", "vectorengine-relay"),
        ("gemini", "gemini-pro", "vectorengine-relay"),
        ("default", "gemini-pro", "vectorengine-relay"),
        ("reasoning", "gemini-pro", "vectorengine-relay"),
        ("gemini-flash", "gemini-flash", "vectorengine-relay"),
        ("gemini-pro", "gemini-pro", "vectorengine-relay"),
        ("gemini-preview", "gemini-preview", "vectorengine-relay"),
        ("deepseek-v3.2", "deepseek-v3", "vectorengine-relay"),
        ("grok-4", "grok-4-1-fast-non-reasoning", "vectorengine-relay"),
        ("grok-4-20-non-reasoning", "grok-4-1-fast-non-reasoning", "vectorengine-relay"),
    ],
)
def test_legacy_model_aliases_resolve_to_configured_models(
    provider_loader: ConfigLoader,
    legacy_alias: str,
    canonical_alias: str,
    provider_id: str,
) -> None:
    assert provider_loader.resolve_config_model_alias(legacy_alias) == canonical_alias
    model = provider_loader.get_model_config(legacy_alias)
    provider = provider_loader.get_provider_for_model(legacy_alias)
    assert model is not None and model.alias == canonical_alias
    assert provider is not None and provider.provider_id == provider_id

    strategy = FallbackStrategy(provider_loader.load())
    assert strategy._resolve_config_model_alias(legacy_alias) == canonical_alias
    attempts = strategy.build_attempt_plan(legacy_alias)
    assert attempts[0].model.alias == canonical_alias
    assert attempts[0].provider.provider_id == provider_id


@pytest.mark.parametrize("official_suffix", ["", "-fallback"])
def test_shared_real_model_still_resolves_to_the_right_alias(
    tmp_path: Path, official_suffix: str
) -> None:
    """Official preview must not select pro, even with shared/upgraded real models.

    Cover both the current fallback aliases and older official-only configs.
    """
    raw = yaml.safe_load(
        (ROOT / "config" / "llm_providers.yaml").read_text(encoding="utf-8")
    )
    models = raw["providers"]["gemini-official"]["models"]
    for model in models:
        model["alias"] = model["alias"].removesuffix("-fallback") + official_suffix
        # Alias compatibility must not depend on registry real-model versions.
        model["real_model"] = "shared-upgraded-model"
    if not official_suffix:
        del raw["providers"]["vectorengine-relay"]

    config = tmp_path / "providers.yaml"
    config.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    loader = ConfigLoader(str(config))
    strategy = FallbackStrategy(loader.load())
    for stem in ("pro", "preview"):
        expected = f"gemini-{stem}{official_suffix}"
        assert loader.resolve_config_model_alias(f"{stem}-official") == expected
        assert strategy._resolve_config_model_alias(f"{stem}-official") == expected


@pytest.mark.parametrize("alias", ["", "   ", "unknown-model"])
def test_unknown_alias_is_not_resolved(provider_loader: ConfigLoader, alias: str) -> None:
    assert provider_loader.resolve_config_model_alias(alias) is None
    assert FallbackStrategy(provider_loader.load())._resolve_config_model_alias(alias) is None


def test_exact_config_alias_takes_precedence(provider_loader: ConfigLoader) -> None:
    config = provider_loader.load()
    model = config.providers["vectorengine-relay"].models[0]
    model.alias = "preview-official"
    assert provider_loader.resolve_config_model_alias(model.alias) == model.alias
    assert FallbackStrategy(config)._resolve_config_model_alias(model.alias) == model.alias


def test_direct_real_model_lookup_is_preserved(provider_loader: ConfigLoader) -> None:
    config = provider_loader.load()
    model = config.providers["gemini-official"].models[0]
    assert provider_loader.resolve_config_model_alias(model.real_model) == model.alias
    assert FallbackStrategy(config)._resolve_config_model_alias(model.real_model) == model.alias


def test_official_alias_does_not_select_relay_when_official_is_absent(
    provider_loader: ConfigLoader,
) -> None:
    config = provider_loader.load()
    del config.providers["gemini-official"]
    assert provider_loader.resolve_config_model_alias("preview-official") is None
    assert FallbackStrategy(config)._resolve_config_model_alias("preview-official") is None


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
