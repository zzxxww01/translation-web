"""translation-agent CLI：stdout 只有一个 JSON、退出码、since 解析、脱敏、SSH 白名单。"""

import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from src.cli import automation as cli


class _Std:
    def __init__(self):
        self.buffer = io.BytesIO()

    def flush(self):
        pass

    def text(self):
        return self.buffer.getvalue().decode("utf-8")


@pytest.fixture
def std(monkeypatch):
    # pytest 在 setup 和 call 之间会换回自己的 sys.stdout，所以到 _run 里才替换
    return SimpleNamespace(out=_Std(), err=_Std(), monkeypatch=monkeypatch)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture(monkeypatch, payload=None, error=None):
    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        if error:
            raise error
        return _Response(payload or {})

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)
    return seen


def _run(std, argv):
    std.monkeypatch.setattr(cli.sys, "stdout", std.out)
    std.monkeypatch.setattr(cli.sys, "stderr", std.err)
    code = cli.run(argv)
    lines = std.out.text().splitlines()
    assert len(lines) == 1  # stdout 只有一个 JSON 对象
    return code, json.loads(lines[0])


@pytest.mark.parametrize("value,expected", [
    ("1763424000", 1763424000.0),
    ("1763424000123", 1763424000.123),
    ("2025-11-18T00:00:00Z", 1763424000.0),
    ("2025-11-18T08:00:00+08:00", 1763424000.0),
    ("2025-11-18T00:00:00", 1763424000.0),
    ("2025-11-18T00:00:00.500000Z", 1763424000.5),
])
def test_parse_since(value, expected):
    assert cli.parse_since(value) == pytest.approx(expected)


def test_updates_calls_internal_endpoint(std, monkeypatch):
    seen = _capture(monkeypatch, {"new_articles": [], "mentions": [], "watermark": "2025-11-18T00:00:00Z"})
    code, out = _run(std, ["updates", "--since", "2025-11-18T00:00:00Z"])
    assert code == 0 and out["watermark"] == "2025-11-18T00:00:00Z"
    assert seen[0].full_url == "http://127.0.0.1:54321/internal/automation/updates?since=1763424000.000000"
    assert "GET /internal/automation/updates" in std.err.text()


def test_translate_article_posts_slug(std, monkeypatch):
    seen = _capture(monkeypatch, {"project_id": "p", "status": "started"})
    code, out = _run(std, ["translate-article", "nvidia-gb300", "--target-lang", "zh"])
    assert code == 0 and out["status"] == "started"
    assert json.loads(seen[0].data) == {"article": "nvidia-gb300", "target_lang": "zh"}
    assert seen[0].get_method() == "POST"


@pytest.mark.parametrize("bad", ["../etc", "a b", "-x", ""])
def test_translate_article_rejects_bad_input(std, monkeypatch, bad):
    seen = _capture(monkeypatch)
    code, out = _run(std, ["translate-article", "--", bad])
    assert code == 1 and out["code"] == "BAD_ARGUMENT" and seen == []


def test_status_quotes_project_id_and_with_markdown(std, monkeypatch):
    seen = _capture(monkeypatch, {"status": "done"})
    _run(std, ["status", "中文项目", "--with-markdown"])
    assert "/projects/%E4%B8%AD%E6%96%87%E9%A1%B9%E7%9B%AE/status?with_markdown=true" in seen[0].full_url
    code, out = _run_fresh(std, monkeypatch, ["status", "../x"])
    assert code == 1


def _run_fresh(std, monkeypatch, argv):
    std.out.buffer = io.BytesIO()
    return _run(std, argv)


def test_http_error_becomes_json_with_exit_3(std, monkeypatch):
    body = io.BytesIO(json.dumps({"detail": "Project not found", "error_code": "NOT_FOUND"}).encode())
    _capture(monkeypatch, error=HTTPError("u", 404, "nf", {}, body))
    code, out = _run(std, ["status", "p1"])
    assert code == 3 and out == {"error": "Project not found", "code": "NOT_FOUND"}


def test_unreachable_service_exit_2(std, monkeypatch):
    _capture(monkeypatch, error=URLError("refused"))
    code, out = _run(std, ["health"])
    assert code == 2 and out["code"] == "SERVICE_UNREACHABLE"


def test_usage_error_is_json(std):
    code, out = _run(std, ["updates"])
    assert code == 1 and "error" in out


def test_translate_slack_posts_body(std, monkeypatch):
    seen = _capture(monkeypatch, {"project_id": "slack-C0123456789-1763424000.000200", "status": "done"})
    code, out = _run(std, ["translate-slack", "C0123456789", "1763424000.000200",
                           "--thread-ts", "1763424000.000100", "--with-thread"])
    assert code == 0 and out["status"] == "done"
    assert seen[0].full_url.endswith("/internal/automation/translate-slack")
    assert json.loads(seen[0].data) == {"conversation_id": "C0123456789", "message_ts": "1763424000.000200",
                                        "thread_ts": "1763424000.000100", "with_thread": True}


