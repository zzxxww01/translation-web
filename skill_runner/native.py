"""各 harness 的原生信息：/status 卡片（照各 CLI 交互界面里 /status 的字段排），以及 CLI 自己回答的斜杠指令（不花额度）。

- Claude Code：非交互模式没有 /status（`claude -p /status` 只回「isn't available in this environment」），
  所以按交互界面的字段自己拼：版本、会话、目录、`claude auth status` 的登录信息、模型，再加套餐用量。
  用量（5 小时 / 7 天）来自每一轮都会推送的 rate_limit_event，这里把最近一次的存进 <home>/claude-limits.json。
  /usage、/context 等原样发给 CLI 即可。
- Codex：exec 模式没有斜杠指令；用 `codex app-server` 的 account/read、account/rateLimits/read 实时查。
- Antigravity：/usage、/credits 等由 CLI 自己回答，但在 stream-json 对话进程里不能用，要单独跑一次 `agy -p=/usage`。

runner 只依赖 Natives 的三个方法；测试里不传 natives，就不起任何外部进程。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import signal
import shlex
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .runtime_paths import claude_cli_path

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 20.0
# agy 自己回答的斜杠指令（`agy -p=/help` 列出的、不需要交互界面的那些）
AGY_LOCAL_COMMANDS = {"/usage", "/quota", "/credits", "/help", "/skills", "/agents", "/changelog"}
_ISO_TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")
# Claude Code 交互界面 /status 用量页的叫法
WINDOW_NAMES = {"five_hour": "Current session", "seven_day": "Current week (all models)",
                "seven_day_opus": "Current week (Opus)", "seven_day_sonnet": "Current week (Sonnet)"}
LOGIN_METHODS = {"claude.ai": "Claude {plan} Account", "console": "Anthropic Console Account", "apiKey": "API Key"}


def _clock(ts: float | int | None) -> str:
    if not ts:
        return ""
    moment = time.localtime(float(ts))
    same_day = time.strftime("%Y%m%d", moment) == time.strftime("%Y%m%d")
    return time.strftime("%H:%M" if same_day else "%m-%d %H:%M", moment)


def _window_line(name: str, used_percent: float | None, resets_at: float | int | None) -> str:
    used = f"{used_percent:.0f}% used" if used_percent is not None else "usage unknown"
    reset = f" · resets {_clock(resets_at)}" if resets_at else ""
    return f"{name}: {used}{reset}"


def _window_name(minutes: int | None) -> str:
    """Codex 交互界面 /status 的叫法：5h limit / Weekly limit。"""
    if not minutes:
        return "Limit"
    if minutes == 10080:
        return "Weekly limit"
    return f"{minutes // 60}h limit" if minutes % 60 == 0 else f"{minutes}m limit"


def _session_lines(session: dict[str, Any]) -> list[str]:
    """这个对话自己的部分：会话 ID、目录、模型（runner 传进来）。"""
    return [
        f"Session ID: {session.get('session_id') or '(not started yet)'}",
        f"cwd: {session.get('cwd') or ''}",
        f"Model: {session.get('model') or 'default'}",
    ]


async def _run(command: list[str], cwd: Path | None = None, timeout: float = PROBE_TIMEOUT_S) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *command, cwd=str(cwd) if cwd else None,
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


class Natives:
    def __init__(self, config: Config):
        self.config = config
        self.limits_file = config.home / "claude-limits.json"
        self._versions: dict[str, str] = {}

    # ---- Claude：记下每一轮推送的套餐用量 ----

    def observe(self, harness: str, event: dict[str, Any]) -> None:
        """runner 收到 harness 的内部事件（页面上不显示）时调用。"""
        if harness == "claude" and event.get("type") == "limits":
            windows = event.get("windows") or {}
            if not windows:
                return
            payload = {"windows": windows, "seen_at": time.time()}
            try:
                self.limits_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.limits_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                tmp.replace(self.limits_file)
            except OSError:
                logger.exception("could not save claude limits")

    def _claude_limit_lines(self) -> list[str]:
        try:
            data = json.loads(self.limits_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ["Usage: no data yet (appears after the first turn)"]
        lines = []
        for key, window in (data.get("windows") or {}).items():
            if not isinstance(window, dict):
                continue
            utilization = window.get("utilization")
            percent = utilization * 100 if isinstance(utilization, (int, float)) else None
            lines.append(_window_line(WINDOW_NAMES.get(key, key), percent, window.get("resetsAt")))
        if data.get("seen_at"):
            lines.append(f"(usage as of the last turn at {_clock(data['seen_at'])})")
        return lines or ["Usage: no data yet (appears after the first turn)"]

    async def _version(self, harness: str, command: list[str]) -> str:
        if harness not in self._versions:
            try:
                _, out, _ = await _run(command + ["--version"], timeout=10)
                self._versions[harness] = out.strip().splitlines()[0] if out.strip() else ""
            except (OSError, asyncio.TimeoutError, IndexError):
                self._versions[harness] = ""
        return self._versions[harness]

    # ---- /status ----

    async def status_lines(self, harness: str, session: dict[str, Any] | None = None) -> list[str]:
        """/status 卡片：照这个 harness 交互界面里 /status 的字段排。session 是这个对话的
        session_id / cwd / model。读不到就写原因，不抛错。"""
        session = session or {}
        try:
            if harness == "codex":
                return await self._codex_status(session)
            if harness == "antigravity":
                return await self._agy_status(session)
            return await self._claude_status(session)
        except Exception as exc:  # noqa: BLE001 — 读不到也要回一张卡
            logger.exception("native status failed for %s", harness)
            return [f"原生信息读不到：{exc}"]

    async def _claude_status(self, session: dict[str, Any]) -> list[str]:
        cli = claude_cli_path(self.config) or "claude"
        version = await self._version("claude", [cli])
        lines = [f"Version: {version.replace(' (Claude Code)', '')}".rstrip(), *_session_lines(session)[:2]]
        lines += await self._claude_account_lines(cli)
        lines.append(_session_lines(session)[2])
        return [*lines, *self._claude_limit_lines()]

    async def _claude_account_lines(self, cli: str) -> list[str]:
        """`claude auth status`（只读、不花额度）：登录方式、组织、邮箱。"""
        try:
            _, out, _ = await _run([cli, "auth", "status"], timeout=10)
            auth = json.loads(out)
        except (OSError, asyncio.TimeoutError, ValueError):
            return ["Login method: (unknown)"]
        if not auth.get("loggedIn"):
            return ["Login method: not logged in"]
        plan = str(auth.get("subscriptionType") or "").capitalize()
        method = LOGIN_METHODS.get(auth.get("authMethod"), str(auth.get("authMethod") or ""))
        lines = [f"Login method: {method.format(plan=plan).replace('  ', ' ')}"]
        if auth.get("orgName"):
            lines.append(f"Organization: {auth['orgName']}")
        if auth.get("email"):
            lines.append(f"Email: {auth['email']}")
        return lines

    async def _codex_status(self, session: dict[str, Any]) -> list[str]:
        result = await asyncio.wait_for(self._codex_query(), PROBE_TIMEOUT_S)
        lines = [f"Version: {result.get('version') or ''}".rstrip(), _session_lines(session)[2],
                 f"Directory: {session.get('cwd') or ''}"]
        account = result.get("account") or {}
        if account:
            who = account.get("email") or {"chatgpt": "ChatGPT", "apiKey": "API key"}.get(account.get("type"), account.get("type") or "")
            plan = account.get("planType")
            lines.append(f"Account: {who}{f' (Plan: {str(plan).capitalize()})' if plan else ''}")
        lines += [f"Session: {session.get('session_id') or '(not started yet)'}"]
        limits = result.get("rateLimits") or {}
        for key in ("primary", "secondary"):
            window = limits.get(key)
            if isinstance(window, dict):
                lines.append(_window_line(_window_name(window.get("windowDurationMins")), window.get("usedPercent"), window.get("resetsAt")))
        credits = limits.get("credits") or {}
        if credits.get("unlimited"):
            lines.append("Credits: unlimited")
        elif credits.get("balance") is not None:
            try:
                lines.append(f"Credits: {float(credits['balance']):.2f}")
            except (TypeError, ValueError):
                lines.append(f"Credits: {credits['balance']}")
        return lines

    async def _codex_query(self) -> dict[str, Any]:
        """起一个 `codex app-server`，问账号和额度，然后关掉（只读，不花额度）。"""
        command = shlex.split(self.config.codex_bin) + ["app-server"]
        proc = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            limit=4 * 1024 * 1024, start_new_session=True)
        assert proc.stdin is not None and proc.stdout is not None

        async def call(rid: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}) + "\n").encode())
            await proc.stdin.drain()
            while True:
                line = await proc.stdout.readline()
                if not line:
                    raise RuntimeError("codex app-server 提前退出")
                message = json.loads(line)
                if message.get("id") == rid:
                    if "error" in message:
                        raise RuntimeError(str(message["error"].get("message") or message["error"]))
                    return message.get("result") or {}

        try:
            init = await call(1, "initialize", {"clientInfo": {"name": "skill-runner", "version": "1"}})
            proc.stdin.write((json.dumps({"jsonrpc": "2.0", "method": "initialized"}) + "\n").encode())
            account = (await call(2, "account/read")).get("account") or {}
            limits = (await call(3, "account/rateLimits/read")).get("rateLimits") or {}
        finally:
            # codex 是一层启动脚本，真正的进程是它的子进程（还占着输出管道）：整个进程组一起结束
            if proc.returncode is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            await proc.wait()
        agent = str(init.get("userAgent") or "")
        version = agent.split("/", 1)[1].split(" ", 1)[0] if "/" in agent else ""
        return {"version": version, "account": account, "rateLimits": limits}

    async def _agy_status(self, session: dict[str, Any]) -> list[str]:
        version = await self._version("antigravity", [str(Path(self.config.antigravity_bin).expanduser())])
        usage = await self.agy_local(None, "/usage")
        return [f"Version: {version}".rstrip(), *_session_lines(session), *(usage or [])]

    # ---- harness 自己回答的斜杠指令 ----

    def is_local(self, harness: str, message: str) -> bool:
        """这条消息是不是要单独跑的本地指令（目前只有 agy 需要；Claude 的直接发给对话进程）。"""
        command = message.strip().split(maxsplit=1)[0].lower() if message.strip() else ""
        return harness == "antigravity" and command in AGY_LOCAL_COMMANDS

    async def agy_local(self, cwd: Path | None, message: str) -> list[str]:
        """`agy -p=/usage` 这类：CLI 自己回答，不进对话、不花额度。返回要显示的几行。"""
        command = [str(Path(self.config.antigravity_bin).expanduser()), "--output-format", "json", f"-p={message.strip()}"]
        code, out, err = await _run(command, cwd=cwd)
        try:
            data = json.loads(out)
        except ValueError:
            return [line for line in (err or out).strip().splitlines() if line.strip()] or [f"agy 退出码 {code}"]
        text = str(data.get("response") or data.get("error") or "")
        return [_ISO_TIME.sub(_local_reset, " ".join(part for part in line.split("\t") if part))
                for line in text.splitlines() if line.strip()]


def _local_reset(match: re.Match[str]) -> str:
    """agy 给的 UTC 时间换成本机时间：「11-29 18:51 重置」。"""
    try:
        moment = datetime.fromisoformat(match.group(0).replace("Z", "+00:00"))
    except ValueError:
        return match.group(0)
    return f"{_clock(moment.timestamp())} 重置"
