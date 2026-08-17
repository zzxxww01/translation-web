from pathlib import Path

import pytest
import yaml

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


def test_shared_real_model_still_resolves_to_the_right_alias(tmp_path: Path) -> None:
    """两个 canonical alias 指向同一个真实模型时，别名不能互相串台。

    把 gemini-pro 和 gemini-preview 都配成同一个模型是完全合理的用法（想统一用
    最强的那个），但反查是按 real_model 匹配的，撞车时会退化成"取列表里第一个"，
    preview-official 于是解析成 gemini-pro。这里用独立配置钉死消歧行为——即使
    将来正式配置里两者又分开了，这条路径仍有覆盖。
    """
    raw = yaml.safe_load(
        (ROOT / "config" / "llm_providers.yaml").read_text(encoding="utf-8")
    )
    models = raw["providers"]["gemini-official"]["models"]
    by_alias = {model["alias"]: model for model in models}
    # 无论正式配置里两者是否已经相同，这里都强制撞车，把消歧路径逼出来
    by_alias["gemini-preview"]["real_model"] = by_alias["gemini-pro"]["real_model"]

    config = tmp_path / "providers.yaml"
    config.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    loader = ConfigLoader(str(config))
    loader.load()

    assert loader.resolve_config_model_alias("pro-official") == "gemini-pro"
    assert loader.resolve_config_model_alias("preview-official") == "gemini-preview"


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
