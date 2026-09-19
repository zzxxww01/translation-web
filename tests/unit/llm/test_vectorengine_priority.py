"""Guard the deployed relay-first, official-fallback routing policy."""
from pathlib import Path

import pytest

from src.llm.config_loader import ConfigLoader
from src.llm.fallback_strategy import FallbackStrategy

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("alias", [
    "deepseek-v3", "grok-4-1-fast-non-reasoning",
    "gemini-flash", "gemini-pro", "gemini-preview",
])
def test_standard_model_tries_relay_before_official(monkeypatch, alias):
    monkeypatch.setenv("VECTORENGINE_API_KEY", "test-relay-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-official-key")
    config = ConfigLoader(str(ROOT / "config/llm_providers.yaml")).load()
    plan = FallbackStrategy(config).build_attempt_plan(alias)
    providers = [attempt.provider.provider_id for attempt in plan]
    assert providers[0] == "vectorengine-relay"
    assert "gemini-official" in providers
    first_official = providers.index("gemini-official")
    assert all(p == "vectorengine-relay" for p in providers[:first_official])
    assert all(p == "gemini-official" for p in providers[first_official:])
