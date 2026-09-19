# -*- coding: utf-8 -*-
"""Tests for the Slack reply command-line client."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from src.cli import slack_reply


class _FakeResponse:
    def __init__(self, payload: dict):
        self.raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.raw


def _variants() -> list[dict[str, str]]:
    return [
        {"version": "A", "english": "Sure, will do.", "chinese": "好的。", "style": "简洁"},
        {"version": "B", "english": "Sure, I'll take care of it.", "chinese": "好的，我来处理。", "style": "正式"},
        {"version": "C", "english": "Absolutely, happy to help with this.", "chinese": "当然，很乐意帮忙。", "style": "友好"},
    ]


class SlackReplyCliTests(unittest.TestCase):
    def test_incoming_mode_calls_process_endpoint(self) -> None:
        response = {"translation": "你能看一下吗？", "suggested_replies": _variants()}
        history = [{"role": "me", "content": "I can review it today."}]
        with patch.object(
            slack_reply, "urlopen", return_value=_FakeResponse(response)
        ) as mock_urlopen:
            mode, result = slack_reply.generate_slack_reply(
                "Could you take a look?",
                mode="incoming",
                history=history,
                base_url="http://translation.test/",
                timeout=12,
            )

        self.assertEqual(mode, "incoming")
        self.assertEqual(result, response)
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://translation.test/api/slack/process")
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 12)
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"message": "Could you take a look?", "conversation_history": history},
        )

    def test_compose_mode_calls_compose_endpoint(self) -> None:
        response = {"versions": _variants()}
        with patch.object(
            slack_reply, "urlopen", return_value=_FakeResponse(response)
        ) as mock_urlopen:
            mode, result = slack_reply.generate_slack_reply(
                "好的，我今天处理。",
                mode="compose",
                base_url="http://translation.test",
            )

        self.assertEqual(mode, "compose")
        self.assertEqual(result, response)
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://translation.test/api/slack/compose")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"content": "好的，我今天处理。", "conversation_history": []},
        )

    def test_auto_mode_matches_frontend_chinese_ratio_rule(self) -> None:
        self.assertEqual(slack_reply._resolve_mode("好的，我来处理。", "auto"), "compose")
        self.assertEqual(slack_reply._resolve_mode("Could you review this?", "auto"), "incoming")
        self.assertEqual(slack_reply._resolve_mode("GPU 版本 OK", "auto"), "incoming")
        self.assertEqual(slack_reply._resolve_mode("anything", "compose"), "compose")

    def test_main_reads_stdin_and_prints_incoming_result(self) -> None:
        stdin = io.StringIO("Could you review this?")
        stdout = io.StringIO()
        result = {"translation": "你能审核一下吗？", "suggested_replies": _variants()}
        with patch.object(slack_reply.sys, "stdin", stdin), patch.object(
            stdin, "isatty", return_value=False
        ), patch.object(
            slack_reply,
            "generate_slack_reply",
            return_value=("incoming", result),
        ), redirect_stdout(stdout):
            exit_code = slack_reply.main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("中文理解：\n\n你能审核一下吗？", stdout.getvalue())
        self.assertIn("A（简洁）：\n\nSure, will do.", stdout.getvalue())

    def test_pick_outputs_only_selected_english_version(self) -> None:
        stdout = io.StringIO()
        with patch.object(
            slack_reply,
            "generate_slack_reply",
            return_value=("compose", {"versions": _variants()}),
        ), redirect_stdout(stdout):
            exit_code = slack_reply.main(["--pick", "b", "我来处理"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "Sure, I'll take care of it.\n")

    def test_history_file_is_validated_and_sent(self) -> None:
        history = [
            {"role": "them", "content": "Can you review this?"},
            {"role": "me", "content": "Yes, send it over."},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(history), encoding="utf-8")
            self.assertEqual(slack_reply._read_history(path), history)

            path.write_text('[{"role":"other","content":"bad"}]', encoding="utf-8")
            with self.assertRaisesRegex(slack_reply.CliError, "role 必须是 me 或 them"):
                slack_reply._read_history(path)

    def test_http_error_is_reported_without_traceback(self) -> None:
        error = HTTPError(
            "http://translation.test/api/slack/process",
            503,
            "Service Unavailable",
            Message(),
            io.BytesIO('{"detail":"模型暂时不可用"}'.encode("utf-8")),
        )
        stderr = io.StringIO()
        with patch.object(slack_reply, "urlopen", side_effect=error), redirect_stderr(
            stderr
        ):
            exit_code = slack_reply.main(
                ["--base-url", "http://translation.test", "Could you help?"]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("HTTP 503: 模型暂时不可用", stderr.getvalue())

    def test_json_outputs_full_service_response(self) -> None:
        result = {"versions": _variants()}
        stdout = io.StringIO()
        with patch.object(
            slack_reply,
            "generate_slack_reply",
            return_value=("compose", result),
        ), redirect_stdout(stdout):
            exit_code = slack_reply.main(["--json", "好的，我来处理"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), result)


if __name__ == "__main__":
    unittest.main()
