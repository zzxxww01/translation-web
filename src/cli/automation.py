#!/usr/bin/env python3
"""translation-agent：给 Muse（Felix 的个人助手）经 SSH 调用的无状态 CLI。

所有子命令只往 stdout 写一个 JSON 对象，日志写 stderr；成功退出码 0，失败非 0 且 JSON 带 error。
逻辑都在本机后端的 /internal/automation/* 里（src/api/routers/automation.py），这里只做参数校验、
HTTP 调用和输出整理；本进程不读任何凭证。只用标准库，启动快。

--ssh：给 authorized_keys 里 command= 强制命令用。从 SSH_ORIGINAL_COMMAND 读子命令，只放行 COMMANDS 里的。
translate-post / slack-reply 的正文可以放参数里，也可以不给、从标准输入传（SSH 时 stdin 照样能用，长文本更省事）。
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
_DRAFT_ID_RE = re.compile(r"^(m_[0-9a-f]{12}|s_[A-Z0-9]{8,12}_[0-9]{9,11}_[0-9]{1,6})$")


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


def _dump(result: Any) -> str:
    """序列化并脱敏；配图的 base64 不过脱敏（随机字节偶尔会长得像密钥，被改掉图就坏了）。"""
    blobs: List[str] = []

    def stash(node: Any) -> Any:
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if key == "data_base64" and isinstance(value, str):
                    blobs.append(value)
                    value = f"@@IMAGE_DATA_{len(blobs) - 1}@@"
                out[key] = stash(value)
            return out
        if isinstance(node, list):
            return [stash(v) for v in node]
        return node

    text = redact(json.dumps(stash(result), ensure_ascii=False))
    return re.sub(r"@@IMAGE_DATA_(\d+)@@", lambda m: blobs[int(m.group(1))] if int(m.group(1)) < len(blobs) else m.group(0), text) if blobs else text


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
        # 参数校验失败（422）时具体原因在 errors 里，只给 detail 就只剩一句 Request validation failed
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if isinstance(errors, list) and errors:
            reasons = [f"{str(e.get('field', '')).removeprefix('body.')}: {e.get('message', '')}".strip(": ")
                       for e in errors if isinstance(e, dict)]
            detail += "：" + "；".join(r for r in reasons if r)
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
    body = {"article": article, "target_lang": args.target_lang, "engines": list(dict.fromkeys(args.engine or ["web"]))}
    return _call(args.base_url, "POST", "/translate-article", body=body, timeout=args.timeout or 240)


def cmd_status(args: argparse.Namespace) -> Dict[str, Any]:
    if not _PROJECT_ID_RE.match(args.project_id):
        raise CliError("project_id 格式不对")
    params: Dict[str, Any] = {"with_markdown": "true"} if args.with_markdown else {}
    if args.engine:
        params["engine"] = args.engine
    return _call(args.base_url, "GET", f"/projects/{quote(args.project_id, safe='')}/status",
                 params=params or None, timeout=args.timeout or 60)


def cmd_articles(args: argparse.Namespace) -> Dict[str, Any]:
    return _call(args.base_url, "GET", "/articles", params={"status": args.status, "limit": args.limit},
                 timeout=args.timeout or 60)


def cmd_mark_sent(args: argparse.Namespace) -> Dict[str, Any]:
    # draft_id（m_… / s_…）是翻译稿，其余按文章 project_id
    if _DRAFT_ID_RE.match(args.id):
        path = f"/drafts/{args.id}/sent"
    elif _PROJECT_ID_RE.match(args.id):
        path = f"/projects/{quote(args.id, safe='')}/sent"
    else:
        raise CliError("要给文章的 project_id 或翻译稿的 draft_id")
    return _call(args.base_url, "POST", path, body={"sent": not args.undo}, timeout=args.timeout or 60)


def cmd_health(args: argparse.Namespace) -> Dict[str, Any]:
    return _call(args.base_url, "GET", "/health", timeout=args.timeout or 60)


def cmd_translate_slack(args: argparse.Namespace) -> Dict[str, Any]:
    if not _CONVERSATION_RE.match(args.conversation_id) or not _TS_RE.match(args.message_ts):
        raise CliError("conversation_id 或 message_ts 格式不对")
    if args.thread_ts and not _TS_RE.match(args.thread_ts):
        raise CliError("--thread-ts 格式不对")
    body = {"conversation_id": args.conversation_id, "message_ts": args.message_ts,
            "thread_ts": args.thread_ts, "with_thread": args.with_thread}
    return _call(args.base_url, "POST", "/translate-slack", body=body, timeout=args.timeout or 240)


def cmd_slack_todos(args: argparse.Namespace) -> Dict[str, Any]:
    return _call(args.base_url, "GET", "/slack-todos", timeout=args.timeout or 180)


def cmd_dms(args: argparse.Namespace) -> Dict[str, Any]:
    return _call(args.base_url, "GET", "/dms", timeout=args.timeout or 360)


def cmd_drafts(args: argparse.Namespace) -> Dict[str, Any]:
    params: Dict[str, Any] = {"status": args.status, "limit": args.limit}
    if args.sent:
        params["sent"] = args.sent
    if args.source:
        params["source"] = args.source
    if args.q:
        params["q"] = args.q
    return _call(args.base_url, "GET", "/drafts", params=params, timeout=args.timeout or 60)


def cmd_draft(args: argparse.Namespace) -> Dict[str, Any]:
    if not _DRAFT_ID_RE.match(args.draft_id):
        raise CliError("draft_id 格式不对（drafts 返回的 draft_id，如 s_C0123ABCD_1794610284_466519）")
    params = {"images": "false"} if args.no_images else None
    return _call(args.base_url, "GET", f"/drafts/{quote(args.draft_id, safe='')}", params=params,
                 timeout=args.timeout or 180)


OPTIMIZE_OPTIONS = ["coherence", "readable", "idiomatic", "professional",  # 网页的 4 个快捷项
                    "shorten", "expand", "formal", "story", "qa", "social"]  # 网页「更多…」


def cmd_optimize_draft(args: argparse.Namespace) -> Dict[str, Any]:
    if not _DRAFT_ID_RE.match(args.draft_id):
        raise CliError("draft_id 格式不对")
    if bool(args.option) == bool(args.instruction and args.instruction.strip()):
        raise CliError("--option 和 --instruction 二选一")
    body = {"option": args.option, "instruction": args.instruction}
    return _call(args.base_url, "POST", f"/drafts/{quote(args.draft_id, safe='')}/optimize", body=body,
                 timeout=args.timeout or 240)


def cmd_translate_slack_post(args: argparse.Namespace) -> Dict[str, Any]:
    if not _CONVERSATION_RE.match(args.conversation_id) or not _TS_RE.match(args.thread_ts):
        raise CliError("conversation_id 或 thread_ts 格式不对")
    body = {"conversation_id": args.conversation_id, "thread_ts": args.thread_ts,
            "instruction": args.instruction, "with_images": not args.no_images}
    return _call(args.base_url, "POST", "/translate-slack-post", body=body, timeout=args.timeout or 360)


ENGINES = ["web", "claude", "codex", "antigravity"]
MAX_POST_CHARS, MAX_REPLY_CHARS, MAX_HISTORY = 10_000, 50_000, 100


def _read_text(value: Optional[str], limit: int) -> str:
    """正文：参数里给了就用；没给或给 - 就读标准输入。"""
    if value is None or value == "-":
        if sys.stdin is None or sys.stdin.isatty():
            raise CliError("缺少正文：放在参数里，或从标准输入传")
        try:
            value = sys.stdin.buffer.read().decode("utf-8")
        except UnicodeDecodeError as exc:  # 不替换成 �：带乱码去翻既花钱又没用
            raise CliError("标准输入不是 UTF-8 文本") from exc
    if not value.strip():
        raise CliError("正文是空的")
    if len(value) > limit:
        raise CliError(f"正文太长：{len(value)} 字符，上限 {limit}")
    return value


def cmd_translate_post(args: argparse.Namespace) -> Dict[str, Any]:
    body = {"content": _read_text(args.text, MAX_POST_CHARS), "hashtags": args.hashtags}
    return _call(args.base_url, "POST", "/translate-post", body=body, timeout=args.timeout or 240)


def cmd_slack_reply(args: argparse.Namespace) -> Dict[str, Any]:
    history: Any = []
    if args.history:
        try:
            history = json.loads(args.history)
        except ValueError as exc:
            raise CliError("--history 不是合法 JSON") from exc
        if not isinstance(history, list):
            raise CliError('--history 要是 [{"role":"them|me","content":"..."}] 这样的数组')
        if len(history) > MAX_HISTORY:
            raise CliError(f"--history 最多 {MAX_HISTORY} 条")
        for index, message in enumerate(history, start=1):
            role = message.get("role") if isinstance(message, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(role, str) or role not in ("me", "them"):
                raise CliError(f"--history 第 {index} 条的 role 要是 me 或 them")
            if not isinstance(content, str) or not content.strip():
                raise CliError(f"--history 第 {index} 条的 content 不能为空")
            if len(content) > MAX_REPLY_CHARS:
                raise CliError(f"--history 第 {index} 条太长，上限 {MAX_REPLY_CHARS} 字符")
    body = {"text": _read_text(args.text, MAX_REPLY_CHARS), "mode": args.mode, "history": history}
    return _call(args.base_url, "POST", "/slack-reply", body=body, timeout=args.timeout or 240)


COMMANDS = {
    "updates": cmd_updates,
    "translate-article": cmd_translate_article,
    "status": cmd_status,
    "articles": cmd_articles,
    "mark-sent": cmd_mark_sent,
    "health": cmd_health,
    "translate-slack": cmd_translate_slack,
    "slack-todos": cmd_slack_todos,
    "dms": cmd_dms,
    "drafts": cmd_drafts,
    "draft": cmd_draft,
    "translate-slack-post": cmd_translate_slack_post,
    "optimize-draft": cmd_optimize_draft,
    "translate-post": cmd_translate_post,
    "slack-reply": cmd_slack_reply,
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

    p = sub.add_parser("translate-article", help="翻译一篇文章，可选网页版 / Claude / Codex / agy，可多选（会花钱，须经 Felix 确认）")
    p.add_argument("article", help="文章 slug 或 Substack 链接")
    p.add_argument("--target-lang", default="zh")
    p.add_argument("--engine", action="append", choices=ENGINES,
                   help="用什么翻，可写多次同时翻：web 网页版（默认）/ claude / codex / antigravity（agy）")

    p = sub.add_parser("status", help="查翻译任务状态与结果")
    p.add_argument("project_id")
    p.add_argument("--with-markdown", action="store_true", help="完成时把中文 Markdown 全文放进 JSON")
    p.add_argument("--engine", choices=ENGINES, help="配合 --with-markdown：要哪一版的全文（默认网页上显示的那版）")

    p = sub.add_parser("articles", help="导入过的文章：unsent 译完还没发（默认）/ sent 已发送（只读）")
    p.add_argument("--status", choices=["unsent", "sent"], default="unsent")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("mark-sent", help="把文章或翻译稿标记为已发送（和网页上的按钮一样）；--undo 撤销")
    p.add_argument("id", help="文章的 project_id 或翻译稿的 draft_id")
    p.add_argument("--undo", action="store_true", help="撤销已发送")

    sub.add_parser("health", help="自检")

    p = sub.add_parser("translate-slack", help="翻译一条 Slack 消息 / 整个 thread（会花模型费，须经 Felix 确认）")
    p.add_argument("conversation_id")
    p.add_argument("message_ts")
    p.add_argument("--thread-ts", help="消息是 thread 里的回复时带上（updates 返回的 thread_ts）")
    p.add_argument("--with-thread", action="store_true", help="翻译这条消息所在的整个 thread")

    sub.add_parser("slack-todos", help="我的待办：找我的私信和 @我（和网页一致；会调一次轻量模型，Slack 只读）")

    sub.add_parser("dms", help="还没回的私信：英文原话、找我干什么、中文理解、3 版英文回复（新消息才调模型，同样的不重复花钱）")

    p = sub.add_parser("drafts", help="翻译记录列表，默认只列还没点「标记完成」的")
    p.add_argument("--status", choices=["draft", "done", "all"], default="draft")
    p.add_argument("--source", choices=["slack", "manual"], help="只看 Slack 帖子 / 帖子翻译页手动翻的")
    p.add_argument("--q", help="在标题、原文、译文里搜")
    p.add_argument("--sent", choices=["yes", "no"], help="只看已发送 / 还没发送的（和 --status 无关）")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("draft", help="一份翻译稿：原文、当前译文、标题和原始配图（base64）")
    p.add_argument("draft_id")
    p.add_argument("--no-images", action="store_true", help="配图只给文件名和大小，不带图片数据")

    p = sub.add_parser("translate-slack-post",
                       help="把一个 thread 当帖子翻：提取原文和配图 → 翻译 → 标题（会花模型费，须经 Felix 确认）")
    p.add_argument("conversation_id")
    p.add_argument("thread_ts")
    p.add_argument("--instruction", help="AI 挑错了时说明要翻哪条，如「翻第二版文案」")
    p.add_argument("--no-images", action="store_true", help="配图不带图片数据")

    p = sub.add_parser("optimize-draft", help="翻译稿快捷优化，存成新版本（和网页帖子翻译的优化按钮一样；会花模型费）")
    p.add_argument("draft_id")
    p.add_argument("--option", choices=OPTIMIZE_OPTIONS,
                   help="coherence 更连贯 / readable 可读性 / idiomatic 地道 / professional 专业 / shorten 精简 / "
                        "expand 展开说明 / formal 正式公文 / story 故事化 / qa 问答格式 / social 社交媒体")
    p.add_argument("--instruction", help="自定义要求，如「第二段别用赋能」（和 --option 二选一）")

    p = sub.add_parser("translate-post", help="翻译一段帖子原文（网页「帖子翻译」同一条链路；会花模型费，须经 Felix 确认）")
    p.add_argument("text", nargs="?", help="原文；不给就从标准输入读")
    p.add_argument("--hashtags", action="store_true", help="译文末尾加小红书话题标签（默认不加）")

    p = sub.add_parser("slack-reply",
                       help="Slack 回复：对方的英文消息 → 中文理解 + 3 版英文回复；中文草稿 → 3 版英文（会花模型费）")
    p.add_argument("text", nargs="?", help="对方的消息或自己的中文草稿；不给就从标准输入读")
    p.add_argument("--mode", choices=["auto", "incoming", "compose"], default="auto",
                   help="incoming=分析对方消息，compose=中文草稿写成英文；默认按中文占比自动判断")
    p.add_argument("--history", help='之前的对话，JSON 数组：[{"role":"them|me","content":"..."}]')
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
    sys.stdout.buffer.write((_dump(result) + "\n").encode("utf-8"))
    sys.stdout.flush()
    return exit_code


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
