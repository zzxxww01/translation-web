import asyncio
import os
import sys
from types import SimpleNamespace

import pytest

from skill_runner import models


def config(tmp_path, **overrides):
    return SimpleNamespace(home=tmp_path, antigravity_bin="agy", antigravity_model=None, **overrides)


def test_antigravity_model_parser_accepts_only_model_rows():
    raw = "\n".join([
        "slug\tdisplay_name",
        "gemini-test-high\tGemini Test (High)",
        "gemini-test-high\tDuplicate",
        "custom/model-v2\tCustom model",
        "Sign in before continuing",
        "--bad\tBad",
        "invalid model\tBad",
        "model;command\tBad",
        "bare-model",
        "empty-label\t",
        "extra-columns\tLabel\tUnexpected",
    ])
    assert models.parse_antigravity_models(raw) == [
        {"id": "gemini-test-high", "label": "Gemini Test (High)", "description": ""},
        {"id": "custom/model-v2", "label": "Custom model", "description": ""},
    ]


@pytest.mark.asyncio
async def test_antigravity_catalog_caches_refreshes_and_invalidates_on_cli_change(tmp_path, monkeypatch):
    executable = tmp_path / "agy"
    executable.write_text("first", encoding="utf-8")
    cfg = config(tmp_path)
    cfg.antigravity_bin = str(executable)
    calls = []

    async def discover(_config):
        calls.append(True)
        return [{"id": f"gemini-test-{len(calls)}", "label": "Test", "description": ""}]

    monkeypatch.setattr(models, "discover_antigravity_models", discover)
    catalog = models.ModelCatalog(cfg)
    assert (await catalog.get("antigravity"))["models"][0]["id"] == "gemini-test-1"
    assert (await catalog.get("antigravity"))["source"] == "runtime"
    assert len(calls) == 1
    assert (await catalog.get("antigravity", refresh=True))["models"][0]["id"] == "gemini-test-2"
    os.utime(executable, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    assert (await catalog.get("antigravity"))["models"][0]["id"] == "gemini-test-3"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, OSError("secret-auth-diagnostic")])
async def test_antigravity_unavailable_keeps_default_without_fake_models(tmp_path, monkeypatch, failure):
    async def discover(_config):
        if failure:
            raise failure
        return []

    monkeypatch.setattr(models, "discover_antigravity_models", discover)
    cfg = config(tmp_path)
    cfg.antigravity_model = "custom-model"
    result = await models.ModelCatalog(cfg).get("antigravity")
    assert result["models"] == []
    assert result["default_model"] == "custom-model"
    assert result["source"] == "unavailable"
    assert result["warning"] and "secret-auth-diagnostic" not in result["warning"]


class FakeProcess:
    pid = 876543210

    def __init__(self, stdout=b"", *, returncode=0, hangs=False):
        self.stdout = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.returncode = None if hangs else returncode
        self.killed = False
        self.done = asyncio.Event()
        if not hangs:
            self.stdout.feed_eof()
            self.done.set()

    async def wait(self):
        await self.done.wait()
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.stdout.feed_eof()
        self.done.set()


def fake_spawn(monkeypatch, process):
    calls = []

    async def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        return process

    monkeypatch.setattr(models.asyncio, "create_subprocess_exec", spawn)
    if os.name != "nt":
        monkeypatch.setattr(models.os, "killpg", lambda *_: process.kill())
    return calls


@pytest.mark.asyncio
async def test_antigravity_discovery_only_runs_models_and_discards_secret_diagnostics(tmp_path, monkeypatch):
    process = FakeProcess(b"gemini-test\tGemini Test\n")
    calls = fake_spawn(monkeypatch, process)
    monkeypatch.setenv("GEMINI_API_KEY", "not-for-subscription")
    monkeypatch.setenv("GOOGLE_API_KEY", "not-for-subscription")
    assert (await models.discover_antigravity_models(config(tmp_path)))[0]["id"] == "gemini-test"
    args, kwargs = calls[0]
    assert args == ("agy", "models")
    assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
    assert kwargs["stderr"] == asyncio.subprocess.DEVNULL
    assert "GEMINI_API_KEY" not in kwargs["env"] and "GOOGLE_API_KEY" not in kwargs["env"]


@pytest.mark.asyncio
async def test_antigravity_discovery_timeout_kills_process(tmp_path, monkeypatch):
    process = FakeProcess(hangs=True)
    fake_spawn(monkeypatch, process)
    monkeypatch.setattr(models, "DISCOVERY_TIMEOUT_S", 0.01)
    with pytest.raises(TimeoutError):
        await models.discover_antigravity_models(config(tmp_path))
    assert process.killed


@pytest.mark.asyncio
async def test_antigravity_discovery_rejects_unbounded_output(tmp_path, monkeypatch):
    process = FakeProcess(b"x" * 2048, hangs=True)
    fake_spawn(monkeypatch, process)
    monkeypatch.setattr(models, "MODEL_OUTPUT_LIMIT", 1024)
    with pytest.raises(ValueError, match="limit"):
        await models.discover_antigravity_models(config(tmp_path))
    assert process.killed


@pytest.mark.asyncio
async def test_antigravity_discovery_nonzero_exit_is_not_a_catalog(tmp_path, monkeypatch):
    fake_spawn(monkeypatch, FakeProcess(b"gemini-test\tTest\n", returncode=1))
    with pytest.raises(RuntimeError):
        await models.discover_antigravity_models(config(tmp_path))


@pytest.mark.asyncio
async def test_antigravity_discovery_cancellation_reaps_started_child(tmp_path, monkeypatch):
    process = FakeProcess(hangs=True)
    calls = fake_spawn(monkeypatch, process)
    task = asyncio.create_task(models.discover_antigravity_models(config(tmp_path)))
    while not calls:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.killed


@pytest.mark.asyncio
async def test_large_real_subprocess_output_is_bounded_and_child_is_reaped(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "_antigravity_command", lambda _: [
        sys.executable, "-c", "import sys,time; sys.stdout.buffer.write(b'x' * 4000000); sys.stdout.flush(); time.sleep(60)",
    ])
    monkeypatch.setattr(models, "MODEL_OUTPUT_LIMIT", 1024)
    with pytest.raises(ValueError, match="limit"):
        await asyncio.wait_for(models.discover_antigravity_models(config(tmp_path)), timeout=5)
