import json

import pytest

from skill_runner import store as store_module
from skill_runner.store import RunStore


def _run_with_files(store: RunStore) -> str:
    meta = store.create("four-step-translate", "精翻 HBM4", "codex", model="gpt-5.5")
    run_dir = store.run_dir(meta.id)
    (run_dir / "input" / "a.html").write_text("<p>hi</p>", encoding="utf-8")
    (run_dir / "output").mkdir()
    (run_dir / "output" / "zh.md").write_text("译文", encoding="utf-8")
    store.append_event(meta.id, {"seq": 1, "type": "user", "text": "go"})
    return meta.id


def _log(store: RunStore) -> list[dict]:
    lines = (store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_archive_moves_the_whole_run_and_logs_what_was_deleted(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)

    record = store.archive(run_id, reason="user", client_ip="203.0.113.7")

    assert not store.exists(run_id)
    assert [m.id for m in store.list_meta()] == []
    moved = store.deleted_dir / run_id
    assert moved == tmp_path / "deleted" / run_id
    assert (moved / "meta.json").is_file() and (moved / "events.jsonl").is_file()
    assert (moved / "input" / "a.html").read_text(encoding="utf-8") == "<p>hi</p>"
    assert (moved / "output" / "zh.md").read_text(encoding="utf-8") == "译文"
    [logged] = _log(store)
    assert logged == record
    assert logged["reason"] == "user" and logged["client_ip"] == "203.0.113.7"
    assert logged["run_id"] == run_id and logged["title"] == "精翻 HBM4"
    assert (logged["skill"], logged["harness"], logged["model"]) == ("four-step-translate", "codex", "gpt-5.5")
    assert logged["inputs"] == [{"path": "input/a.html", "bytes": 9}]
    assert logged["outputs"] == [{"path": "output/zh.md", "bytes": len("译文".encode("utf-8"))}]
    assert logged["moved_to"] == str(moved)
    assert "truncated" not in logged
    for key in ("deleted_at", "created_at", "status", "actual_model"):
        assert key in logged


def test_archive_never_overwrites_an_earlier_archive(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.deleted_dir / run_id).mkdir(parents=True)

    record = store.archive(run_id, reason="user")

    assert record["moved_to"] == str(store.deleted_dir / f"{run_id}-1")
    assert (store.deleted_dir / f"{run_id}-1" / "meta.json").is_file()


def test_archive_still_moves_the_run_when_the_log_cannot_be_written(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.deleted_dir / "deleted.jsonl").mkdir(parents=True)  # 目录挡住了日志文件

    store.archive(run_id, reason="user")

    assert not store.exists(run_id)
    assert (store.deleted_dir / run_id / "meta.json").is_file()


def test_long_file_lists_are_truncated_in_the_log(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "MAX_LOGGED_FILES", 1)
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)

    record = store.archive(run_id, reason="user")

    assert len(record["inputs"]) + len(record["outputs"]) == 1
    assert record["truncated"] is True


def test_hard_delete_is_gone(tmp_path):
    assert not hasattr(RunStore(tmp_path / "runs"), "delete")


@pytest.mark.parametrize("bad", ["../x", "20261028-000000-zzzzzz"])
def test_archive_rejects_ids_that_are_not_run_ids(tmp_path, bad):
    with pytest.raises(KeyError):
        RunStore(tmp_path / "runs").archive(bad, reason="user")
