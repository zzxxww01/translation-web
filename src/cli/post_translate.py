#!/usr/bin/env python3
"""Translate a social-media post through the local Translation Agent API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:54321"
DEFAULT_TIMEOUT_SECONDS = 190.0
MAX_POST_CONTENT_LENGTH = 10_000


class CliError(RuntimeError):
    """A user-facing CLI error."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="translate-post",
        description="调用 Translation Agent 的帖子翻译链路，将帖子翻译成中文。",
        epilog="未提供 TEXT 或 --file 时，从标准输入读取原文。",
    )
    parser.add_argument("text", metavar="TEXT", nargs="?", help="待翻译帖子（建议用引号包裹）")
    parser.add_argument("-f", "--file", type=Path, help="从 UTF-8 文本文件读取原文")
    parser.add_argument("--model", help="指定服务中已配置的模型；默认使用帖子翻译默认模型")
    parser.add_argument(
        "--base-url",
        default=os.getenv("TRANSLATION_SERVICE_URL", DEFAULT_BASE_URL),
        help=(
            "翻译服务地址（默认 %(default)s；也可设置 "
            "TRANSLATION_SERVICE_URL）"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP 请求超时秒数（默认 %(default)s）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="输出含模型元数据的完整 JSON，而不是只输出译文",
    )
    return parser


def _read_content(args: argparse.Namespace) -> str:
    if args.text is not None and args.file is not None:
        raise CliError("TEXT 与 --file 不能同时使用")

    if args.file is not None:
        try:
            content = args.file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CliError(f"无法读取文件 {args.file}: {exc}") from exc
    elif args.text is not None:
        content = args.text
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        raise CliError("请提供 TEXT、--file，或通过标准输入传入帖子原文")

    if not content.strip():
        raise CliError("帖子原文不能为空")
    if len(content) > MAX_POST_CONTENT_LENGTH:
        raise CliError(
            f"帖子原文过长：{len(content)} 个字符，服务上限为 {MAX_POST_CONTENT_LENGTH}"
        )
    return content


def _endpoint(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base:
        raise CliError("--base-url 不能为空")
    if not base.startswith(("http://", "https://")):
        raise CliError("--base-url 必须以 http:// 或 https:// 开头")
    return f"{base}/api/translate/post"


def _error_detail(raw: bytes, fallback: str) -> str:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return fallback

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if detail is not None:
            return json.dumps(detail, ensure_ascii=False)
    return fallback


def translate_post(
    content: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Call the post translation endpoint and return its decoded response."""
    if timeout <= 0:
        raise CliError("--timeout 必须大于 0")

    payload: dict[str, Any] = {"content": content}
    if model:
        payload["model"] = model

    request = Request(
        _endpoint(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        raw = exc.read()
        detail = _error_detail(raw, exc.reason or f"HTTP {exc.code}")
        raise CliError(f"翻译服务返回 HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise CliError(f"无法连接翻译服务 {_endpoint(base_url)}: {reason}") from exc
    except TimeoutError as exc:
        raise CliError(f"翻译请求在 {timeout:g} 秒后超时") from exc

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CliError("翻译服务返回了无效的 JSON") from exc

    if not isinstance(result, dict):
        raise CliError("翻译服务返回格式错误：预期 JSON 对象")
    translation = result.get("translation")
    if not isinstance(translation, str) or not translation.strip():
        raise CliError("翻译服务未返回有效译文")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        content = _read_content(args)
        result = translate_post(
            content,
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout,
        )
    except CliError as exc:
        print(f"translate-post: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["translation"].strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
