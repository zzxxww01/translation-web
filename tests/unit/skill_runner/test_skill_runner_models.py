import json

import pytest
from fastapi.testclient import TestClient

from skill_runner.app import PREFIX, create_app
from skill_runner.runner import Runner
from skill_runner.store import RunStore
from skill_runner_fakes import FakeFactory, make_config, settle


def test_selected_model_reaches_session_and_survives_recovery(tmp_path):
    config = make_config(tmp_path)
    factory = FakeFactory()
    app = create_app(config, session_factory=factory)
    with TestClient(app) as client:
        client.post(f"{PREFIX}/login", json={"password": "s3cret"})
        response = client.post(f"{PREFIX}/runs", data={
            "message": "hello", "harness": "codex", "model": "gpt-6-astra",
        })
        assert response.status_code == 200
        run = response.json()
        assert run.get("model") == "gpt-6-astra"
        assert factory.last.spec.model == "gpt-6-astra"
    stored = RunStore(config.runs_dir).load_meta(run["id"])
    assert stored.model == "gpt-6-astra"


@pytest.mark.asyncio
async def test_model_is_retained_when_resuming_and_actual_model_is_reported(tmp_path):
    config = make_config(tmp_path, idle_timeout_s=0.01)
    store = RunStore(config.runs_dir)
    factory = FakeFactory()
    runner = Runner(config, store, factory)
    meta = runner.create("", "test", "claude", model="opus")
    await runner.begin(meta.id, "hello", [])
    factory.last.push({"type": "session", "session_id": "session-1", "model": "claude-opus-test"})
    factory.last.push({"type": "result", "session_id": "session-1", "is_error": False})
    await settle()
    await runner.shutdown()
    resumed = Runner(config, RunStore(config.runs_dir), factory)
    await resumed.send_message(meta.id, "continue", [])
    assert factory.last.spec.resume == "session-1"
    assert factory.last.spec.model == "opus"
    assert resumed.meta(meta.id).actual_model == "claude-opus-test"
    await resumed.shutdown()


def test_model_catalog_requires_login_and_reads_codex_catalog(tmp_path):
    config = make_config(tmp_path, codex_home=tmp_path / "codex")
    config.codex_home.mkdir()
    (config.codex_home / "models_cache.json").write_text(json.dumps({"models": [
        {"slug": "gpt-6-astra", "display_name": "GPT-6 Astra", "visibility": "list", "priority": 2},
        {"slug": "hidden", "visibility": "hide", "priority": 0},
        {"slug": "gpt-6.1-sol", "display_name": "GPT-6.1 Sol", "visibility": "list", "priority": 1},
    ]}), encoding="utf-8")
    with TestClient(create_app(config, session_factory=FakeFactory())) as client:
        assert client.get(f"{PREFIX}/models/codex").status_code == 401
        client.post(f"{PREFIX}/login", json={"password": "s3cret"})
        response = client.get(f"{PREFIX}/models/codex")
        assert response.status_code == 200
        data = response.json()
        assert [m["id"] for m in data["models"]] == ["gpt-6.1-sol", "gpt-6-astra"]
        assert data["default_model"] == "gpt-6.1-sol"
        assert client.get(f"{PREFIX}/models/unknown").status_code == 400


@pytest.mark.parametrize("model", ["--help", "gpt-6;whoami", "gpt-6\nignored", "x" * 129])
def test_invalid_model_never_creates_a_run(tmp_path, model):
    factory = FakeFactory()
    app = create_app(make_config(tmp_path), session_factory=factory)
    with TestClient(app) as client:
        client.post(f"{PREFIX}/login", json={"password": "s3cret"})
        response = client.post(f"{PREFIX}/runs", data={"message": "hello", "harness": "codex", "model": model})
        assert response.status_code in (400, 422)
        assert client.get(f"{PREFIX}/runs").json() == []
        assert factory.sessions == []


