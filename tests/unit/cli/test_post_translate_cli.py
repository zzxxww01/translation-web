# -*- coding: utf-8 -*-
"""Tests for the post translation command-line client."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError

from src.cli import post_translate


class _FakeResponse:
    def __init__(self, payload: dict):
        self.raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self.raw


class PostTranslateCliTests(unittest.TestCase):
    def test_translate_post_sends_content_and_optional_model(self) -> None:
        response = {
            "translation": "英伟达发布了新芯片。",
            "model_used": "configured-model",
            "provider_used": "configured-provider",
            "fallback_used": False,
        }
        with patch.object(
            post_translate, "urlopen", return_value=_FakeResponse(response)
        ) as mock_urlopen:
            result = post_translate.translate_post(
                "NVIDIA launched a new chip.",
                base_url="http://translation.test/",
                model="my-model",
                timeout=12,
            )

        self.assertEqual(result, response)
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://translation.test/api/translate/post")
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 12)
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"content": "NVIDIA launched a new chip.", "model": "my-model"},
        )

    def test_main_reads_stdin_and_prints_only_translation_by_default(self) -> None:
        stdin = io.StringIO("Hello from stdin")
        stdout = io.StringIO()
        with patch.object(post_translate.sys, "stdin", stdin), patch.object(
            stdin, "isatty", return_value=False
        ), patch.object(
            post_translate,
            "translate_post",
            return_value={"translation": "来自标准输入的问候。"},
        ) as mock_translate, redirect_stdout(stdout):
            exit_code = post_translate.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "来自标准输入的问候。\n")
        mock_translate.assert_called_once()
        self.assertEqual(mock_translate.call_args.args[0], "Hello from stdin")

    def test_main_json_outputs_metadata(self) -> None:
        result = {
            "translation": "译文",
            "model_used": "model-a",
            "provider_used": "provider-a",
            "fallback_used": True,
        }
        stdout = io.StringIO()
        with patch.object(
            post_translate, "translate_post", return_value=result
        ), redirect_stdout(stdout):
            exit_code = post_translate.main(["--json", "source"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), result)

    def test_http_error_is_reported_without_traceback(self) -> None:
        error = HTTPError(
            "http://translation.test/api/translate/post",
            503,
            "Service Unavailable",
            Message(),
            io.BytesIO('{"detail":"模型暂时不可用"}'.encode("utf-8")),
        )
        stderr = io.StringIO()
        with patch.object(post_translate, "urlopen", side_effect=error), redirect_stderr(
            stderr
        ):
            exit_code = post_translate.main(
                ["--base-url", "http://translation.test", "source"]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("HTTP 503: 模型暂时不可用", stderr.getvalue())

    def test_empty_stdin_is_rejected_before_request(self) -> None:
        stdin = io.StringIO(" \n")
        stderr = io.StringIO()
        with patch.object(post_translate.sys, "stdin", stdin), patch.object(
            stdin, "isatty", return_value=False
        ), patch.object(post_translate, "urlopen") as mock_urlopen, redirect_stderr(stderr):
            exit_code = post_translate.main([])

        self.assertEqual(exit_code, 1)
        self.assertIn("帖子原文不能为空", stderr.getvalue())
        mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
