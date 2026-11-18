#!/usr/bin/env python3
"""translation-agent：给 Muse（Felix 的个人助手）经 SSH 调用的无状态 CLI。

所有子命令只往 stdout 写一个 JSON 对象，日志写 stderr；成功退出码 0，失败非 0 且 JSON 带 error。
逻辑都在本机后端的 /internal/automation/* 里（src/api/routers/automation.py），这里只做参数校验、
HTTP 调用和输出整理；本进程不读任何凭证。只用标准库，启动快。

--ssh：给 authorized_keys 里 command= 强制命令用。从 SSH_ORIGINAL_COMMAND 读子命令，只放行下面这几个。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request

from ._http import urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:54321"
PREFIX = "/internal/automation"

EXIT_OK, EXIT_USAGE, EXIT_UNREACHABLE, EXIT_SERVICE = 0, 1, 2, 3

# 兜底脱敏：正常输出里不会有这些，万一上游报错信息里带了也不往外漏
_SECRET_PATTERNS = [
    re.compile(r"xox[a-z]-[A-Za-z0-9-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(substack\.sid|substack\.lli|connect\.sid)=[^;\s\"]+", re.I),
    re.compile(r"(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
    re.compile(r"(api[_-]?key|token|cookie|secret|password)(\"?\s*[:=]\s*\"?)[^\s\",;]{6,}", re.I),
]
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_ARTICLE_URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+/[^\s]{1,1900}$")
_PROJECT_ID_RE = re.compile(r"^[^/\\\s.][^/\\\s]{0,199}$")
_CONVERSATION_RE = re.compile(r"^[CDG][A-Z0-9]{6,20}$")
_TS_RE = re.compile(r"^\d{9,11}\.\d{1,6}$")


class CliError(Exception):
    def __init__(self, message: str, code: str = "BAD_ARGUMENT", exit_code: int = EXIT_USAGE):
        super().__init__(message)
        self.message, self.code, self.exit_code = message, code, exit_code


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # argparse 默认往 stderr 打用法并 exit(2)；这里统一成 JSON
        raise CliError(message)


def redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) + m.group(2) + "[redacted]") if pattern.groups >= 2
                           else "[redacted]", text)
    return text


def parse_since(value: str) -> float:
    """ISO 时间（无时区按 UTC）或 Unix 时间戳（秒或毫秒）→ Unix 秒。"""
    value = (value or "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", value):
        ts = float(value)
        return ts / 1000 if ts > 1e12 else ts
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CliError(f"--since 不是 ISO 时间或 Unix 时间戳：{value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _log(message: str) -> None:
    sys.stderr.buffer.write((redact(message) + "\n").encode("utf-8"))
    sys.stderr.flush()


def _call(base_url: str, method: str, path: str, *, params: Optional[Dict[str, Any]] = None,
          body: Optional[Dict[str, Any]] = None, timeout: float = 120) -> Dict[str, Any]:
    url = base_url.rstrip("/") + PREFIX + path
    if params:
        url += "?" + urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    _log(f"{method} {PREFIX}{path}")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (ValueError, OSError):
            payload = {}
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False) if detail else f"HTTP {error.code}"
        code = (payload.get("error_code") if isinstance(payload, dict) else None) or f"HTTP_{error.code}"
        raise CliError(detail, code=code, exit_code=EXIT_SERVICE) from error
    except (URLError, TimeoutError, ConnectionError) as error:
        reason = getattr(error, "reason", error)
        raise CliError(f"连不上翻译服务：{reason}", code="SERVICE_UNREACHABLE", exit_code=EXIT_UNREACHABLE) from error
    except ValueError as error:
        raise CliError("翻译服务返回的不是 JSON", code="BAD_RESPONSE", exit_code=EXIT_SERVICE) from error


# ---------------------------------------------------------------- 子命令


def cmd_updates(args: argparse.Namespace) -> Dict[str, Any]:
    since = parse_since(args.since)
    return _call(args.base_url, "GET", "/updates", params={"since": f"{since:.6f}"}, timeout=args.timeout or 180)


def cmd_translate_article(args: argparse.Namespace) -> Dict[str, Any]:
    article = args.article.strip()
    if not (_SLUG_RE.match(article) or _ARTICLE_URL_RE.match(article)):
        raise CliError("文章要给 slug（如 nvidia-gb300）或 https 开头的 Substack 链接")
    return _call(args.base_url, "POST", "/translate-article",
                 body={"article": article, "target_lang": args.target_lang}, timeout=args.timeout or 240)


def cmd_status(args: argparse.Namespace) -> Dict[str, Any]:
    if not _PROJECT_ID_RE.match(args.project_id):
        raise CliError("project_id 格式不对")
    params = {"with_markdown": "true"} if args.with_markdown else None
    return _call(args.base_url, "GET", f"/projects/{quote(args.project_id, safe='')}/status",
                 params=params, timeout=args.timeout or 60)


def cmd_health(args: argparse.Namespace) -> Dict[str, Any]:
    return _call(args.base_url, "GET", "/health", timeout=args.timeout or 60)


def cmd_translate_slack(args: argparse.Namespace) -> Dict[str, Any]:
    if not _CONVERSATION_RE.match(args.conversation_id) or not _TS_RE.match(args.message_ts):
        raise CliError("conversation_id 或 message_ts 格式不对")
    raise CliError("translate-slack 是二期功能，还没有上线", code="NOT_IMPLEMENTED", exit_code=EXIT_SERVICE)


COMMANDS = {
    "updates": cmd_updates,
    "translate-article": cmd_translate_article,
    "status": cmd_status,
    "health": cmd_health,
    "translate-slack": cmd_translate_slack,
}


def build_parser() -> _Parser:
    parser = _Parser(prog="translation-agent", description="Muse 调用翻译服务的 CLI（stdout 只输出一个 JSON）")
    parser.add_argument("--base-url", default=os.getenv("TRANSLATION_SERVICE_URL", DEFAULT_BASE_URL),
                        help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=float, default=None, help="HTTP 超时秒数")
    parser.add_argument("--ssh", action="store_true", help="从 SSH_ORIGINAL_COMMAND 读子命令（authorized_keys 强制命令用）")
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)

    p = sub.add_parser("updates", help="查 since 之后的新文章和 @我（只读）")
    p.add_argument("--since", required=True, help="ISO 时间或 Unix 时间戳；用上次返回的 watermark")

    p = sub.add_parser("translate-article", help="翻译一篇文章（会花模型费，须经 Felix 确认）")
    p.add_argument("article", help="文章 slug 或 Substack 链接")
    p.add_argument("--target-lang", default="zh")

    p = sub.add_parser("status", help="查翻译任务状态与结果")
    p.add_argument("project_id")
    p.add_argument("--with-markdown", action="store_true", help="完成时把中文 Markdown 全文放进 JSON")

    sub.add_parser("health", help="自检")

    p = sub.add_parser("translate-slack", help="翻译一条 Slack 消息 / 线程（二期）")
    p.add_argument("conversation_id")
    p.add_argument("message_ts")
    p.add_argument("--with-thread", action="store_true")
    return parser


def _ssh_argv() -> List[str]:
    """把 SSH_ORIGINAL_COMMAND 转成参数；允许带或不带开头的 translation-agent。"""
    original = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    try:
        argv = shlex.split(original)
    except ValueError as exc:
        raise CliError("命令解析失败") from exc
    if argv and os.path.basename(argv[0]) in {"translation-agent", "translation-agent-cli"}:
        argv = argv[1:]
    if not argv or argv[0] not in COMMANDS:
        raise CliError(f"只允许这些子命令：{', '.join(COMMANDS)}", code="FORBIDDEN")
    if any(a.startswith("--base-url") or a == "--ssh" for a in argv):
        raise CliError("SSH 模式不允许改服务地址", code="FORBIDDEN")
    return argv


def run(argv: Sequence[str]) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.ssh:
            ssh_args = parser.parse_args(_ssh_argv())
            ssh_args.base_url = DEFAULT_BASE_URL
            args = ssh_args
        if not args.command:
            raise CliError(f"缺少子命令：{', '.join(COMMANDS)}")
        result, exit_code = COMMANDS[args.command](args), EXIT_OK
    except CliError as error:
        result, exit_code = {"error": error.message, "code": error.code}, error.exit_code
    except Exception as error:  # 兜底：stdout 也必须是 JSON
        result, exit_code = {"error": f"内部错误：{type(error).__name__}", "code": "INTERNAL"}, EXIT_SERVICE
    # 直接写 UTF-8 字节：SSH 非交互会话的 locale 可能不是 UTF-8
    sys.stdout.buffer.write((redact(json.dumps(result, ensure_ascii=False)) + "\n").encode("utf-8"))
    sys.stdout.flush()
    return exit_code


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