def test_old_metadata_without_model_remains_readable(tmp_path):
    store = RunStore(tmp_path)
    meta = store.create("", "old")
    path = store.run_dir(meta.id) / "meta.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.pop("model", None)
    raw.pop("actual_model", None)
    path.write_text(json.dumps(raw), encoding="utf-8")
    loaded = store.load_meta(meta.id)
    assert loaded.model is None and loaded.actual_model is None


def test_codex_per_run_model_overrides_server_default_on_new_and_resumed_turns(tmp_path):
    from skill_runner.codex_session import build_command

    config = make_config(tmp_path, codex_model="gpt-default")
    for thread in (None, "existing-thread"):
        command = build_command(config, thread, "gpt-6-astra")
        assert command[command.index("-m") + 1] == "gpt-6-astra"


@pytest.mark.asyncio
async def test_claude_discovery_is_cached_and_failure_keeps_honest_aliases(tmp_path, monkeypatch):
    from skill_runner import models

    calls = []

    async def discover(_config):
        calls.append(True)
        return [{"id": "claude-test", "label": "Test", "description": ""}]

    monkeypatch.setattr(models, "discover_claude_models", discover)
    catalog = models.ModelCatalog(make_config(tmp_path))
    assert (await catalog.get("claude"))["models"][0]["id"] == "claude-test"
    assert (await catalog.get("claude"))["source"] == "runtime"
    assert len(calls) == 1
    await catalog.get("claude", refresh=True)
    assert len(calls) == 2

    async def unavailable(_config):
        raise OSError("offline")

    monkeypatch.setattr(models, "discover_claude_models", unavailable)
    fallback = await models.ModelCatalog(make_config(tmp_path)).get("claude")
    assert fallback["source"] == "aliases" and fallback["warning"]
    assert [model["id"] for model in fallback["models"]] == ["opus", "sonnet", "haiku"]


@pytest.mark.parametrize("raw", ["not json", "[]", '{"models": null}'])
def test_corrupt_codex_cache_keeps_default_and_does_not_break_picker(tmp_path, raw):
    from skill_runner.models import codex_models

    (tmp_path / "models_cache.json").write_text(raw, encoding="utf-8")
    assert codex_models(tmp_path) == []


def test_model_refresh_route_bypasses_cached_runtime_catalog(tmp_path, monkeypatch):
    from skill_runner import models

    calls = []

    async def discover(_config):
        calls.append(True)
        return [{"id": f"model-{len(calls)}", "label": "Test", "description": ""}]

    monkeypatch.setattr(models, "discover_claude_models", discover)
    with TestClient(create_app(make_config(tmp_path), session_factory=FakeFactory())) as client:
        client.post(f"{PREFIX}/login", json={"password": "s3cret"})
        assert client.get(f"{PREFIX}/models/claude").json()["models"][0]["id"] == "model-1"
        assert client.get(f"{PREFIX}/models/claude").json()["models"][0]["id"] == "model-1"
        assert client.get(f"{PREFIX}/models/claude?refresh=true").json()["models"][0]["id"] == "model-2"


def test_antigravity_model_route_keeps_selected_model_in_run(tmp_path, monkeypatch):
    from skill_runner import models

    async def discover(_config):
        return [{"id": "gemini-test", "label": "Gemini Test", "description": ""}]

    monkeypatch.setattr(models, "discover_antigravity_models", discover)
    factory = FakeFactory()
    with TestClient(create_app(make_config(tmp_path), session_factory=factory)) as client:
        assert client.get(f"{PREFIX}/models/antigravity").status_code == 401
        client.post(f"{PREFIX}/login", json={"password": "s3cret"})
        catalog = client.get(f"{PREFIX}/models/antigravity?refresh=true").json()
        assert catalog["source"] == "runtime"
        response = client.post(f"{PREFIX}/runs", data={
            "message": "hello", "harness": "antigravity", "model": catalog["models"][0]["id"],
        })
        assert response.status_code == 200
        assert response.json()["harness"] == "antigravity"
        assert factory.last.spec.harness == "antigravity"
        assert factory.last.spec.model == "gemini-test"
