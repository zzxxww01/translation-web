#!/usr/bin/env python3
"""Generate Slack replies through the local Translation Agent API."""

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
MAX_CONTENT_LENGTH = 50_000
MAX_HISTORY_MESSAGES = 100
VALID_ROLES = {"me", "them"}
VALID_VERSIONS = {"A", "B", "C"}


class CliError(RuntimeError):
    """A user-facing CLI error."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slack-reply",
        description="调用 Translation Agent 的 Slack 回复链路生成英文回复。",
        epilog=(
            "auto 模式会复用网页规则：中文占比超过 30%% 时按中文草稿生成英文版本，"
            "否则分析对方消息并给出建议回复。"
        ),
    )
    parser.add_argument("text", metavar="TEXT", nargs="?", help="对方消息或中文回复草稿")
    parser.add_argument("-f", "--file", type=Path, help="从 UTF-8 文本文件读取输入")
    parser.add_argument(
        "--mode",
        choices=("auto", "incoming", "compose"),
        default="auto",
        help="incoming=分析对方消息，compose=把中文草稿写成英文，默认 auto",
    )
    parser.add_argument(
        "--history",
        type=Path,
        help='对话历史 JSON 文件，格式为 [{"role":"them|me","content":"..."}]',
    )
    parser.add_argument(
        "--pick",
        choices=("A", "B", "C", "a", "b", "c"),
        help="只输出指定版本的英文，便于直接复制",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="输出服务返回的完整 JSON",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("TRANSLATION_SERVICE_URL", DEFAULT_BASE_URL),
        help="翻译服务地址（默认 %(default)s；也可设置 TRANSLATION_SERVICE_URL）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP 请求超时秒数（默认 %(default)s）",
    )
    return parser


def _read_content(args: argparse.Namespace) -> str:
    if args.text is not None and args.file is not None:
        raise CliError("TEXT 与 --file 不能同时使用")

    if args.file is not None:
        try:
            content = args.file.read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"无法读取文件 {args.file}: {exc}") from exc
    elif args.text is not None:
        content = args.text
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        raise CliError("请提供 TEXT、--file，或通过标准输入传入内容")

    if not content.strip():
        raise CliError("输入内容不能为空")
    if len(content) > MAX_CONTENT_LENGTH:
        raise CliError(
            f"输入过长：{len(content)} 个字符，服务上限为 {MAX_CONTENT_LENGTH}"
        )
    return content


def _read_history(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"无法读取对话历史文件 {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(f"对话历史不是有效 JSON: {exc.msg}") from exc

    if not isinstance(data, list):
        raise CliError("对话历史必须是 JSON 数组")
    if len(data) > MAX_HISTORY_MESSAGES:
        raise CliError(f"对话历史最多包含 {MAX_HISTORY_MESSAGES} 条消息")

    history: list[dict[str, str]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise CliError(f"对话历史第 {index} 项必须是对象")
        role = item.get("role")
        content = item.get("content")
        if role not in VALID_ROLES:
            raise CliError(f"对话历史第 {index} 项的 role 必须是 me 或 them")
        if not isinstance(content, str) or not content.strip():
            raise CliError(f"对话历史第 {index} 项的 content 不能为空")
        if len(content) > MAX_CONTENT_LENGTH:
            raise CliError(
                f"对话历史第 {index} 项过长，服务上限为 {MAX_CONTENT_LENGTH}"
            )
        history.append({"role": role, "content": content})
    return history


def _resolve_mode(content: str, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    compact = "".join(content.split())
    if not compact:
        return "incoming"
    chinese_count = sum("\u4e00" <= char <= "\u9fff" for char in compact)
    return "compose" if chinese_count / len(compact) > 0.3 else "incoming"


def _endpoint(base_url: str, mode: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base:
        raise CliError("--base-url 不能为空")
    if not base.startswith(("http://", "https://")):
        raise CliError("--base-url 必须以 http:// 或 https:// 开头")
    path = "/api/slack/compose" if mode == "compose" else "/api/slack/process"
    return f"{base}{path}"


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


def generate_slack_reply(
    content: str,
    *,
    mode: str = "auto",
    history: list[dict[str, str]] | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[str, dict[str, Any]]:
    """Call the matching Slack endpoint and return (resolved mode, response)."""
    if timeout <= 0:
        raise CliError("--timeout 必须大于 0")
    resolved_mode = _resolve_mode(content, mode)
    payload: dict[str, Any] = {
        "conversation_history": history or [],
        "content" if resolved_mode == "compose" else "message": content,
    }
    endpoint = _endpoint(base_url, resolved_mode)
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = _error_detail(exc.read(), exc.reason or f"HTTP {exc.code}")
        raise CliError(f"Slack 回复服务返回 HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise CliError(f"无法连接 Slack 回复服务 {endpoint}: {reason}") from exc
    except TimeoutError as exc:
        raise CliError(f"Slack 回复请求在 {timeout:g} 秒后超时") from exc

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CliError("Slack 回复服务返回了无效的 JSON") from exc
    if not isinstance(result, dict):
        raise CliError("Slack 回复服务返回格式错误：预期 JSON 对象")

    variants = (
        result.get("versions")
        if resolved_mode == "compose"
        else result.get("suggested_replies")
    )
    if not isinstance(variants, list) or not any(
        isinstance(item, dict) and str(item.get("english", "")).strip()
        for item in variants
    ):
        raise CliError("Slack 回复服务未返回有效的英文回复")
    if resolved_mode == "incoming":
        translation = result.get("translation")
        if not isinstance(translation, str) or not translation.strip():
            raise CliError("Slack 回复服务未返回对方消息的中文理解")
    return resolved_mode, result


def _variants(mode: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    value = result.get("versions" if mode == "compose" else "suggested_replies", [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _pick_variant(mode: str, result: dict[str, Any], version: str) -> str:
    wanted = version.upper()
    for item in _variants(mode, result):
        if str(item.get("version", "")).upper() == wanted:
            english = str(item.get("english", "")).strip()
            if english:
                return english
    raise CliError(f"Slack 回复服务未返回有效的 {wanted} 版本")


def _format_plain(mode: str, result: dict[str, Any]) -> str:
    blocks: list[str] = []
    if mode == "incoming":
        blocks.extend(["中文理解：", str(result["translation"]).strip()])
    for item in _variants(mode, result):
        english = str(item.get("english", "")).strip()
        if not english:
            continue
        version = str(item.get("version", "")).strip() or "?"
        style = str(item.get("style", "")).strip()
        title = f"{version}（{style}）：" if style else f"{version}："
        blocks.extend([title, english])
    return "\n\n".join(blocks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.as_json and args.pick:
        parser.error("--json 与 --pick 不能同时使用")

    try:
        content = _read_content(args)
        history = _read_history(args.history)
        mode, result = generate_slack_reply(
            content,
            mode=args.mode,
            history=history,
            base_url=args.base_url,
            timeout=args.timeout,
        )
        if args.pick:
            output = _pick_variant(mode, result, args.pick)
        elif args.as_json:
            output = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output = _format_plain(mode, result)
    except CliError as exc:
        print(f"slack-reply: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