@pytest.mark.parametrize("argv", [
    ["translate-slack", "bad", "1763424000.000100"],
    ["translate-slack", "C0123456789", "nope"],
    ["translate-slack", "C0123456789", "1763424000.000100", "--thread-ts", "x"],
])
def test_translate_slack_rejects_bad_ids(std, monkeypatch, argv):
    seen = _capture(monkeypatch)
    code, out = _run(std, argv)
    assert code == 1 and seen == []


def test_unexpected_exception_still_json(std, monkeypatch):
    monkeypatch.setitem(cli.COMMANDS, "health", lambda args: 1 / 0)
    code, out = _run(std, ["health"])
    assert code == 3 and out["code"] == "INTERNAL"


@pytest.mark.parametrize("secret", [
    "xoxc-1234-5678-abcdef",
    "xoxd-AbC%2Fdef",
    "sk-proj-abcdefghijklmnop",
    "AIzaSyA1234567890abcdefghijklmnop",
    "substack.sid=s%3Aabcdef.ghijk",
    "Bearer abcdefghijklmnop",
])
def test_redact_scrubs_secrets(std, monkeypatch, secret):
    _capture(monkeypatch, {"status": "healthy", "note": f"leak {secret} here"})
    code, out = _run(std, ["health"])
    assert secret not in json.dumps(out) and "[redacted]" in out["note"]


def test_redact_keeps_normal_output():
    text = json.dumps({"status": "healthy", "substack": "cookie_missing", "token_count": 12}, ensure_ascii=False)
    assert cli.redact(text) == text


# ---------------------------------------------------------------- --ssh


def test_ssh_mode_runs_whitelisted_command(std, monkeypatch):
    seen = _capture(monkeypatch, {"status": "healthy"})
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "translation-agent health")
    code, out = _run(std, ["--ssh"])
    assert code == 0 and out["status"] == "healthy"
    assert seen[0].full_url.startswith("http://127.0.0.1:54321/")


@pytest.mark.parametrize("command", [
    "cat .env",
    "bash -c id",
    "",
    "health; cat .env",
    "updates --since 0 --base-url http://evil",
    "status 'unterminated",
])
def test_ssh_mode_rejects_anything_else(std, monkeypatch, command):
    seen = _capture(monkeypatch)
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", command)
    code, out = _run(std, ["--ssh"])
    assert code != 0 and "error" in out and seen == []


def test_ssh_mode_ignores_env_base_url(std, monkeypatch):
    seen = _capture(monkeypatch, {"status": "healthy"})
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "health")
    monkeypatch.setenv("TRANSLATION_SERVICE_URL", "http://evil.example")
    _run(std, ["--ssh"])
    assert seen[0].full_url.startswith("http://127.0.0.1:54321/")


# ---------------------------------------------------------------- 待办 / 翻译记录 / 帖子流程

DRAFT_ID = "s_C0123456789_1763424000_000100"


def test_slack_todos_and_drafts(std, monkeypatch):
    seen = _capture(monkeypatch, {"items": [], "fyi": []})
    code, _ = _run(std, ["slack-todos"])
    assert code == 0 and seen[0].full_url.endswith("/internal/automation/slack-todos")
    std.out.buffer.seek(0)
    std.out.buffer.truncate()
    _run(std, ["drafts", "--source", "slack", "--q", "AI racks"])
    assert seen[1].full_url.endswith("/internal/automation/drafts?status=draft&limit=50&source=slack&q=AI+racks")


def test_draft_keeps_image_data_intact(std, monkeypatch):
    # 随机字节的 base64 偶尔长得像密钥（/AIza…），不能被脱敏改坏
    blob = "/AIzaSyA1234567890abcdefghijklmnop+xoxc-not"
    seen = _capture(monkeypatch, {"draft_id": DRAFT_ID, "note": "AIzaSyA1234567890abcdefghijklmnop",
                                  "images": [{"n": 1, "data_base64": blob}]})
    code, out = _run(std, ["draft", DRAFT_ID])
    assert code == 0 and out["images"][0]["data_base64"] == blob
    assert out["note"] == "[redacted]"
    assert seen[0].full_url.endswith(f"/internal/automation/drafts/{DRAFT_ID}")
    std.out.buffer.seek(0)
    std.out.buffer.truncate()
    _run(std, ["draft", DRAFT_ID, "--no-images"])
    assert seen[1].full_url.endswith("?images=false")


def test_translate_slack_post_body(std, monkeypatch):
    seen = _capture(monkeypatch, {"draft_id": DRAFT_ID})
    code, _ = _run(std, ["translate-slack-post", "C0123456789", "1763424000.000100", "--instruction", "翻第二版"])
    assert code == 0 and seen[0].full_url.endswith("/internal/automation/translate-slack-post")
    assert json.loads(seen[0].data) == {"conversation_id": "C0123456789", "thread_ts": "1763424000.000100",
                                        "instruction": "翻第二版", "with_images": True}


