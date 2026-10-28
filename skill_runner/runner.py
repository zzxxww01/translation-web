"""运行生命周期。

每次运行对应一个 Claude 会话（由会话工厂创建，生产环境是 sdk_session.SdkSession）。状态：

    running  一轮正在进行
    waiting  有提问等用户在页面上回答（AskUserQuestion 挂起在 can_use_tool 回调里）
    idle     本轮结束，等用户发下一条消息；空闲久了会断开 Claude 进程，下次发消息时按会话 ID 续接
             （回复末尾带 AWAIT_MARK 时 awaiting_reply=True：是在等用户确认，不是做完了）

任务设了 auto_reply_s 时，等确认（提问挂着，或带等待标记的一轮结束）超过这么久没人回复，
就自动按推荐方案继续：提问选推荐选项，其余发一条「按你的建议确认、继续」，每个任务最多自动 AUTO_REPLY_LIMIT 次。
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
from contextlib import contextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol

from . import agents, policy
from .config import HARNESSES, Config
from .models import validate_model
from .store import RunMeta, RunStore

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"running", "waiting"}

AWAIT_MARK = "【等待确认】"
AUTO_REPLY_LIMIT = 3
AUTO_REPLY_TEXT = (
    "（自动确认）{wait}没有收到回复。请按你推荐的方案确认（比如术语表全部采用建议译法），"
    "接下来不要再停下来等确认，直接完成剩下的全部步骤。"
)


def wait_text(seconds: float) -> str:
    return f"{round(seconds / 60)} 分钟" if seconds >= 60 else f"{int(seconds)} 秒"


def recommended_answer(question: dict[str, Any]) -> str | list[str]:
    """提问的推荐选项：标了 Recommended / 推荐的那个，没有就第一个。"""
    labels = [str(o.get("label")) for o in question.get("options") or [] if isinstance(o, dict) and o.get("label")]
    pick = next((label for label in labels if "recommended" in label.lower() or "推荐" in label), labels[0] if labels else "按你的建议")
    return [pick] if question.get("multiSelect") else pick


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
    # 按任务追加到系统提示词的说明（见 agents.prompt_note）
    prompt_note: str = ""
    harness: str = "claude"
    model: str | None = None


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
    auto_task: asyncio.Task | None = None
    # 这一轮最后一段文字（判断是不是以等待标记结尾）
    last_text: str = ""
    closing: bool = False
    pending: dict[str, _Pending] = field(default_factory=dict)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    close_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def harness_label(harness: str) -> str:
    return {"claude": "Claude", "codex": "Codex", "antigravity": "Antigravity"}.get(harness, harness)


def build_prompt(
    skill: str | None, message: str, attachments: list[str], harness: str = "claude", skills_dir: Path | None = None
) -> str:
    text = message.strip()
    if skill and harness in {"codex", "antigravity"}:
        # CLI 后端显式读取共用 SKILL.md，不依赖各自的 slash command 派发
        skill_md = (skills_dir or Path.home() / ".agents" / "skills") / skill / "SKILL.md"
        text = f"使用 skill「{skill}」：先完整阅读 {skill_md}，严格按其中的流程完成下面的任务。\n\n{text}".rstrip()
    elif skill:
        # /<skill> 直接派发 skill，正文作为参数跟在后面
        text = f"/{skill} {text}".rstrip()
    if attachments:
        listing = "\n".join(f"- {path}" for path in attachments)
        text += f"\n\n附件（已保存在当前运行目录）：\n{listing}"
    return text


def make_title(message: str, attachments: list[str], title: str = "") -> str:
    """对话标题：调用方给了（比如文章工作台给文章标题）就用它，否则用消息第一句，再不然用附件名。"""
    first_line = message.strip().splitlines()[0] if message.strip() else ""
    first_sentence = first_line.split("。")[0] if len(first_line) > 30 else first_line
    title = title.strip() or first_sentence or (Path(attachments[0]).name if attachments else "新对话")
    return title[:60]


class Runner:
    def __init__(self, config: Config, store: RunStore, session_factory: SessionFactory):
        self.config = config
        self.store = store
        self.session_factory = session_factory
        self._runs: dict[str, _Run] = {}
        self._runtime_maintenance = False
        self._runtime_users = 0

    @contextmanager
    def runtime_use(self):
        """Reserve runtime use before the first await, including CLI startup/discovery."""
        if self._runtime_maintenance:
            raise Conflict("正在更新运行工具，请完成后再开始或继续对话")
        self._runtime_users += 1
        try:
            yield
        finally:
            self._runtime_users -= 1

    def reserve_runtime_update(self) -> None:
        if self._runtime_maintenance:
            raise Conflict("已有更新正在进行")
        if (self._runtime_users
                or any(meta.status in ACTIVE_STATUSES or meta.awaiting_reply for meta in self.list_runs())
                or any(self._session_busy(run) for run in self._runs.values())):
            raise Conflict("还有对话正在运行或等待确认，请结束后再更新")
        self._runtime_maintenance = True

    async def close_idle_for_runtime_update(self) -> None:
        if not self._runtime_maintenance:
            raise Conflict("尚未进入更新状态")
        for run in list(self._runs.values()):
            if self._session_busy(run):
                raise Conflict("还有已接收的对话正在处理，请完成后再更新")
            await self._close_session(run, strict=True)

    def release_runtime_update(self) -> None:
        self._runtime_maintenance = False

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
        return sum(1 for run in self._runs.values() if run.meta.status in ACTIVE_STATUSES or self._session_busy(run))

    @staticmethod
    def _session_busy(run: _Run) -> bool:
        # Queued harnesses may emit a result before all accepted work/processes finish.
        return bool(getattr(run.session, "busy", False))

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
        # awaiting：这一轮结束时是在等用户确认（不是做完了），页面据此显示「等你确认」
        self._emit(run, {"type": "status", "status": status, "error": error, "awaiting": run.meta.awaiting_reply})

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

    def create(self, skill: str, title: str, harness: str = "claude", auto_reply_s: int = 0,
               model: str | None = None) -> RunMeta:
        if self._runtime_maintenance:
            raise Conflict("正在更新运行工具，请完成后再开始对话")
        # skill 为空就是直接对话：消息原样发给 Claude / Codex，不派发 skill
        if skill and skill not in self.config.skills:
            raise RunnerError(f"未启用的 skill：{skill}")
        if harness not in HARNESSES:
            raise RunnerError(f"不支持的 harness：{harness}")
        try:
            model = validate_model(model)
        except ValueError as exc:
            raise RunnerError(str(exc)) from exc
        if self.active_count() >= self.config.max_active:
            raise Busy(f"已有 {self.config.max_active} 个任务在运行，请等其中一个结束")
        meta = self.store.create(skill, title, harness, auto_reply_s, model=model)
        self._runs[meta.id] = _Run(meta=meta, seq=0)
        return meta

    async def begin(self, run_id: str, message: str, attachments: list[str]) -> RunMeta:
        run = self._get(run_id)
        prompt = build_prompt(run.meta.skill, message, attachments, run.meta.harness, self.config.shared_skills_dir)
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
        with self.runtime_use():
            return await self._deliver_to_session(run, message, attachments, prompt)

    async def _deliver_to_session(self, run: _Run, message: str, attachments: list[str], prompt: str) -> RunMeta:
        async with run.lock:
            if run.closing:
                try:
                    await self._close_session(run, strict=True)
                except Exception as exc:
                    raise SessionFailed(f"上次会话未能关闭，请稍后重试：{exc}") from exc
            need_open = run.session is None
            if need_open and run.meta.status not in ACTIVE_STATUSES and self.active_count() >= self.config.max_active:
                raise Busy(f"已有 {self.config.max_active} 个任务在运行，请等其中一个结束")
            # 先记下用户的话再起会话：起不来时页面上也能看到发了什么、为什么失败
            self._emit(run, {"type": "user", "text": message, "files": attachments})
            self._clear_awaiting(run)
            run.last_text = ""
            if need_open:
                await self._open(run)
            self._cancel_idle(run)
            self._set_status(run, "running")
            try:
                assert run.session is not None
                await run.session.send(prompt)
            except Exception as exc:  # noqa: BLE001 - 任何发送失败都要反映到页面上
                logger.exception("send failed for run %s", run.meta.id)
                await self._fail(run, f"消息没能发给 {harness_label(run.meta.harness)}：{exc}")
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
            prompt_note=agents.prompt_note(agents.build_catalog(self.config), run.meta.skill),
            harness=run.meta.harness,
            # Codex 续接时沿用这次运行已经定下的模型（中途清单更新也不换）
            model=run.meta.model or (run.meta.actual_model if run.meta.harness == "codex" and run.meta.session_id else None),
        )
        try:
            session = await self.session_factory(spec)
        except Exception as exc:  # noqa: BLE001
            logger.exception("failed to open session for run %s", run.meta.id)
            label = harness_label(run.meta.harness)
            self._emit(run, {"type": "error", "text": f"启动 {label} 失败：{exc}"})
            self._set_status(run, "error", f"启动 {label} 失败：{exc}")
            raise SessionFailed(str(exc)) from exc
        run.session = session
        run.closing = False
        run.pump = asyncio.create_task(self._pump(run, session))

    async def _pump(self, run: _Run, session: AgentSession) -> None:
        try:
            async for event in session.events():
                if run.session is session and not run.closing:
                    self._on_event(run, event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if run.session is session and not run.closing:
                logger.exception("session stream failed for run %s", run.meta.id)
                await self._fail(run, f"{harness_label(run.meta.harness)} 进程出错：{exc}")
            return
        if run.session is session and not run.closing:
            # 流在没有被我们关闭的情况下结束了：进程退出
            if run.meta.status in ACTIVE_STATUSES:
                await self._fail(run, f"{harness_label(run.meta.harness)} 进程意外退出")
            else:
                run.session = None

    def _on_event(self, run: _Run, event: dict[str, Any]) -> None:
        kind = event.get("type")
        if kind == "session":
            if event.get("model") and event["model"] != run.meta.actual_model:
                run.meta.actual_model = event["model"]
                self.store.save_meta(run.meta)
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
                run.meta.awaiting_reply = not event.get("is_error") and AWAIT_MARK in run.last_text
                self._set_status(run, "idle")
                self.store.save_meta(run.meta)
                self._schedule_idle(run)
                if run.meta.awaiting_reply:
                    self._schedule_auto_reply(run)
            return
        if kind == "text" and not event.get("parent"):
            run.last_text = str(event.get("text") or "")
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
            if len(run.pending) == 1:
                self._schedule_auto_reply(run)
            try:
                return await future
            finally:
                run.pending.pop(qid, None)
                if not run.pending:
                    self._cancel_auto_reply(run)
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
        self._clear_awaiting(run)
        for pending in list(run.pending.values()):
            if not pending.future.done():
                pending.future.set_result(PermissionOutcome(allow=False, message="用户中断了任务", interrupt=True))
        if run.session is not None and (run.meta.status in ACTIVE_STATUSES or self._session_busy(run)):
            self._emit(run, {"type": "notice", "level": "info", "text": "已发送中断"})
            try:
                await run.session.interrupt()
            except Exception as exc:  # noqa: BLE001
                logger.exception("interrupt failed for run %s", run_id)
                await self._fail(run, f"中断失败：{exc}")
        return run.meta

    async def stop(self, run_id: str) -> RunMeta:
        """Close all accepted work before replacing a run; retain its history and resume ID."""
        run = self._get(run_id)
        async with run.lock:
            self._clear_awaiting(run)
            for pending in list(run.pending.values()):
                if not pending.future.done():
                    pending.future.set_result(PermissionOutcome(allow=False, message="用户停止了任务", interrupt=True))
            try:
                await self._close_session(run, strict=True)
            except Exception as exc:
                # A replacement must not start while the previous process may still be live.
                raise SessionFailed(f"旧任务未能停止：{exc}") from exc
            self._clear_awaiting(run)
            self._set_status(run, "error", "任务已停止；对话和文件已保留，发送消息可以继续原会话")
        return run.meta

    async def delete(self, run_id: str, *, reason: str = "user", client_ip: str | None = None) -> None:
        """从页面上删掉对话：会话先关干净，目录挪进 deleted/ 存档（见 RunStore.archive）。"""
        run = self._get(run_id)
        if run.meta.status in ACTIVE_STATUSES or self._session_busy(run):
            raise Conflict("任务还在运行，先中断再删除")
        self._cancel_auto_reply(run)
        try:
            await self._close_session(run, strict=True)
        except Exception as exc:
            raise SessionFailed(f"会话未能关闭，暂时无法删除：{exc}") from exc
        if self._runs.get(run_id) is not run:  # 等关会话的时候，另一个删除请求已经删完了
            raise NotFound("运行不存在")
        for queue in list(run.subscribers):
            queue.put_nowait(None)
        self._runs.pop(run_id, None)
        self.store.archive(run_id, reason=reason, client_ip=client_ip)

    # ---- 等确认超时自动继续 ----

    def _schedule_auto_reply(self, run: _Run, delay: float | None = None) -> None:
        self._cancel_auto_reply(run)
        if run.meta.auto_reply_s <= 0 or run.meta.auto_replies >= AUTO_REPLY_LIMIT:
            return
        delay = run.meta.auto_reply_s if delay is None else delay
        run.meta.auto_reply_at = time.time() + delay
        self.store.save_meta(run.meta)
        self._emit(run, {
            "type": "notice", "level": "info",
            "text": f"{wait_text(run.meta.auto_reply_s)}内没有回复，会自动按推荐方案继续",
        })
        run.auto_task = asyncio.create_task(self._auto_reply_later(run, delay))

    def _cancel_auto_reply(self, run: _Run) -> None:
        if run.auto_task is not None and run.auto_task is not asyncio.current_task():
            run.auto_task.cancel()
        run.auto_task = None
        if run.meta.auto_reply_at is not None:
            run.meta.auto_reply_at = None
            self.store.save_meta(run.meta)

    def _clear_awaiting(self, run: _Run) -> None:
        self._cancel_auto_reply(run)
        if run.meta.awaiting_reply:
            run.meta.awaiting_reply = False
            self.store.save_meta(run.meta)

    async def _auto_reply_later(self, run: _Run, delay: float) -> None:
        task = asyncio.current_task()
        try:
            await asyncio.sleep(max(0.0, delay))
            # Keep the task cancellable while delivery is queued behind stop/user input.
            run.meta.auto_reply_at = None
            run.meta.auto_replies += 1
            self.store.save_meta(run.meta)
            waited = wait_text(run.meta.auto_reply_s)
            if run.pending:
                for qid, pending in list(run.pending.items()):
                    answers = {str(q.get("question", "")): recommended_answer(q) for q in pending.questions}
                    self._emit(run, {"type": "notice", "level": "info", "text": f"{waited}没有回答，已自动选推荐选项"})
                    self._resolve_question(run, qid, {"answers": answers})
                return
            if run.meta.status != "idle" or not run.meta.awaiting_reply:
                return
            self._emit(run, {"type": "notice", "level": "info", "text": f"{waited}没有回复，自动按推荐方案继续"})
            text = AUTO_REPLY_TEXT.format(wait=waited)
            try:
                await self._deliver(run, text, [], text)
            except RunnerError:
                logger.exception("auto reply failed for run %s", run.meta.id)
        finally:
            if run.auto_task is task:
                run.auto_task = None

    def resume_auto_replies(self) -> int:
        """服务启动时调用（在事件循环里）：重启前排着的自动回复接着排，时间照旧。"""
        resumed = 0
        for meta in self.store.list_meta():
            if meta.status == "idle" and meta.awaiting_reply and meta.auto_reply_at is not None:
                run = self._get(meta.id)
                self._schedule_auto_reply(run, delay=max(5.0, meta.auto_reply_at - time.time()))
                resumed += 1
        return resumed

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
            if self._session_busy(run):
                self._schedule_idle(run)
            else:
                await self._close_session(run)

    async def _close_session(self, run: _Run, *, strict: bool = False) -> None:
        self._cancel_idle(run)
        async with run.close_lock:
            session = run.session
            if session is None:
                return
            # Keep uncertain/live sessions tracked, including on failure or cancellation.
            run.closing = True
            try:
                await session.close()
            except Exception:  # noqa: BLE001
                logger.exception("closing session for run %s failed", run.meta.id)
                if strict:
                    raise
            else:
                run.session = None
                run.closing = False
            finally:
                if run.pump is not None and run.pump is not asyncio.current_task():
                    run.pump.cancel()
                run.pump = None

    async def _fail(self, run: _Run, message: str) -> None:
        self._clear_awaiting(run)
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
            if run.auto_task is not None:
                run.auto_task.cancel()  # 不清 auto_reply_at：重启后 resume_auto_replies 接着排
            if run.session is not None:
                await self._close_session(run)
            for queue in list(run.subscribers):
                queue.put_nowait(None)
