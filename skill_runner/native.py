"""各 harness 的原生信息：/status 里的版本、账号、套餐用量，以及 CLI 自己回答的斜杠指令（不花额度）。

- Claude Code：非交互模式没有 /status；套餐用量（5 小时 / 7 天）来自每一轮都会推送的 rate_limit_event，
  这里把最近一次的存进 <home>/claude-limits.json，/status 时读出来。/usage、/context 等原样发给 CLI 即可。
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
WINDOW_NAMES = {"five_hour": "5 小时", "seven_day": "7 天", "seven_day_opus": "7 天（Opus）", "seven_day_sonnet": "7 天（Sonnet）"}


def _clock(ts: float | int | None) -> str:
    if not ts:
        return ""
    moment = time.localtime(float(ts))
    same_day = time.strftime("%Y%m%d", moment) == time.strftime("%Y%m%d")
    return time.strftime("%H:%M" if same_day else "%m-%d %H:%M", moment)


def _window_line(name: str, used_percent: float | None, resets_at: float | int | None) -> str:
    used = f"已用 {used_percent:.0f}%" if used_percent is not None else "用量未知"
    reset = f"，{_clock(resets_at)} 重置" if resets_at else ""
    return f"{name}额度：{used}{reset}"


def _window_name(minutes: int | None) -> str:
    if not minutes:
        return "额度窗口"
    if minutes == 300:
        return "5 小时"
    if minutes == 10080:
        return "每周"
    return f"{minutes // 60} 小时" if minutes % 60 == 0 else f"{minutes} 分钟"


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
            return ["套餐用量：还没有数据（跑完一轮对话后才有）"]
        lines = []
        for key, window in (data.get("windows") or {}).items():
            if not isinstance(window, dict):
                continue
            utilization = window.get("utilization")
            percent = utilization * 100 if isinstance(utilization, (int, float)) else None
            lines.append(_window_line(WINDOW_NAMES.get(key, key), percent, window.get("resetsAt")))
        if data.get("seen_at"):
            lines.append(f"（用量取自 {_clock(data['seen_at'])} 最近一轮对话）")
        return lines or ["套餐用量：还没有数据（跑完一轮对话后才有）"]

    async def _version(self, harness: str, command: list[str]) -> str:
        if harness not in self._versions:
            try:
                _, out, _ = await _run(command + ["--version"], timeout=10)
                self._versions[harness] = out.strip().splitlines()[0] if out.strip() else ""
            except (OSError, asyncio.TimeoutError, IndexError):
                self._versions[harness] = ""
        return self._versions[harness]

    # ---- /status ----

    async def status_lines(self, harness: str) -> list[str]:
        """/status 卡片上半部分：这个 harness 的版本、账号和套餐用量。读不到就写原因，不抛错。"""
        try:
            if harness == "codex":
                return await self._codex_status()
            if harness == "antigravity":
                return await self._agy_status()
            return await self._claude_status()
        except Exception as exc:  # noqa: BLE001 — 状态卡读不到原生信息也要能显示页面部分
            logger.exception("native status failed for %s", harness)
            return [f"原生信息读不到：{exc}"]

    async def _claude_status(self) -> list[str]:
        cli = claude_cli_path(self.config) or "claude"
        version = await self._version("claude", [cli])
        return [f"Claude Code {version.replace(' (Claude Code)', '')}".strip(), *self._claude_limit_lines()]

    async def _codex_status(self) -> list[str]:
        result = await asyncio.wait_for(self._codex_query(), PROBE_TIMEOUT_S)
        lines = [f"Codex {result.get('version') or ''}".strip()]
        account = result.get("account") or {}
        if account:
            kind = {"chatgpt": "ChatGPT 账号", "apiKey": "API key"}.get(account.get("type"), account.get("type") or "")
            plan = account.get("planType")
            email = f" {account['email']}" if account.get("email") else ""
            lines.append(f"登录：{kind}{email}{f'（{plan}）' if plan else ''}")
        limits = result.get("rateLimits") or {}
        for key in ("primary", "secondary"):
            window = limits.get(key)
            if isinstance(window, dict):
                lines.append(_window_line(_window_name(window.get("windowDurationMins")), window.get("usedPercent"), window.get("resetsAt")))
        credits = limits.get("credits") or {}
        if credits.get("unlimited"):
            lines.append("credits：不限")
        elif credits.get("balance") is not None:
            try:
                lines.append(f"credits 余额：{float(credits['balance']):.2f}")
            except (TypeError, ValueError):
                lines.append(f"credits 余额：{credits['balance']}")
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

    async def _agy_status(self) -> list[str]:
        version = await self._version("antigravity", [str(Path(self.config.antigravity_bin).expanduser())])
        usage = await self.agy_local(None, "/usage")
        return [f"Antigravity {version}".strip(), *(usage or [])]

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