@pytest.mark.parametrize("argv", [
    ["draft", "../etc/passwd"],
    ["draft", "s_bad"],
    ["translate-slack-post", "bad", "1763424000.000100"],
    ["drafts", "--status", "weird"],
])
def test_new_commands_reject_bad_input(std, monkeypatch, argv):
    seen = _capture(monkeypatch)
    code, _ = _run(std, argv)
    assert code == 1 and seen == []


def test_ssh_mode_allows_new_commands(std, monkeypatch):
    seen = _capture(monkeypatch, {"items": []})
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "translation-agent drafts --status all")
    code, _ = _run(std, ["--ssh"])
    assert code == 0 and "status=all" in seen[0].full_url


# ---------------------------------------------------------------- translate-post / slack-reply


class _Stdin:
    def __init__(self, text, tty=False):
        self.buffer = io.BytesIO(text.encode("utf-8"))
        self.tty = tty

    def isatty(self):
        return self.tty


def test_translate_post_text_from_argument_or_stdin(std, monkeypatch):
    seen = _capture(monkeypatch, {"translation": "你好"})
    code, out = _run(std, ["translate-post", "Hello"])
    assert code == 0 and out["translation"] == "你好"
    assert seen[0].full_url.endswith("/internal/automation/translate-post")
    assert json.loads(seen[0].data) == {"content": "Hello", "hashtags": False}
    std.out.buffer.seek(0)
    std.out.buffer.truncate()
    monkeypatch.setattr(cli.sys, "stdin", _Stdin("Long post\nwith 'quotes'"))
    _run(std, ["translate-post", "--hashtags"])
    assert json.loads(seen[1].data) == {"content": "Long post\nwith 'quotes'", "hashtags": True}


@pytest.mark.parametrize("argv,stdin", [
    (["translate-post"], _Stdin("", tty=True)),
    (["translate-post", "   "], None),
    (["translate-post", "x" * 10001], None),
    (["slack-reply", "hi", "--history", "not json"], None),
    (["slack-reply", "hi", "--history", '[{"role":"boss","content":"x"}]'], None),
    (["slack-reply", "hi", "--mode", "weird"], None),
    (["slack-reply", "hi", "--history", '[{"role":[],"content":"x"}]'], None),
    (["slack-reply", "hi", "--history", '[{"role":"them","content":"  "}]'], None),
    (["slack-reply", "hi", "--history", '[{"role":"them","content":"%s"}]' % ("x" * 50001)], None),
    (["slack-reply", "hi", "--history", json.dumps([{"role": "me", "content": "x"}] * 101)], None),
    (["translate-post"], _Stdin("")),
])
def test_translate_post_and_slack_reply_reject_bad_input(std, monkeypatch, argv, stdin):
    seen = _capture(monkeypatch)
    if stdin is not None:
        monkeypatch.setattr(cli.sys, "stdin", stdin)
    code, _ = _run(std, argv)
    assert code == 1 and seen == []


def test_slack_reply_body(std, monkeypatch):
    seen = _capture(monkeypatch, {"mode": "incoming", "replies": []})
    history = '[{"role":"them","content":"Can you check?"}]'
    code, _ = _run(std, ["slack-reply", "Looks good", "--history", history])
    assert code == 0 and seen[0].full_url.endswith("/internal/automation/slack-reply")
    assert json.loads(seen[0].data) == {"text": "Looks good", "mode": "auto",
                                        "history": [{"role": "them", "content": "Can you check?"}]}


def test_ssh_mode_allows_translate_post_with_stdin(std, monkeypatch):
    seen = _capture(monkeypatch, {"translation": "你好"})
    monkeypatch.setenv("SSH_ORIGINAL_COMMAND", "translation-agent translate-post")
    monkeypatch.setattr(cli.sys, "stdin", _Stdin("Hello"))
    code, _ = _run(std, ["--ssh"])
    assert code == 0 and json.loads(seen[0].data)["content"] == "Hello"


def test_invalid_utf8_stdin_is_rejected(std, monkeypatch):
    seen = _capture(monkeypatch)
    stdin = _Stdin("")
    stdin.buffer = io.BytesIO(b"Hello \xff")
    monkeypatch.setattr(cli.sys, "stdin", stdin)
    code, out = _run(std, ["translate-post"])
    assert code == 1 and "UTF-8" in out["error"] and seen == []


def test_validation_error_keeps_field_reasons(std, monkeypatch):
    payload = json.dumps({"detail": "Request validation failed", "errors": [
        {"field": "body.content", "message": "String should have at most 10000 characters"}]}).encode()
    error = HTTPError("http://x", 422, "Unprocessable", {}, io.BytesIO(payload))
    _capture(monkeypatch, error=error)
    code, out = _run(std, ["translate-post", "Hello"])
    assert code == 3 and out["code"] == "HTTP_422"
    assert out["error"] == "Request validation failed：content: String should have at most 10000 characters"
