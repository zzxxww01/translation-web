"""Regression coverage for CLI paths and malformed inputs/responses."""

import io
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli import post_translate, slack_reply


@pytest.mark.parametrize("command,module", [("slack-reply", "slack_reply"), ("translate-post", "post_translate")])
@pytest.mark.parametrize("use_venv", [False, True])
def test_wrapper_reads_relative_paths_from_caller(tmp_path, command, module, use_venv):
    root = Path(__file__).resolve().parents[3]
    install = tmp_path / "installation with spaces"
    caller = tmp_path / "caller"
    caller.mkdir()
    (install / "src" / "cli").mkdir(parents=True)
    shutil.copy2(root / command, install / command)
    shutil.copy2(root / "src" / "cli" / f"{module}.py", install / "src" / "cli")
    for package in [install / "src", install / "src" / "cli"]:
        (package / "__init__.py").touch()
    if use_venv:
        bin_dir = install / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").symlink_to(sys.executable)
    (caller / "input.txt").write_text("Hello from caller", encoding="utf-8")
    (install / "input.txt").write_text("Wrong installation input", encoding="utf-8")
    history = [{"role": "them", "content": "Earlier caller message"}]
    (caller / "history.json").write_text(json.dumps(history), encoding="utf-8")
    (install / "history.json").write_text("[]", encoding="utf-8")
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            response = {"translation": "译文", "suggested_replies": [{"version": "A", "english": "Sure."}]}
            body = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        args = [str(install / command), "--file", "input.txt", "--base-url", f"http://127.0.0.1:{server.server_port}"]
        if command == "slack-reply":
            args += ["--history", "history.json"]
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["NO_PROXY"] = "127.0.0.1"
        result = subprocess.run(args, cwd=caller, env=env, text=True, capture_output=True, timeout=10)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    assert result.returncode == 0, result.stderr
    assert len(requests) == 1
    if command == "slack-reply":
        assert requests[0] == ("/api/slack/process", {"message": "Hello from caller", "conversation_history": history})
    else:
        assert requests[0] == ("/api/translate/post", {"content": "Hello from caller"})


@pytest.mark.parametrize("module", [post_translate, slack_reply])
def test_invalid_utf8_content_is_friendly_error(tmp_path, capsys, module):
    path = tmp_path / "invalid.txt"
    path.write_bytes(b"\xff")
    with patch.object(module, "urlopen") as request:
        assert module.main(["--file", str(path)]) == 1
    captured = capsys.readouterr()
    assert "无法读取文件" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out
    request.assert_not_called()


def test_invalid_utf8_history_is_friendly_error(tmp_path, capsys):
    path = tmp_path / "history.json"
    path.write_bytes(b"\xff")
    with patch.object(slack_reply, "urlopen") as request:
        assert slack_reply.main(["Hello", "--history", str(path)]) == 1
    assert "无法读取对话历史文件" in capsys.readouterr().err
    request.assert_not_called()


@pytest.mark.parametrize("role", [[], {}])
def test_unhashable_history_role_is_friendly_error(tmp_path, capsys, role):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([{"role": role, "content": "Hello"}]), encoding="utf-8")
    with patch.object(slack_reply, "urlopen") as request:
        assert slack_reply.main(["Hello", "--history", str(path)]) == 1
    assert "role 必须是 me 或 them" in capsys.readouterr().err
    request.assert_not_called()


@pytest.mark.parametrize("mode,key", [("incoming", "suggested_replies"), ("compose", "versions")])
def test_null_english_is_not_valid_reply(mode, key):
    response = {"translation": "译文", key: [{"version": "A", "english": None}]}
    with patch.object(slack_reply, "urlopen", return_value=io.BytesIO(json.dumps(response).encode())):
        with pytest.raises(slack_reply.CliError, match="未返回有效的英文回复"):
            slack_reply.generate_slack_reply("Hello", mode=mode)


@pytest.mark.parametrize("mode,key", [("incoming", "suggested_replies"), ("compose", "versions")])
def test_null_english_is_skipped_in_plain_output_and_rejected_by_pick(mode, key):
    response = {"translation": "译文", key: [{"version": "A", "english": None}, {"version": "B", "english": "Sure."}]}
    output = slack_reply._format_plain(mode, response)
    assert "None" not in output
    assert "A：" not in output
    assert "Sure." in output
    with pytest.raises(slack_reply.CliError, match="未返回有效的 A 版本"):
        slack_reply._pick_variant(mode, response, "A")
    assert slack_reply._pick_variant(mode, response, "B") == "Sure."
