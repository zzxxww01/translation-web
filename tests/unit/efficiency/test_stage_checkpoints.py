from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from threading import Event, Lock
import json
import time

import pytest

from src.llm.execution_context import cancellation_scope
from src.llm.errors import LLMRequestCancelledError
from src.services.stage_checkpoints import StageCheckpoints, fingerprint, provider_identity


def test_reuses_validated_result_and_does_not_alias_mutable_objects(tmp_path):
    store = StageCheckpoints(tmp_path, {"prompt": "v1"})
    calls = []
    def compute():
        calls.append(1)
        return {"items": [1]}
    first = store.compute("draft", {"source": "source"}, compute)
    first["items"].append(2)
    second = store.compute("draft", {"source": "source"}, compute)
    second["items"].append(3)
    assert store.compute("draft", {"source": "source"}, compute) == {"items": [1]}
    assert len(calls) == 1
    assert store.hits == 2


@pytest.mark.parametrize("field", ["source", "terms", "rules", "model", "parameters", "neighbors"])
def test_dependency_changes_invalidate_only_matching_key(tmp_path, field):
    store = StageCheckpoints(tmp_path, "bundle")
    inputs = {k: "v1" for k in ["source", "terms", "rules", "model", "parameters", "neighbors"]}
    assert store.compute("draft", inputs, lambda: "old") == "old"
    changed = {**inputs, field: "v2"}
    assert store.compute("draft", changed, lambda: "new") == "new"
    assert store.compute("draft", inputs, lambda: "wrong") == "old"


def test_namespace_and_explicit_retranslation_bypass(tmp_path):
    store = StageCheckpoints(tmp_path, "v1")
    store.compute("draft", {}, lambda: "old")
    assert StageCheckpoints(tmp_path, "v2").compute("draft", {}, lambda: "new") == "new"
    assert store.compute("draft", {}, lambda: "fresh", reuse=False) == "fresh"
    bypass = StageCheckpoints(tmp_path, "v1", reuse_enabled=False)
    assert bypass.compute("draft", {}, lambda: "forced") == "forced"
    assert bypass.compute("draft", {}, lambda: "forced-again") == "forced-again"


def test_invalid_candidate_and_failed_work_never_cached(tmp_path):
    store = StageCheckpoints(tmp_path, "v1")
    def decode(value):
        if not isinstance(value, dict) or value.get("complete") is not True:
            raise ValueError("incomplete")
        return value
    with pytest.raises(ValueError):
        store.compute("draft", {}, lambda: {"complete": False}, decode=decode)
    def failed():
        raise RuntimeError("offline")
    with pytest.raises(RuntimeError):
        store.compute("draft", {}, failed)
    assert not list(store.root.glob("*.json"))
    assert store.compute("draft", {}, lambda: {"complete": True}, decode=decode) == {"complete": True}


@pytest.mark.parametrize("damage", ["json", "hash", "schema", "decoded"])
def test_corrupt_checkpoint_is_a_miss_not_approval(tmp_path, damage):
    store = StageCheckpoints(tmp_path, "v1")
    store.compute("review", {}, lambda: {"issues": []})
    path = next(store.root.glob("*.json"))
    data = json.loads(path.read_text())
    if damage == "json":
        path.write_text("{")
    else:
        if damage == "hash": data["result_digest"] = "wrong"
        if damage == "schema": data["schema"] = 99
        if damage == "decoded":
            data["result"] = {"broken": True}
            data["result_digest"] = fingerprint(data["result"])
        path.write_text(json.dumps(data))
    def decode(value):
        if "issues" not in value: raise ValueError("no issues")
        return value
    assert store.compute("review", {}, lambda: {"issues": ["new finding"]}, decode=decode) == {"issues": ["new finding"]}


def test_equal_concurrent_work_runs_once_across_store_instances(tmp_path):
    calls, lock = [], Lock()
    def work():
        with lock: calls.append(1)
        time.sleep(0.12)
        return "done"
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(StageCheckpoints(tmp_path, "v1").compute, "draft", {}, work) for _ in range(6)]
        assert [f.result(timeout=4) for f in futures] == ["done"] * 6
    assert len(calls) == 1


def test_cancelled_worker_does_not_publish_checkpoint(tmp_path):
    store = StageCheckpoints(tmp_path, "v1")
    event = Event()
    def abandoned():
        event.set()
        return "late"
    with cancellation_scope(event), pytest.raises(LLMRequestCancelledError):
        store.compute("draft", {}, abandoned)
    assert not list(store.root.glob("*.json"))


def test_waiting_for_checkpoint_observes_cancellation(tmp_path):
    from src.llm.execution_context import cancellation_scope
    started, finish, cancelled = Event(), Event(), Event()
    owner = StageCheckpoints(tmp_path, "v1")
    def work():
        started.set()
        assert finish.wait(3)
        return "result"
    def waiter():
        with cancellation_scope(cancelled):
            return StageCheckpoints(tmp_path, "v1").compute("draft", {}, lambda: "duplicate")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(owner.compute, "draft", {}, work)
        assert started.wait(1)
        b = pool.submit(waiter)
        cancelled.set()
        with pytest.raises(LLMRequestCancelledError): b.result(timeout=1)
        finish.set()
        assert a.result(timeout=1) == "result"


def test_rejects_symlink_cache_and_does_not_store_credentials(tmp_path):
    (tmp_path / "artifacts").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        StageCheckpoints(tmp_path, "v1").compute("draft", {}, lambda: "no")
    class Provider:
        model_alias = "alias"
        api_key = "SECRET"
        _checkpoint_route = [{"provider_id": "one", "real_model": "m"}]
    assert "SECRET" not in json.dumps(provider_identity(Provider()))
