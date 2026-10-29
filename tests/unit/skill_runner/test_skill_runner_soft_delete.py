import json
import os

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


def test_long_file_lists_are_truncated_but_keep_input_and_output(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "MAX_LOGGED_FILES", 3)
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    run_dir = store.run_dir(run_id)
    (run_dir / ".venv").mkdir()
    (run_dir / "node_modules").mkdir()
    for i in range(10):
        (run_dir / ".venv" / f"lib{i}.py").write_text("x", encoding="utf-8")
        (run_dir / "node_modules" / f"m{i}.js").write_text("x", encoding="utf-8")

    record = store.archive(run_id, reason="user")

    assert record["inputs"] == [{"path": "input/a.html", "bytes": 9}]
    assert [e["path"] for e in record["outputs"]] == ["output/zh.md", "node_modules/m0.js"]
    assert record["truncated"] is True
    # 真实总数：a.html + zh.md + 10 个 node_modules 文件（隐藏的 .venv 和 meta/events 不算）
    assert record["file_count"] == 12
    assert record["total_bytes"] == 9 + len("译文".encode("utf-8")) + 10


def test_manifest_has_totals_and_skips_unstatable_files(tmp_path, monkeypatch):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    real_lstat = os.lstat

    def flaky(path, *a, **kw):
        if os.path.basename(path) == "zh.md":
            raise OSError("gone")
        return real_lstat(path, *a, **kw)

    monkeypatch.setattr(store_module.os, "lstat", flaky)
    record = store.archive(run_id, reason="user")
    monkeypatch.undo()

    assert record["outputs"] == []
    assert (record["file_count"], record["total_bytes"]) == (1, 9)


def test_symlinked_input_dir_is_not_followed(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("s", encoding="utf-8")
    input_dir = store.run_dir(run_id) / "input"
    for child in input_dir.iterdir():
        child.unlink()
    input_dir.rmdir()
    try:
        os.symlink(outside, input_dir, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create symlinks here")

    record = store.archive(run_id, reason="user")

    assert record["inputs"] == []
    assert all("secret" not in e["path"] for e in record["outputs"])


def test_non_utf8_filename_does_not_lose_the_record(tmp_path, monkeypatch):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    bad = "output/\udcb2.md"
    monkeypatch.setattr(
        store, "_file_manifest",
        lambda root: {"inputs": [], "outputs": [{"path": bad, "bytes": 1}], "file_count": 1, "total_bytes": 1},
    )

    record = store.archive(run_id, reason="user")

    assert not store.exists(run_id)
    [logged] = _log(store)
    assert logged["run_id"] == run_id and logged["outputs"][0]["path"] == bad
    assert record["run_id"] == run_id


def test_failed_log_append_logs_the_full_record_at_error_level(tmp_path, caplog):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.deleted_dir / "deleted.jsonl").mkdir(parents=True)

    with caplog.at_level("INFO", logger="skill_runner.store"):
        store.archive(run_id, reason="user")

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert errors and run_id in errors[0].getMessage() and "output/zh.md" in errors[0].getMessage()


def test_info_log_is_only_a_summary(tmp_path, caplog):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)

    with caplog.at_level("INFO", logger="skill_runner.store"):
        store.archive(run_id, reason="user", client_ip="203.0.113.7")

    [info] = [r for r in caplog.records if r.levelname == "INFO"]
    message = info.getMessage()
    assert run_id in message and "203.0.113.7" in message and "output/zh.md" not in message


def test_archive_works_when_meta_is_corrupt(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.run_dir(run_id) / "meta.json").write_text("{not json", encoding="utf-8")

    record = store.archive(run_id, reason="user")

    assert record["title"] is None and record["status"] is None
    assert (store.deleted_dir / run_id / "output" / "zh.md").is_file()


def test_hard_delete_is_gone(tmp_path):
    assert not hasattr(RunStore(tmp_path / "runs"), "delete")


@pytest.mark.parametrize("bad", ["../x", "20261028-000000-zzzzzz"])
def test_archive_rejects_ids_that_are_not_run_ids(tmp_path, bad):
    with pytest.raises(KeyError):
        RunStore(tmp_path / "runs").archive(bad, reason="user")
