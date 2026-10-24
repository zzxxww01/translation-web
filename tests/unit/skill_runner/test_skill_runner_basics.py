import io
import json
import os
from pathlib import Path

import pytest

from skill_runner import auth, policy
from skill_runner.config import DEFAULT_SKILLS, Config
from skill_runner.store import RunStore, UploadTooLarge, iter_skill_catalog, safe_filename


# ---- 登录 ----


def test_password_check_fails_closed_without_configured_password():
    assert auth.check_password("", "") is False
    assert auth.check_password("", "anything") is False
    assert auth.check_password("pw", "PW") is False
    assert auth.check_password("pw", "pw") is True


def test_token_roundtrip_tamper_and_expiry():
    secret = b"k" * 32
    token = auth.issue_token(secret, now=1_000_000)
    assert auth.verify_token(secret, token, now=1_000_100)
    assert not auth.verify_token(b"x" * 32, token, now=1_000_100)
    issued, sig = token.split(".")
    assert not auth.verify_token(secret, f"{int(issued) + 1}.{sig}", now=1_000_100)
    assert not auth.verify_token(secret, token, now=1_000_000 + auth.SESSION_TTL_S + 1)
    assert not auth.verify_token(secret, auth.issue_token(secret, now=2_000_000), now=1_000_000)
    for bad in (None, "", "nodot", "abc.def"):
        assert not auth.verify_token(secret, bad)


def test_login_limiter_locks_after_consecutive_failures_and_success_resets():
    limiter = auth.LoginLimiter(max_failures=3, lockout_s=60)
    limiter.record(False, now=0)
    limiter.record(False, now=1)
    limiter.record(True, now=2)
    limiter.record(False, now=3)
    limiter.record(False, now=4)
    assert limiter.locked_for(now=5) == 0
    limiter.record(False, now=5)
    assert limiter.locked_for(now=6) == pytest.approx(59)
    assert limiter.locked_for(now=66) == 0


# ---- 配置 ----


def test_config_from_env_parses_lists_and_derives_secret_from_password(tmp_path):
    env = {
        "SKILL_RUNNER_HOME": str(tmp_path),
        "SKILL_RUNNER_PASSWORD": "a",
        "SKILL_RUNNER_SKILLS": "x, y",
        "SKILL_RUNNER_EXTRA_WRITE": os.pathsep.join(["/srv/a", "/srv/b.json"]),
        "SKILL_RUNNER_UNSANDBOXED_COMMANDS": "python scripts/tts.py *; ffmpeg -i *",
        "SKILL_RUNNER_SANDBOX": "0",
    }
    config = Config.from_env(env)
    assert config.runs_dir == tmp_path / "runs"
    assert config.skills == ("x", "y")
    assert config.extra_write == (Path("/srv/a"), Path("/srv/b.json"))
    assert config.unsandboxed_commands == ("python scripts/tts.py *", "ffmpeg -i *")
    assert config.sandbox is False
    assert config.cookie_secure is True
    # 改口令即换签名密钥，旧 cookie 全部失效
    assert Config.from_env({**env, "SKILL_RUNNER_PASSWORD": "b"}).session_secret != config.session_secret
    assert Config.from_env({"SKILL_RUNNER_HOME": str(tmp_path)}).skills == DEFAULT_SKILLS


# ---- 存储 ----


def test_meta_roundtrip_and_listing_order(tmp_path):
    store = RunStore(tmp_path)
    first = store.create("four-step-translate", "a")
    second = store.create("four-step-translate", "b")
    first.status = "running"
    store.save_meta(first)
    assert store.load_meta(first.id).status == "running"
    assert {m.id for m in store.list_meta()} == {first.id, second.id}
    assert (store.run_dir(first.id) / "input").is_dir()
    assert store.load_meta("../etc") is None
    with pytest.raises(KeyError):
        store.run_dir("../../etc")


