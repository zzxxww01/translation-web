"""Official Google Antigravity CLI backend, using one stream-json process per turn.

Protocol: https://antigravity.google/docs/cli/headless/
Only explicit conversation IDs are resumed; the global latest conversation is never used.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any, AsyncIterator

from .config import Config
from .runner import SessionSpec

logger = logging.getLogger(__name__)

SUMMARY_LIMIT = 200
TOOL_RESULT_LIMIT = 2000
INTERRUPT_GRACE_S = 5.0
CLEANUP_TIMEOUT_S = 5.0

PREFACE = """\
【运行环境说明，不用回复这一段】你运行在 momo 的 Agent 页里。用户只能在网页上看到你的文字回复、工具摘要和当前目录里的文件，看不到终端或 Antigravity 的审阅界面。
- 当前工作目录就是本次运行的目录，用户上传的文件在 input/ 下。所有产出都写在当前目录内，用户可以在网页上下载。
- 需要用户做选择或确认时，把要审阅的内容（术语表、稿件、字幕）和选项用 Markdown 完整写在回复里，然后结束这一轮，等用户在网页上回复。
- 这一轮结束时如果要等用户确认或回答才能继续，在回复最后单独一行写「【等待确认】」（页面据此提醒用户；用户一直不回时会自动按你推荐的方案继续）。任务全部做完时不要写。
- 命令直接在服务器上执行，本服务不保证沙箱隔离。这台服务器还跑着线上服务：除非用户要求或 skill 的说明需要，不要改动当前目录以外的文件，不要装系统级软件或重启服务。
"""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _clip(value: Any, limit: int) -> str:
    text = _text(value)
    return text if len(text) <= limit else text[:limit] + f"…（共 {len(text)} 字，已截断）"


class AntigravityMapper:
    """Accumulate incremental response deltas into the page's complete-message events."""

    def __init__(self, conversation_id: str | None = None) -> None:
        self.conversation_id = conversation_id
        self.turn_done = False
        self._started_at = time.monotonic()
        self._text_parts: dict[str, list[str]] = {}
        self._emitted_text: list[str] = []
        self._started_tools: set[str] = set()
        self._finished_steps: set[str] = set()

    def map(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(event, dict):
            raise ValueError("Gemini 输出的事件不是 JSON 对象")
        kind = event.get("event")
        if kind == "init":
            self.conversation_id = event.get("conversation_id") or self.conversation_id
            mapped = {"type": "session", "session_id": self.conversation_id}
            model = (event.get("init") or {}).get("model")
            if model:
                mapped["model"] = model
            return [mapped]
        if kind == "step_update":
            step = event.get("step_update") or {}
            self.conversation_id = step.get("conversation_id") or self.conversation_id
            return self._step(step)
        if kind == "result" and not self.turn_done:
            data = event.get("result") or {}
            self.conversation_id = data.get("conversation_id") or self.conversation_id
            self.turn_done = True
            events: list[dict[str, Any]] = []
            response = _text(data.get("response"))
            if response.strip() and response not in self._emitted_text and response != "".join(self._emitted_text):
                events.append({"type": "text", "text": response, "parent": None})
            status = data.get("status")
            is_error = status != "SUCCESS" or bool(data.get("error"))
            errors = [_clip(data.get("error") or f"Gemini 状态：{status or 'UNKNOWN'}", TOOL_RESULT_LIMIT)] if is_error else []
            mapped = self.result(is_error=is_error,
                                 subtype="interrupted" if status in {"CANCELED", "INTERRUPTED"} else None,
                                 errors=errors)
            if isinstance(data.get("duration_seconds"), (int, float)):
                mapped["duration_ms"] = int(data["duration_seconds"] * 1000)
            if isinstance(data.get("num_turns"), int):
                mapped["num_turns"] = data["num_turns"]
            if isinstance(data.get("usage"), dict):
                mapped["usage"] = data["usage"]
            if is_error:
                events.append({"type": "notice", "level": "error", "text": errors[0]})
            return events + [mapped]
        if kind == "error":
            raise ValueError(_clip(event.get("error") or event.get("message") or "Gemini 输出错误事件", TOOL_RESULT_LIMIT))
        return []

    def _step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        index = step.get("step_index")
        if index is None:
            return []
        step_id = f"agy-{self.conversation_id}-{index}"
        if step_id in self._finished_steps:
            return []
        done = step.get("state") == "DONE"
        if done:
            self._finished_steps.add(step_id)
        if step.get("step_type") == "agent_response":
            parts = self._text_parts.setdefault(step_id, [])
            parts.append(_text(step.get("text_delta")))
            if not done:
                return []
            text = "".join(self._text_parts.pop(step_id))
            if text.strip():
                self._emitted_text.append(text)
                return [{"type": "text", "text": text, "parent": None}]
            return []
        if step.get("step_type") != "tool":
            return []
        info = step.get("tool_info") or {}
        name = step.get("tool_name") or info.get("name") or "GeminiTool"
        parameters = info.get("parameters") or {}
        names = {"run_command": "Bash", "write_to_file": "Write", "replace_file_content": "Edit",
                 "multi_replace_file_content": "Edit", "view_file": "Read", "list_dir": "LS",
                 "find_by_name": "Glob", "grep_search": "Grep", "search_web": "WebSearch", "read_url_content": "WebFetch"}
        summary = next((parameters[key] for key in ("CommandLine", "TargetFile", "AbsolutePath", "SearchDirectory", "Query", "Url")
                        if isinstance(parameters, dict) and parameters.get(key)), parameters)
        events = []
        if step_id not in self._started_tools:
            self._started_tools.add(step_id)
            events.append({"type": "tool", "id": step_id, "name": names.get(name, name),
                           "summary": _clip(summary, SUMMARY_LIMIT), "parent": None})
        if done:
            error = info.get("error")
            output = _text(info.get("output"))
            if error:
                message = error.get("message") if isinstance(error, dict) else error
                output = "\n".join(part for part in (output, _text(message or error)) if part)
            events.append({"type": "tool_result", "id": step_id, "ok": not bool(error),
                           "text": _clip(output, TOOL_RESULT_LIMIT), "parent": None})
        return events

    def result(self, *, is_error: bool, subtype: str | None = None, errors: list[str] | None = None) -> dict[str, Any]:
        return {"type": "result", "session_id": self.conversation_id, "is_error": is_error,
                "subtype": subtype or ("error" if is_error else "success"),
                "duration_ms": int((time.monotonic() - self._started_at) * 1000), "num_turns": 1,
                "errors": errors or []}


def build_command(config: Config, conversation_id: str | None, model: str | None = None) -> list[str]:
    if config.sandbox:
        # agy --sandbox can silently do nothing on unsupported hosts. Do not claim isolation.
        raise ValueError("Gemini（agy CLI）无法保证服务器沙箱隔离；当前 SKILL_RUNNER_SANDBOX 要求沙箱，拒绝启动")
    command = [str(Path(config.antigravity_bin).expanduser()), "--input-format", "stream-json", "--output-format", "stream-json",
               "--dangerously-skip-permissions", "--print-timeout", "0s"]
    if conversation_id:
        command += ["--conversation", conversation_id]
    model = model or config.antigravity_model
    if model:
        command += ["--model", model]
    return command


class AntigravitySession:
    def __init__(self, config: Config, spec: SessionSpec):
        self._config, self._spec = config, spec
        self._mapper = AntigravityMapper(spec.resume)
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._inbox: asyncio.Queue[str] = asyncio.Queue()
        self._proc: asyncio.subprocess.Process | None = None
        self._startup: asyncio.Task | None = None
        self._io_done = asyncio.Event()
        self._io_done.set()
        self._cleanup_tasks: dict[int, asyncio.Task] = {}
        self._working = self._closed = self._interrupted = False
        self._worker = asyncio.create_task(self._work())

    @classmethod
    async def open(cls, config: Config, spec: SessionSpec) -> "AntigravitySession":
        build_command(config, spec.resume, spec.model)  # Validate before accepting a turn.
        return cls(config, spec)

    async def send(self, text: str) -> None:
        if self._closed:
            raise RuntimeError("Gemini 会话已关闭")
        await self._inbox.put(text)

    @property
    def busy(self) -> bool:
        return (self._working or not self._inbox.empty()
                or (not self._closed and not self._queue.empty())
                or self._proc is not None
                or any(not task.done() for task in self._cleanup_tasks.values()))

    async def _work(self) -> None:
        while not self._closed:
            prompt = await self._inbox.get()
            self._working, self._interrupted = True, False
            self._mapper = AntigravityMapper(self._mapper.conversation_id)
            try:
                await self._turn(prompt)
            except Exception as exc:  # Every failed turn must terminate in a page result.
                # Neither raw CLI output nor prompt-bearing exceptions go into service logs.
                logger.warning("antigravity turn failed for run %s (%s)", self._spec.run_id, type(exc).__name__)
                message = _clip(str(exc), TOOL_RESULT_LIMIT)
                await self._queue.put({"type": "notice", "level": "error", "text": f"Gemini 进程出错：{message}"})
                await self._queue.put(self._mapper.result(is_error=True, errors=[message]))
            finally:
                try:
                    await self._stop_process()
                finally:
                    self._working = False

    async def _read_stderr(self, stream: asyncio.StreamReader) -> str:
        tail = b""
        while chunk := await stream.read(8192):
            tail = (tail + chunk)[-8192:]
        return tail.decode("utf-8", "replace").strip()

    async def _turn(self, prompt: str) -> None:
        # Cleanup may run concurrently with an interrupt. Only hand it the pipes once
        # both normal readers have stopped, including on parsing/startup cancellation.
        io_done = self._io_done = asyncio.Event()
        try:
            await self._run_turn(prompt)
        finally:
            io_done.set()

    async def _run_turn(self, prompt: str) -> None:
        conversation_id = self._mapper.conversation_id
        command = build_command(self._config, conversation_id, self._spec.model)
        if not conversation_id:
            prompt = PREFACE + self._spec.prompt_note + "\n" + prompt
        logger.info("starting antigravity turn for run %s", self._spec.run_id)
        self._startup = asyncio.create_task(asyncio.create_subprocess_exec(
            *command, cwd=str(self._spec.cwd), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=16 * 1024 * 1024,
            **({"start_new_session": True} if os.name == "posix" else {}),
        ))
        try:
            self._proc = await asyncio.shield(self._startup)
        except asyncio.CancelledError:
            self._proc = await self._startup  # Capture children created during cancellation.
            raise
        finally:
            self._startup = None
        proc = self._proc
        assert proc.stdin and proc.stdout and proc.stderr
        stderr_task = asyncio.create_task(self._read_stderr(proc.stderr))
        terminal = None
        try:
            if not self._interrupted:
                message = {"event": "user", "message": {"content": prompt}}
                proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
                await proc.stdin.drain()
            proc.stdin.close()
            async for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError as exc:
                    raise ValueError("Gemini 输出了无效的 JSON 事件") from exc
                for mapped in self._mapper.map(event):
                    if mapped["type"] == "result":
                        terminal = mapped  # Wait for exit before reporting success.
                    else:
                        await self._queue.put(mapped)
            code = await proc.wait()
            stderr = await stderr_task
            if self._interrupted or code in (-signal.SIGINT, -signal.SIGTERM, 130):
                terminal = self._mapper.result(is_error=True, subtype="interrupted", errors=["已中断"])
            elif code != 0 or terminal is None:
                reason = f"Gemini 退出码 {code}：{stderr[-300:] or '未收到完整的 result 事件'}"
                if terminal is None or not terminal["is_error"]:
                    terminal = self._mapper.result(is_error=True, errors=[reason])
            await self._queue.put(terminal)
        finally:
            if not stderr_task.done():
                stderr_task.cancel()
            await asyncio.gather(stderr_task, return_exceptions=True)

    async def _stop_process(self) -> None:
        proc = self._proc
        if proc is None:
            return
        key = id(proc)
        task = self._cleanup_tasks.get(key)
        if task is None:
            task = asyncio.create_task(self._cleanup_process(proc, self._io_done))
            self._cleanup_tasks[key] = task
        try:
            # A canceled worker/interrupt must not cancel the shared child reaper.
            await asyncio.shield(task)
        finally:
            if task.done() and self._cleanup_tasks.get(key) is task:
                self._cleanup_tasks.pop(key)

    @staticmethod
    def _signal_process(proc: asyncio.subprocess.Process, *, force: bool) -> None:
        if os.name == "posix" and getattr(proc, "pid", None) is not None:
            # The group belongs to this turn (start_new_session=True). Its children
            # can still own our pipes after the leader has already exited.
            try:
                os.killpg(proc.pid, signal.SIGKILL if force else signal.SIGINT)
            except ProcessLookupError:
                pass
            return
        if proc.returncode is not None:
            return
        try:
            if force:
                proc.kill()
            else:
                proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
        except (ValueError, OSError):
            try:
                proc.terminate()  # Windows has no SIGINT for these children.
            except ProcessLookupError:
                pass

    async def _drain_pipes(self, proc: asyncio.subprocess.Process, io_done: asyncio.Event) -> None:
        await io_done.wait()
        async def discard(stream: asyncio.StreamReader | None) -> None:
            if stream is not None:
                while await stream.read(65536):
                    pass  # Bounded memory; do not retain or log failed CLI output.
        await asyncio.gather(discard(getattr(proc, "stdout", None)), discard(getattr(proc, "stderr", None)))

    async def _cleanup_process(self, proc: asyncio.subprocess.Process, io_done: asyncio.Event) -> None:
        draining = asyncio.create_task(self._drain_pipes(proc, io_done))
        try:
            self._signal_process(proc, force=False)
            try:
                await asyncio.wait_for(proc.wait(), INTERRUPT_GRACE_S)
            except asyncio.TimeoutError:
                pass
            self._signal_process(proc, force=True)
            # wait() can remain pending after exit while a full pipe is paused. Drain
            # both pipes concurrently, and bound the wait if a descendant escaped.
            await asyncio.wait_for(asyncio.gather(proc.wait(), draining), CLEANUP_TIMEOUT_S)
        finally:
            if not draining.done():
                draining.cancel()
            await asyncio.gather(draining, return_exceptions=True)
        if self._proc is proc:
            self._proc = None

    async def interrupt(self) -> None:
        self._interrupted = True
        if self._startup is not None:
            self._proc = await asyncio.shield(self._startup)
        await self._stop_process()

    async def close(self) -> None:
        self._closed = True
        self._worker.cancel()
        await asyncio.gather(self._worker, return_exceptions=True)
        await self._stop_process()
        while not self._inbox.empty():
            self._inbox.get_nowait()
        await self._queue.put(None)

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event


def make_antigravity_factory(config: Config):
    async def factory(spec: SessionSpec) -> AntigravitySession:
        return await AntigravitySession.open(config, spec)
    return factory
