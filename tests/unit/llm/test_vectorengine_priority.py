"""Guard the deployed relay-first, official-fallback routing policy."""
from pathlib import Path

import pytest

from src.llm.config_loader import ConfigLoader
from src.llm.config_models import is_relay_provider
from src.llm.fallback_strategy import FallbackStrategy
from src.llm.provider_adapter import ProviderAdapter

ROOT = Path(__file__).resolve().parents[3]


def load_config(monkeypatch):
    monkeypatch.setenv("VECTORENGINE_API_KEY", "test-relay-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-official-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    return ConfigLoader(str(ROOT / "config/llm_providers.yaml")).load()


def task_route(monkeypatch, task):
    """Real models the adapter would try for a task default, after the four-attempt cap."""
    config = load_config(monkeypatch)
    adapter = ProviderAdapter.__new__(ProviderAdapter)
    adapter.model_alias = config.task_defaults[task]
    adapter.attempt_plan = FallbackStrategy(config).build_attempt_plan(adapter.model_alias)
    return [(a.provider.provider_id, a.model.real_model) for a in adapter._bounded_attempt_plan()]


@pytest.mark.parametrize("task", ["longform", "post", "slack"])
def test_relay_flash_tasks_fall_back_to_official_flash(monkeypatch, task):
    route = task_route(monkeypatch, task)
    assert route[:2] == [("vectorengine-relay", "gemini-3.8-flash"), ("gemini-official", "gemini-3.8-flash")]
    assert not {"gemini-4-argon", "gemini-2.5-flash", "qwen3.6-plus"} & {model for _, model in route}


@pytest.mark.parametrize("task", ["analysis", "metadata"])
def test_relay_deepseek_falls_back_to_official_deepseek_first(monkeypatch, task):
    route = task_route(monkeypatch, task)
    assert route[:2] == [("vectorengine-relay", "deepseek-v4.1-flash"), ("deepseek-official", "deepseek-flash")]


@pytest.mark.parametrize("task", ["post_optimize", "title"])
def test_short_form_tasks_use_official_argon_then_official_flash(monkeypatch, task):
    route = task_route(monkeypatch, task)
    assert all(provider != "vectorengine-relay" for provider, _ in route)
    assert [model for _, model in route][:2] == ["gemini-4-argon", "gemini-3.8-flash"]


@pytest.mark.parametrize("alias", [
    "deepseek-v3", "grok-4-1-fast-non-reasoning",
    "gemini-flash", "gemini-pro", "gemini-preview",
])
def test_relay_model_falls_back_to_official_before_other_relay_models(monkeypatch, alias):
    plan = FallbackStrategy(load_config(monkeypatch)).build_attempt_plan(alias)
    assert is_relay_provider(plan[0].provider)
    first_other = next(i for i, a in enumerate(plan) if a.model.alias != plan[0].model.alias)
    official = [i for i, a in enumerate(plan) if not is_relay_provider(a.provider)]
    other_relay = [i for i, a in enumerate(plan) if is_relay_provider(a.provider) and a.model.alias != plan[0].model.alias]
    assert official and official[0] == first_other
    assert max(official) < min(other_relay)


def test_models_marked_no_fallback_are_never_fallback_targets(monkeypatch):
    config = load_config(monkeypatch)
    excluded = {m.alias for p in config.providers.values() for m in p.models if not m.fallback}
    assert {"gemini-official-argon", "qwen-plus"} <= excluded
    strategy = FallbackStrategy(config)
    for provider in config.providers.values():
        for model in provider.models:
            later = {a.model.alias for a in strategy.build_attempt_plan(model.alias)[1:]} - {model.alias}
            assert not later & excluded, model.alias