def test_events_append_read_after_seq_and_skip_torn_line(tmp_path):
    store = RunStore(tmp_path)
    run = store.create("s", "t")
    for seq in (1, 2, 3):
        store.append_event(run.id, {"seq": seq, "type": "text"})
    with open(store.run_dir(run.id) / "events.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"seq": 4, "type": "te')  # 进程被杀时留下的残行
    assert [e["seq"] for e in store.read_events(run.id, after_seq=1)] == [2, 3]
    assert store.last_seq(run.id) == 3


def test_upload_sanitizes_dedupes_and_removes_oversized(tmp_path):
    store = RunStore(tmp_path)
    run = store.create("s", "t")
    assert store.save_upload(run.id, "../../a b.html", io.BytesIO(b"x"), 10) == "input/a b.html"
    assert store.save_upload(run.id, "a b.html", io.BytesIO(b"y"), 10) == "input/a b-1.html"
    with pytest.raises(UploadTooLarge):
        store.save_upload(run.id, "big.bin", io.BytesIO(b"z" * 11), 10)
    assert not (store.run_dir(run.id) / "input" / "big.bin").exists()
    assert safe_filename(".env") == "env"
    assert safe_filename('a<b>:"c".txt') == "a_b___c_.txt"
    assert safe_filename("") == "file"


def test_file_listing_hides_internal_and_hidden_entries(tmp_path):
    store = RunStore(tmp_path)
    run = store.create("s", "t")
    root = store.run_dir(run.id)
    store.append_event(run.id, {"seq": 1})
    (root / "out").mkdir()
    (root / "out" / "zh.md").write_text("中文", encoding="utf-8")
    (root / ".claude").mkdir()
    (root / ".claude" / "x.json").write_text("{}")
    (root / ".secret").write_text("x")
    paths = [f["path"] for f in store.list_files(run.id)]
    assert paths == ["out/zh.md"]
    assert store.resolve_file(run.id, "out/zh.md") == Path(os.path.realpath(root / "out" / "zh.md"))
    for bad in ("../" + run.id + "/meta.json", "meta.json", "events.jsonl", ".claude/x.json", ".secret", "out", "nope"):
        assert store.resolve_file(run.id, bad) is None, bad


def test_resolve_file_rejects_symlink_escape(tmp_path):
    store = RunStore(tmp_path / "runs")
    run = store.create("s", "t")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    try:
        os.symlink(outside, store.run_dir(run.id) / "link.txt")
    except (OSError, NotImplementedError):
        pytest.skip("当前系统不能创建符号链接")
    assert store.resolve_file(run.id, "link.txt") is None


def test_catalog_reads_description_and_flags_missing_skill(tmp_path):
    skill = tmp_path / "four-step-translate"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: four-step-translate\ndescription: 四步翻译\n---\n", encoding="utf-8")
    catalog = iter_skill_catalog(tmp_path, ["four-step-translate", "missing"])
    assert catalog == [
        {"name": "four-step-translate", "description": "四步翻译", "available": True},
        {"name": "missing", "description": "", "available": False},
    ]


# ---- 权限策略 ----


def test_policy_limits_writes_to_run_dir_and_whitelist(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    glossary = tmp_path / "glossary" / "global.json"
    kwargs = {"run_dir": run_dir, "extra_write": (glossary,), "sandbox": True}
    assert policy.decide("Write", {"file_path": str(run_dir / "out" / "zh.md")}, **kwargs).allow
    assert policy.decide("Edit", {"file_path": "relative/zh.md"}, **kwargs).allow
    assert policy.decide("Edit", {"file_path": str(glossary)}, **kwargs).allow
    assert policy.decide("NotebookEdit", {"notebook_path": str(run_dir / "a.ipynb")}, **kwargs).allow
    denied = policy.decide("Write", {"file_path": str(tmp_path / "elsewhere.txt")}, **kwargs)
    assert not denied.allow and "只能写当前运行目录" in denied.message
    assert not policy.decide("Write", {"file_path": str(run_dir / ".." / "x")}, **kwargs).allow
    assert not policy.decide("Write", {}, **kwargs).allow


def test_policy_blocks_unsandboxed_bash_only_when_sandbox_on(tmp_path):
    common = {"run_dir": tmp_path, "extra_write": ()}
    assert not policy.decide("Bash", {"command": "ls"}, sandbox=True, **common).allow
    assert policy.decide("Bash", {"command": "ls"}, sandbox=False, **common).allow
    assert policy.decide("WebFetch", {"url": "https://x"}, sandbox=True, **common).allow


def test_policy_allows_everything_without_sandbox(tmp_path):
    common = {"run_dir": tmp_path / "run", "extra_write": (), "sandbox": False}
    assert policy.decide("Write", {"file_path": str(tmp_path / "elsewhere.txt")}, **common).allow
    assert policy.decide("Edit", {"file_path": "/etc/hosts"}, **common).allow


def test_policy_rejects_write_through_symlinked_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, run_dir / "escape", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("当前系统不能创建符号链接")
    decision = policy.decide(
        "Write", {"file_path": str(run_dir / "escape" / "x.txt")}, run_dir=run_dir, extra_write=(), sandbox=True
    )
    assert not decision.allow


def test_sse_event_payload_is_json_with_seq_id():
    from skill_runner.app import _sse

    frame = _sse({"seq": 7, "type": "text", "text": "你好"})
    assert frame.startswith("id: 7\ndata: ")
    assert json.loads(frame.split("data: ", 1)[1]) == {"seq": 7, "type": "text", "text": "你好"}
