"""Codex 作为 harness：每一轮起一个 `codex exec --json` 进程，之后的轮次用 `codex exec resume <thread_id>` 接着聊。

和 sdk_session 一样实现 runner 的 AgentSession 协议，把 Codex 的 JSONL 事件映射成页面事件。Codex 没有
AskUserQuestion 这类提问工具：要用户确认时，它把内容写在回复里、结束这一轮，用户在输入框里回复即可。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shlex
import signal
import time
from pathlib import Path
from typing import Any, AsyncIterator

from .config import Config
from .runner import SessionSpec

logger = logging.getLogger(__name__)

TOOL_RESULT_LIMIT = 2000
SUMMARY_LIMIT = 200
INTERRUPT_GRACE_S = 5.0

PREFACE = """\
【运行环境说明，不用回复这一段】你运行在 momo 的 Agent 页里。用户只能在网页上看到你的文字回复、命令摘要和当前目录里的文件，看不到终端。
- 当前工作目录就是本次运行的目录，用户上传的文件在 input/ 下。所有产出都写在当前目录内，用户可以在网页上下载。
- 需要用户做选择或确认时，把要审阅的内容（术语表、稿件、字幕）和选项用 Markdown 完整写在回复里，然后结束这一轮，等用户在网页上回复。
- 这一轮结束时如果要等用户确认或回答才能继续，在回复最后单独一行写「【等待确认】」（页面据此提醒用户；用户一直不回时会自动按你推荐的方案继续）。任务全部做完时不要写。
- 命令直接在服务器上执行，没有沙箱。这台服务器还跑着线上服务：除非用户要求或 skill 的说明需要，不要改动当前目录以外的文件，不要装系统级软件或重启服务。
"""

_SHELL_WRAPPER = re.compile(r"^(?:/bin/)?(?:ba|z)?sh -lc (.+)$", re.S)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"…（共 {len(text)} 字，已截断）"


def _command_summary(command: str) -> str:
    """Codex 的命令都包在 `/bin/bash -lc '…'` 里，页面上只显示里面那句。"""
    match = _SHELL_WRAPPER.match(command.strip())
    if match:
        try:
            parts = shlex.split(match.group(1))
            command = parts[0] if len(parts) == 1 else match.group(1)
        except ValueError:
            command = match.group(1)
    return command[:SUMMARY_LIMIT]


def latest_model(codex_home: Path) -> str | None:
    """Codex 自己的模型清单里排在最前、可选的那个（用户要「用最新的模型」，不写死名字）。"""
    try:
        data = json.loads((codex_home / "models_cache.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    listed = [m for m in data.get("models", []) if isinstance(m, dict) and m.get("visibility") == "list" and m.get("slug")]
    listed.sort(key=lambda m: m.get("priority", 1_000_000))
    return listed[0]["slug"] if listed else None


class CodexMapper:
    """把 `codex exec --json` 的一行事件映射成页面事件（0 到多个）。"""

    def __init__(self) -> None:
        self.thread_id: str | None = None
        self.turn_done = False
        self._started_tools: set[str] = set()
        self._turn_started_at = time.monotonic()

    def _tool(self, item: dict[str, Any]) -> dict[str, Any] | None:
        kind = item.get("type")
        if kind == "command_execution":
            name, summary = "Bash", _command_summary(str(item.get("command") or ""))
        elif kind == "file_change":
            paths = [str(change.get("path") or "") for change in item.get("changes") or [] if isinstance(change, dict)]
            name, summary = "Edit", "、".join(p for p in paths if p)[:SUMMARY_LIMIT]
        elif kind == "web_search":
            name, summary = "WebSearch", str(item.get("query") or "")[:SUMMARY_LIMIT]
        elif kind == "mcp_tool_call":
            name, summary = f"{item.get('server')}.{item.get('tool')}", json.dumps(item.get("arguments") or {}, ensure_ascii=False)[:SUMMARY_LIMIT]
        else:
            return None
        return {"type": "tool", "id": str(item.get("id")), "name": name, "summary": summary, "parent": None}

    def map(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        kind = event.get("type")
        if kind == "thread.started":
            self.thread_id = event.get("thread_id") or self.thread_id
            return [{"type": "session", "session_id": self.thread_id}]
        if kind == "turn.started":
            self.turn_done = False
            self._turn_started_at = time.monotonic()
            return []
        if kind in ("item.started", "item.updated", "item.completed"):
            return self._map_item(kind, event.get("item") or {})
        if kind == "turn.completed":
            self.turn_done = True
            return [self.result(is_error=False)]
        if kind == "turn.failed":
            self.turn_done = True
            message = (event.get("error") or {}).get("message") or "未知错误"
            return [{"type": "notice", "level": "error", "text": f"Codex 这一轮失败：{message}"}, self.result(is_error=True, errors=[message])]
        if kind == "error":
            return [{"type": "notice", "level": "error", "text": f"Codex 出错：{event.get('message') or event}"}]
        return []

    def _map_item(self, phase: str, item: dict[str, Any]) -> list[dict[str, Any]]:
        kind, item_id = item.get("type"), str(item.get("id"))
        if kind == "agent_message":
            text = str(item.get("text") or "")
            return [{"type": "text", "text": text, "parent": None}] if phase == "item.completed" and text.strip() else []
        if kind == "todo_list":
            items = [{"content": str(todo.get("text") or ""), "status": "completed" if todo.get("completed") else "pending"}
                     for todo in item.get("items") or [] if isinstance(todo, dict)]
            return [{"type": "todos", "items": items}]
        if kind == "error":
            return [{"type": "notice", "level": "warn", "text": str(item.get("message") or "")}] if phase == "item.completed" else []
        tool = self._tool(item)
        if tool is None:
            return []  # reasoning 等不上页面
        events: list[dict[str, Any]] = []
        if item_id not in self._started_tools:
            self._started_tools.add(item_id)
            events.append(tool)
        if phase == "item.completed":
            ok = item.get("status") != "failed" and item.get("exit_code") in (None, 0)
            text = str(item.get("aggregated_output") or "") if kind == "command_execution" else ""
            if kind == "mcp_tool_call" and item.get("error"):
                text = str(item["error"])
            events.append({"type": "tool_result", "id": item_id, "ok": ok, "text": _clip(text, TOOL_RESULT_LIMIT), "parent": None})
        return events

    def result(self, *, is_error: bool, subtype: str | None = None, errors: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "result",
            "session_id": self.thread_id,
            "is_error": is_error,
            "subtype": subtype or ("error" if is_error else "success"),
            "duration_ms": int((time.monotonic() - self._turn_started_at) * 1000),
            "num_turns": 1,
            "errors": errors or [],
        }


def build_command(config: Config, thread_id: str | None) -> list[str]:
    command = shlex.split(config.codex_bin) + ["exec"]
    if thread_id:
        command += ["resume"]
    command += ["--json", "--skip-git-repo-check"]
    if config.sandbox:
        command += ["--sandbox", "workspace-write", "-c", 'approval_policy="never"']
    else:
        command += ["--dangerously-bypass-approvals-and-sandbox"]
    model = config.codex_model or latest_model(config.codex_home)
    if model:
        command += ["-m", model]
    if thread_id:
        command += [thread_id]
    return command + ["-"]  # 提示词从 stdin 读，读完就关，不会卡在「Reading additional input」


class CodexSession:
    def __init__(self, config: Config, spec: SessionSpec):
        self._config = config
        self._spec = spec
        self._mapper = CodexMapper()
        self._mapper.thread_id = spec.resume
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._inbox: asyncio.Queue[str] = asyncio.Queue()
        self._proc: asyncio.subprocess.Process | None = None
        self._closed = False
        self._first = spec.resume is None
        self._worker = asyncio.create_task(self._work())

    @classmethod
    async def open(cls, config: Config, spec: SessionSpec) -> "CodexSession":
        return cls(config, spec)

    async def send(self, text: str) -> None:
        if self._first:
            # 第一轮把运行环境说明和这类任务的补充说明放在前面；resume 的轮次 Codex 自己记得
            text = PREFACE + self._spec.prompt_note + "\n" + text
            self._first = False
        # 上一轮还在跑时排队，等它结束再接着跑（和 Claude 那边插话的效果一样）
        await self._inbox.put(text)

    async def _work(self) -> None:
        while not self._closed:
            prompt = await self._inbox.get()
            try:
                await self._turn(prompt)
            except Exception as exc:  # noqa: BLE001 - 这一轮的任何失败都要反映到页面上
                logger.exception("codex turn failed for run %s", self._spec.run_id)
                await self._queue.put({"type": "notice", "level": "error", "text": f"Codex 进程出错：{exc}"})
                await self._queue.put(self._mapper.result(is_error=True, errors=[str(exc)]))

    async def _turn(self, prompt: str) -> None:
        command = build_command(self._config, self._mapper.thread_id)
        logger.info("[codex %s] %s", self._spec.run_id, " ".join(command[:-1]))
        self._proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._spec.cwd),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,  # 一行 JSON 里可能带很长的命令输出
        )
        proc = self._proc
        assert proc.stdin and proc.stdout and proc.stderr
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()
        stderr_task = asyncio.create_task(proc.stderr.read())
        self._mapper.turn_done = False
        async for raw in proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                logger.info("[codex %s] %s", self._spec.run_id, line[:500])
                continue
            for mapped in self._mapper.map(event):
                await self._queue.put(mapped)
        code = await proc.wait()
        stderr = (await stderr_task).decode("utf-8", "replace").strip()
        if stderr:
            logger.info("[codex %s stderr] %s", self._spec.run_id, stderr[-2000:])
        self._proc = None
        if not self._mapper.turn_done:
            # 被中断、进程崩溃、登录失效……没有 turn.completed 也要给页面一个结果，否则一直显示运行中
            reason = "已中断" if code in (-signal.SIGINT, -signal.SIGTERM, 130) else f"Codex 退出码 {code}：{stderr[-300:] or '无输出'}"
            await self._queue.put(self._mapper.result(is_error=True, subtype="interrupted" if "中断" in reason else "error", errors=[reason]))

    async def interrupt(self) -> None:
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            proc.send_signal(signal.SIGINT)  # 让 Codex 自己收尾（会话照常落盘，之后还能 resume）
        except (ValueError, OSError):
            proc.terminate()  # Windows 上不能对子进程发 SIGINT
        try:
            await asyncio.wait_for(proc.wait(), INTERRUPT_GRACE_S)
        except asyncio.TimeoutError:
            proc.kill()

    async def close(self) -> None:
        self._closed = True
        await self.interrupt()
        self._worker.cancel()
        await self._queue.put(None)

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event


def make_codex_factory(config: Config):
    async def factory(spec: SessionSpec) -> CodexSession:
        return await CodexSession.open(config, spec)

    return factory
