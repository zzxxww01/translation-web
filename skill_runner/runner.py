"""运行生命周期。

每次运行对应一个 Claude 会话（由会话工厂创建，生产环境是 sdk_session.SdkSession）。状态：

    running  一轮正在进行
    waiting  有提问等用户在页面上回答（AskUserQuestion 挂起在 can_use_tool 回调里）
    idle     本轮结束，等用户发下一条消息；空闲久了会断开 Claude 进程，下次发消息时按会话 ID 续接
    error    出错或服务重启导致中断；用户发消息即从会话断点续跑

所有页面事件带递增 seq，先落盘到 events.jsonl 再推给 SSE 订阅者，所以页面断线、刷新、
服务重启后都能完整回放。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol

from . import policy
from .config import Config
from .store import RunMeta, RunStore

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"running", "waiting"}


@dataclass
class PermissionOutcome:
    allow: bool
    updated_input: dict[str, Any] | None = None
    message: str = ""
    interrupt: bool = False


# 参数：工具名、工具参数、tool_use_id、Claude Code 给出的请求原因（如「要访问某域名」，可能为空）
PermissionHandler = Callable[[str, dict[str, Any], "str | None", "str | None"], Awaitable[PermissionOutcome]]


@dataclass
class SessionSpec:
    run_id: str
    cwd: Path
    resume: str | None
    on_permission: PermissionHandler


class AgentSession(Protocol):
    async def send(self, text: str) -> None: ...
    async def interrupt(self) -> None: ...
    async def close(self) -> None: ...
    def events(self) -> AsyncIterator[dict[str, Any]]: ...


SessionFactory = Callable[[SessionSpec], Awaitable[AgentSession]]


class RunnerError(Exception):
    status_code = 400


class NotFound(RunnerError):
    status_code = 404


class Busy(RunnerError):
    status_code = 429


class Conflict(RunnerError):
    status_code = 409


class SessionFailed(RunnerError):
    status_code = 502


@dataclass
class _Pending:
    questions: list[dict[str, Any]]
    future: asyncio.Future


@dataclass
class _Run:
    meta: RunMeta
    seq: int
    session: AgentSession | None = None
    pump: asyncio.Task | None = None
    idle_task: asyncio.Task | None = None
    closing: bool = False
    pending: dict[str, _Pending] = field(default_factory=dict)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def build_prompt(skill: str | None, message: str, attachments: list[str]) -> str:
    text = message.strip()
    if skill:
        # /<skill> 直接派发 skill，正文作为参数跟在后面
        text = f"/{skill} {text}".rstrip()
    if attachments:
        listing = "\n".join(f"- {path}" for path in attachments)
        text += f"\n\n附件（已保存在当前运行目录）：\n{listing}"
    return text


def make_title(message: str, attachments: list[str]) -> str:
    first_line = message.strip().splitlines()[0] if message.strip() else ""
    title = first_line or (Path(attachments[0]).name if attachments else "新运行")
    return title[:60]


class Runner:
    def __init__(self, config: Config, store: RunStore, session_factory: SessionFactory):
        self.config = config
        self.store = store
        self.session_factory = session_factory
        self._runs: dict[str, _Run] = {}

    # ---- 查询 ----

    def _get(self, run_id: str) -> _Run:
        run = self._runs.get(run_id)
        if run is not None:
            return run
        meta = self.store.load_meta(run_id)
        if meta is None:
            raise NotFound("运行不存在")
        run = _Run(meta=meta, seq=self.store.last_seq(run_id))
        self._runs[run_id] = run
        return run

    def meta(self, run_id: str) -> RunMeta:
        return self._get(run_id).meta

    def list_runs(self) -> list[RunMeta]:
        metas = self.store.list_meta()
        # 内存里的状态比磁盘新（磁盘只在状态切换时写）
        return [self._runs[m.id].meta if m.id in self._runs else m for m in metas]

    def active_count(self) -> int:
        return sum(1 for run in self._runs.values() if run.meta.status in ACTIVE_STATUSES)

    # ---- 事件 ----

    def _emit(self, run: _Run, event: dict[str, Any]) -> dict[str, Any]:
        run.seq += 1
        stamped = {"seq": run.seq, "ts": time.time(), **event}
        self.store.append_event(run.meta.id, stamped)
        for queue in list(run.subscribers):
            queue.put_nowait(stamped)
        return stamped

    def _set_status(self, run: _Run, status: str, error: str | None = None) -> None:
        if run.meta.status == status and run.meta.error == error:
            return
        run.meta.status = status
        run.meta.error = error
        run.meta.updated_at = time.time()
        self.store.save_meta(run.meta)
        self._emit(run, {"type": "status", "status": status, "error": error})

    def subscribe(self, run_id: str, after_seq: int = 0) -> tuple[list[dict[str, Any]], asyncio.Queue]:
        run = self._get(run_id)
        # 读回放和登记订阅之间没有 await，不会漏掉或重复事件
        backlog = self.store.read_events(run_id, after_seq)
        queue: asyncio.Queue = asyncio.Queue()
        run.subscribers.add(queue)
        return backlog, queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        run = self._runs.get(run_id)
        if run is not None:
            run.subscribers.discard(queue)

    # ---- 生命周期 ----

    def create(self, skill: str, title: str) -> RunMeta:
        if skill not in self.config.skills:
            raise RunnerError(f"未启用的 skill：{skill}")
        if self.active_count() >= self.config.max_active:
            raise Busy(f"已有 {self.config.max_active} 个任务在运行，请等其中一个结束")
        meta = self.store.create(skill, title)
        self._runs[meta.id] = _Run(meta=meta, seq=0)
        return meta

    async def begin(self, run_id: str, message: str, attachments: list[str]) -> RunMeta:
        run = self._get(run_id)
        prompt = build_prompt(run.meta.skill, message, attachments)
        return await self._deliver(run, message, attachments, prompt)

    async def send_message(self, run_id: str, message: str, attachments: list[str]) -> RunMeta:
        run = self._get(run_id)
        if not message.strip() and not attachments:
            raise RunnerError("消息不能为空")
        if run.pending and not attachments:
            # 有提问挂着时，输入框里的话就是对提问的自由回答
            qid = next(iter(run.pending))
            self._emit(run, {"type": "user", "text": message, "files": []})
            self._resolve_question(run, qid, {"response": message})
            return run.meta
        return await self._deliver(run, message, attachments, build_prompt(None, message, attachments))

    async def _deliver(self, run: _Run, message: str, attachments: list[str], prompt: str) -> RunMeta:
        async with run.lock:
            need_open = run.session is None
            if need_open and run.meta.status not in ACTIVE_STATUSES and self.active_count() >= self.config.max_active:
                raise Busy(f"已有 {self.config.max_active} 个任务在运行，请等其中一个结束")
            # 先记下用户的话再起会话：起不来时页面上也能看到发了什么、为什么失败
            self._emit(run, {"type": "user", "text": message, "files": attachments})
            if need_open:
                await self._open(run)
            self._cancel_idle(run)
            self._set_status(run, "running")
            try:
                assert run.session is not None
                await run.session.send(prompt)
            except Exception as exc:  # noqa: BLE001 - 任何发送失败都要反映到页面上
                logger.exception("send failed for run %s", run.meta.id)
                await self._fail(run, f"消息没能发给 Claude：{exc}")
                raise SessionFailed(str(exc)) from exc
        return run.meta

    async def _open(self, run: _Run) -> None:
        spec = SessionSpec(
            run_id=run.meta.id,
            cwd=self.store.run_dir(run.meta.id),
            resume=run.meta.session_id,
            on_permission=lambda name, data, tool_use_id, reason=None: self._on_permission(
                run, name, data, tool_use_id, reason
            ),
        )
        try:
            session = await self.session_factory(spec)
        except Exception as exc:  # noqa: BLE001
            logger.exception("failed to open session for run %s", run.meta.id)
            self._emit(run, {"type": "error", "text": f"启动 Claude 失败：{exc}"})
            self._set_status(run, "error", f"启动 Claude 失败：{exc}")
            raise SessionFailed(str(exc)) from exc
        run.session = session
        run.closing = False
        run.pump = asyncio.create_task(self._pump(run, session))

    async def _pump(self, run: _Run, session: AgentSession) -> None:
        try:
            async for event in session.events():
                self._on_event(run, event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if not run.closing:
                logger.exception("session stream failed for run %s", run.meta.id)
                await self._fail(run, f"Claude 进程出错：{exc}")
            return
        if run.session is session and not run.closing:
            # 流在没有被我们关闭的情况下结束了：进程退出
            if run.meta.status in ACTIVE_STATUSES:
                await self._fail(run, "Claude 进程意外退出")
            else:
                run.session = None

    def _on_event(self, run: _Run, event: dict[str, Any]) -> None:
        kind = event.get("type")
        if kind == "session":
            session_id = event.get("session_id")
            if session_id and session_id != run.meta.session_id:
                run.meta.session_id = session_id
                self.store.save_meta(run.meta)
            return
        if kind == "result":
            if event.get("session_id") and event["session_id"] != run.meta.session_id:
                run.meta.session_id = event["session_id"]
            self._emit(run, event)
            if not run.pending:
                self._set_status(run, "idle")
                self._schedule_idle(run)
            return
        if run.meta.status == "idle":
            # 运行中插的话会在上一轮结束后接着跑，此时又有新内容进来
            self._cancel_idle(run)
            self._set_status(run, "running")
        self._emit(run, event)

    async def _on_permission(
        self,
        run: _Run,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str | None,
        reason: str | None = None,
    ) -> PermissionOutcome:
        if tool_name == "AskUserQuestion":
            qid = tool_use_id or uuid.uuid4().hex
            questions = tool_input.get("questions") or []
            future: asyncio.Future = asyncio.get_running_loop().create_future()
            run.pending[qid] = _Pending(questions=questions, future=future)
            self._emit(run, {"type": "question", "qid": qid, "questions": questions})
            self._set_status(run, "waiting")
            try:
                return await future
            finally:
                run.pending.pop(qid, None)
                if not run.pending and run.meta.status == "waiting":
                    self._set_status(run, "running")
        decision = policy.decide(
            tool_name,
            tool_input,
            run_dir=self.store.run_dir(run.meta.id),
            extra_write=self.config.extra_write,
            sandbox=self.config.sandbox,
        )
        if not decision.allow:
            # 带上 Claude Code 给的原因（比如具体要访问哪个域名），否则页面上看不出到底拦了什么
            detail = f"（{reason}）" if reason else ""
            self._emit(run, {"type": "notice", "level": "warn", "text": f"已拦截 {tool_name}{detail}：{decision.message}"})
            return PermissionOutcome(allow=False, message=decision.message)
        return PermissionOutcome(allow=True)

    def answer(
        self,
        run_id: str,
        qid: str,
        answers: dict[str, Any] | None = None,
        response: str | None = None,
    ) -> RunMeta:
        run = self._get(run_id)
        if qid not in run.pending:
            raise Conflict("这个提问已经回答过或已失效")
        payload: dict[str, Any] = {}
        if answers:
            payload["answers"] = answers
        if response:
            payload["response"] = response
        if not payload:
            raise RunnerError("回答不能为空")
        self._resolve_question(run, qid, payload)
        return run.meta

    def _resolve_question(self, run: _Run, qid: str, payload: dict[str, Any]) -> None:
        pending = run.pending[qid]
        self._emit(run, {"type": "answer", "qid": qid, **payload})
        if not pending.future.done():
            pending.future.set_result(
                PermissionOutcome(allow=True, updated_input={"questions": pending.questions, **payload})
            )

    async def interrupt(self, run_id: str) -> RunMeta:
        run = self._get(run_id)
        for pending in list(run.pending.values()):
            if not pending.future.done():
                pending.future.set_result(PermissionOutcome(allow=False, message="用户中断了任务", interrupt=True))
        if run.session is not None and run.meta.status in ACTIVE_STATUSES:
            self._emit(run, {"type": "notice", "level": "info", "text": "已发送中断"})
            try:
                await run.session.interrupt()
            except Exception as exc:  # noqa: BLE001
                logger.exception("interrupt failed for run %s", run_id)
                await self._fail(run, f"中断失败：{exc}")
        return run.meta

    async def delete(self, run_id: str) -> None:
        run = self._get(run_id)
        if run.meta.status in ACTIVE_STATUSES:
            raise Conflict("任务还在运行，先中断再删除")
        await self._close_session(run)
        for queue in list(run.subscribers):
            queue.put_nowait(None)
        self._runs.pop(run_id, None)
        self.store.delete(run_id)

    # ---- 回收与故障 ----

    def _schedule_idle(self, run: _Run) -> None:
        self._cancel_idle(run)
        run.idle_task = asyncio.create_task(self._idle_close(run))

    def _cancel_idle(self, run: _Run) -> None:
        if run.idle_task is not None and run.idle_task is not asyncio.current_task():
            run.idle_task.cancel()
        run.idle_task = None

    async def _idle_close(self, run: _Run) -> None:
        await asyncio.sleep(self.config.idle_timeout_s)
        if run.meta.status == "idle" and not run.pending:
            run.idle_task = None
            await self._close_session(run)

    async def _close_session(self, run: _Run) -> None:
        self._cancel_idle(run)
        session, run.session = run.session, None
        if session is None:
            return
        run.closing = True
        try:
            await session.close()
        except Exception:  # noqa: BLE001
            logger.exception("closing session for run %s failed", run.meta.id)
        if run.pump is not None and run.pump is not asyncio.current_task():
            run.pump.cancel()
        run.pump = None

    async def _fail(self, run: _Run, message: str) -> None:
        for pending in list(run.pending.values()):
            if not pending.future.done():
                pending.future.set_result(PermissionOutcome(allow=False, message=message, interrupt=True))
        self._emit(run, {"type": "error", "text": message})
        self._set_status(run, "error", message)
        await self._close_session(run)

    def recover(self) -> int:
        """服务启动时调用：上次没跑完的运行标成 error，用户发消息即可按会话续跑。"""
        recovered = 0
        for meta in self.store.list_meta():
            if meta.status in ACTIVE_STATUSES:
                run = self._get(meta.id)
                message = "服务重启导致任务中断，发送一条消息（比如「继续」）即可从断点接着跑"
                self._emit(run, {"type": "error", "text": message})
                self._set_status(run, "error", message)
                recovered += 1
        return recovered

    async def shutdown(self) -> None:
        for run in list(self._runs.values()):
            if run.session is not None:
                await self._close_session(run)
            for queue in list(run.subscribers):
                queue.put_nowait(None)
