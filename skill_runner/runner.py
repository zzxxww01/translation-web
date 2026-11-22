"""运行生命周期。

每次运行对应一个 Claude 会话（由会话工厂创建，生产环境是 sdk_session.SdkSession）。状态：

    running  一轮正在进行
    waiting  有提问等用户在页面上回答（AskUserQuestion 挂起在 can_use_tool 回调里）
    idle     本轮结束，等用户发下一条消息；几秒后就断开进程（不常驻），下次发消息时按会话 ID 续接
             （回复末尾带 AWAIT_MARK 时 awaiting_reply=True：是在等用户确认，不是做完了）
    queued   名额满了（或内存不够），消息存在 meta.queued_prompt 里排队，有空位按先来后到自动发出

名额按活着的进程算（会话没关就占着，正在启动的也算），重活（config.heavy_skills）算 2 个。
提问挂着超过 question_detach_s 没人回答，就把问题存进 meta.detached_questions、关掉进程；
之后的回答作为一条新消息续接会话。

任务设了 auto_reply_s 时，等确认（提问挂着，或带等待标记的一轮结束）超过这么久没人回复，
就自动按推荐方案继续：提问选推荐选项，其余发一条「按你的建议确认、继续」，每个任务最多自动 AUTO_REPLY_LIMIT 次。
    error    出错或服务重启导致中断；用户发消息即从会话断点续跑

所有页面事件带递增 seq，先落盘到 events.jsonl 再推给 SSE 订阅者，所以页面断线、刷新、
服务重启后都能完整回放。
"""

from __future__ import annotations

import asyncio
import logging
import re
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
QUEUED = "queued"
# 页面自己处理的命令（不发给模型）
STATUS_COMMANDS = {"/status", "/状态"}

AWAIT_MARK = "【等待确认】"
# 只认回复末尾的标记（和页面 state.ts 一致）：正文里提到这几个字不算在等确认
_AWAIT_AT_END = re.compile(re.escape(AWAIT_MARK) + r"\s*$")
AUTO_REPLY_LIMIT = 3
DETACH_MESSAGE = "用户暂时没回答，问题已保留在页面上；回答会作为下一条消息发来。请就此结束这一轮，先不要继续做。"
# 等确认超时后替用户发的话（页面上另有一行小字说明这是自动发的）
AUTO_REPLY_TEXT = "继续，按照你的想法做就行了，不需要和我确认"


def awaits_reply(text: str) -> bool:
    """这一轮是不是停下来等用户确认：回复以【等待确认】结尾。"""
    return bool(_AWAIT_AT_END.search(text or ""))


def mem_available_mb() -> int | None:
    """系统可用内存（MB），读不到返回 None（不按内存拦）。"""
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def answer_text(questions_by_qid: dict[str, Any], answers: dict[str, Any] | None, response: str | None) -> str:
    """脱离进程的提问被回答时，作为新消息发给 agent 的话。"""
    lines = ["（回答你之前的提问）"]
    for questions in questions_by_qid.values():
        for q in questions or []:
            question = str(q.get("question", "")) if isinstance(q, dict) else ""
            if answers and question in answers:
                value = answers[question]
                value = "、".join(map(str, value)) if isinstance(value, list) else str(value)
                lines.append(f"- {question}：{value}")
    if response:
        lines.append(response.strip())
    lines.append("请按这个回答接着做。")
    return "\n".join(lines)


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
    detach_task: asyncio.Task | None = None
    # 正在起进程（还没赋给 session）：也占名额，避免同时起多个
    opening: bool = False
    # 用户点了停止：这一轮结束后挂起的消息不自动发
    interrupted: bool = False
    # 这一轮最后一段文字（判断是不是以等待标记结尾）
    last_text: str = ""
    closing: bool = False
    pending: dict[str, _Pending] = field(default_factory=dict)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    close_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def harness_label(harness: str) -> str:
    # 界面上第三个 Agent 叫 Gemini；内部 id 仍是 antigravity（官方 agy CLI）
    return {"claude": "Claude", "codex": "Codex", "antigravity": "Gemini"}.get(harness, harness)


# momo Slack 页：slack:<会话 ID>，thread 再加 :<thread_ts>
SOURCE_RE = re.compile(r"^slack:[CDG][A-Z0-9]{6,20}(:\d{9,11}\.\d{1,6})?$")


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
IMAGE_NOTE = "（图片，请打开看内容）"


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


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
        listing = "\n".join(f"- {path}{IMAGE_NOTE if is_image(path) else ''}" for path in attachments)
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
        self._drain_lock = asyncio.Lock()
        self._queue_tick: asyncio.Task | None = None

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
                or any(meta.status in ACTIVE_STATUSES or meta.status == QUEUED or meta.awaiting_reply
                       for meta in self.list_runs())
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

    def _weight(self, run: _Run) -> int:
        return 2 if run.meta.skill in self.config.heavy_skills else 1

    def slots_used(self) -> int:
        """活着的进程占的名额：会话没关（含空闲那几秒）或正在启动都算。"""
        return sum(self._weight(run) for run in self._runs.values() if run.session is not None or run.opening)

    def _has_room(self, run: _Run) -> bool:
        used = self.slots_used()
        if used == 0:
            return True  # 一个都没在跑时总能起一个（重活也行）
        if used + self._weight(run) > self.config.max_active:
            return False
        free = mem_available_mb()
        return free is None or free >= self.config.min_free_mb

    def queue_position(self, run_id: str) -> int | None:
        queued = sorted((r for r in self._runs.values() if r.meta.status == QUEUED), key=lambda r: r.meta.queued_at or 0)
        return next((i + 1 for i, r in enumerate(queued) if r.meta.id == run_id), None)

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

    def find_by_source(self, source: str) -> RunMeta | None:
        """同一个 Slack 会话 / thread 只配一个 agent：返回最新的那个。"""
        matches = [meta for meta in self.list_runs() if meta.source == source]
        return max(matches, key=lambda meta: meta.created_at) if matches else None

    def _slack_busy(self) -> bool:
        return any(
            run.meta.source.startswith("slack:") and (run.meta.status in ACTIVE_STATUSES or self._session_busy(run))
            for run in self._runs.values()
        )

    def create(self, skill: str, title: str, harness: str = "claude", auto_reply_s: int = 0,
               model: str | None = None, source: str = "") -> RunMeta:
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
        if source and not SOURCE_RE.match(source):
            raise RunnerError("source 格式不对")
        # 名额满了不拒绝：begin 时进队列，有空位自动开始
        # 服务器内存小：Slack 页自动启动的 agent 一次只跑一个，其余在页面上排队
        if source.startswith("slack:") and self._slack_busy():
            raise Busy("已有一个 Slack AI 在处理，排队中")
        meta = self.store.create(skill, title, harness, auto_reply_s, model=model, source=source)
        self._runs[meta.id] = _Run(meta=meta, seq=0)
        return meta

    async def begin(self, run_id: str, message: str, attachments: list[str]) -> RunMeta:
        run = self._get(run_id)
        if self._status_command(run, message, attachments):
            # 新对话第一句就是 /status：只回状态卡，不启动 agent；下一条消息才是真正的开头（仍走这里，带 skill 提示）
            return run.meta
        run.meta.begun = True
        self.store.save_meta(run.meta)
        prompt = build_prompt(run.meta.skill, message, attachments, run.meta.harness, self.config.shared_skills_dir)
        return await self._deliver(run, message, attachments, prompt)

    async def send_message(self, run_id: str, message: str, attachments: list[str], mode: str = "now") -> RunMeta:
        """mode="queue"：agent 正在干活时先挂起，这一轮结束再发；"now"：立刻发（运行中就是插话）。"""
        run = self._get(run_id)
        if not message.strip() and not attachments:
            raise RunnerError("消息不能为空")
        if self._status_command(run, message, attachments):
            return run.meta
        if not run.meta.begun:
            # 开头只发过 /status：这条才是第一条消息，标题也按它重起
            if run.meta.title.strip().lower() in STATUS_COMMANDS:
                run.meta.title = make_title(message, attachments)
            return await self.begin(run_id, message, attachments)
        if run.pending and not attachments:
            # 有提问挂着时，输入框里的话就是对提问的自由回答
            qid = next(iter(run.pending))
            self._emit(run, {"type": "user", "text": message, "files": []})
            self._resolve_question(run, qid, {"response": message})
            return run.meta
        if mode == "queue" and self._working(run):
            self._hold(run, message, attachments)
            return run.meta
        return await self._send_now(run, message, attachments)

    def _status_command(self, run: _Run, message: str, attachments: list[str]) -> bool:
        """页面自己的命令（/status）：直接回状态卡，不发给模型、不花额度，什么状态下都能用。处理了返回 True。"""
        if attachments or message.strip().lower() not in STATUS_COMMANDS:
            return False
        self._emit(run, {"type": "user", "text": message.strip(), "files": []})
        self._emit(run, {"type": "report", "title": "当前状态", "lines": self.status_lines(run)})
        return True

    def status_lines(self, run: _Run) -> list[str]:
        """/status 的内容：这个对话在哪个状态、用什么跑、服务器上名额和内存够不够。"""
        meta = run.meta
        label = {"running": "进行中", "waiting": "等你回答提问", "idle": "空闲", "error": "已中断", QUEUED: "排队中"}
        status = label.get(meta.status, meta.status)
        if meta.status == "idle" and (meta.awaiting_reply or meta.detached_questions):
            status = "等你确认"
        model = meta.actual_model or meta.model or "默认模型"
        if meta.model and meta.actual_model and meta.model != meta.actual_model:
            model = f"{meta.actual_model}（选的是 {meta.model}）"
        if run.session is not None:
            process = "在运行"
        elif meta.session_id:
            process = "已关闭（下次发消息按会话 ID 续接）"
        else:
            process = "还没启动"
        lines = [
            f"状态：{status}" + (f"（{meta.error}）" if meta.status == "error" and meta.error else ""),
            f"Agent：{meta.skill or '通用 Agent'} · {harness_label(meta.harness)} · {model}",
            f"会话 ID：{meta.session_id or '还没有'}",
            f"进程：{process}",
            f"名额：已用 {self.slots_used()}/{self.config.max_active}（这个对话占 {self._weight(run)} 个）",
        ]
        position = self.queue_position(meta.id)
        if position is not None:
            waiting = sum(1 for r in self._runs.values() if r.meta.status == QUEUED)
            lines.append(f"排队：第 {position} 位，共 {waiting} 个在排")
        if meta.held:
            lines.append(f"挂起的消息：{len(meta.held)} 条，这一轮结束后按顺序发")
        if meta.detached_questions:
            lines.append(f"没答的提问：{len(meta.detached_questions)} 个（进程已关，回答后续接）")
        if meta.auto_reply_s > 0:
            auto = f"自动继续：{wait_text(meta.auto_reply_s)}没回复就按建议继续，已用 {meta.auto_replies}/{AUTO_REPLY_LIMIT} 次"
            if meta.auto_reply_at:
                auto += "，下一次 " + time.strftime("%H:%M", time.localtime(meta.auto_reply_at))
            lines.append(auto)
        else:
            lines.append("自动继续：关闭")
        free = mem_available_mb()
        if free is not None:
            lines.append(f"服务器可用内存：{free} MB（低于 {self.config.min_free_mb} MB 新对话排队）")
        return lines

    def _working(self, run: _Run) -> bool:
        return run.meta.status in ACTIVE_STATUSES or run.meta.status == QUEUED or self._session_busy(run)

    async def _send_now(self, run: _Run, message: str, attachments: list[str]) -> RunMeta:
        run.interrupted = False
        prompt = build_prompt(None, message, attachments)
        if run.meta.detached_questions:
            # 进程已关的提问：这条消息就是回答，提问卡片随之收起
            for qid in list(run.meta.detached_questions):
                self._emit(run, {"type": "answer", "qid": qid, "response": message})
            prompt = "（回答你之前的提问）\n" + prompt
            run.meta.detached_questions = {}
            self.store.save_meta(run.meta)
        return await self._deliver(run, message, attachments, prompt)

    # ---- 挂起的消息：等这一轮结束再发，期间可以改、删、立刻发 ----

    def _emit_held(self, run: _Run) -> None:
        self.store.save_meta(run.meta)
        self._emit(run, {"type": "held", "items": list(run.meta.held)})

    def _hold(self, run: _Run, message: str, attachments: list[str]) -> None:
        run.meta.held.append({"id": uuid.uuid4().hex[:12], "text": message, "files": attachments, "created_at": time.time()})
        self._emit_held(run)

    def _find_held(self, run: _Run, hid: str) -> dict[str, Any]:
        item = next((h for h in run.meta.held if h.get("id") == hid), None)
        if item is None:
            raise NotFound("这条待发消息已经发出或删掉了")
        return item

    def edit_held(self, run_id: str, hid: str, text: str) -> RunMeta:
        run = self._get(run_id)
        item = self._find_held(run, hid)
        if not text.strip() and not item.get("files"):
            raise RunnerError("消息不能为空")
        item["text"] = text
        self._emit_held(run)
        return run.meta

    def delete_held(self, run_id: str, hid: str) -> RunMeta:
        run = self._get(run_id)
        item = self._find_held(run, hid)
        run.meta.held.remove(item)
        self._emit_held(run)
        return run.meta

    async def send_held(self, run_id: str, hid: str) -> RunMeta:
        """不等了，立刻发（agent 在干活时就是插话）。"""
        run = self._get(run_id)
        item = self._find_held(run, hid)
        run.meta.held.remove(item)
        self._emit_held(run)
        return await self._send_now(run, str(item.get("text") or ""), list(item.get("files") or []))

    async def _send_next_held(self, run: _Run) -> None:
        if not run.meta.held or self._working(run) or run.pending:
            return
        item = run.meta.held.pop(0)
        self._emit_held(run)
        try:
            await self._send_now(run, str(item.get("text") or ""), list(item.get("files") or []))
        except RunnerError:
            logger.exception("sending held message failed for run %s", run.meta.id)

    async def _deliver(self, run: _Run, message: str, attachments: list[str], prompt: str, *, echo: bool = True) -> RunMeta:
        with self.runtime_use():
            return await self._deliver_to_session(run, message, attachments, prompt, echo=echo)

    async def _deliver_to_session(
        self, run: _Run, message: str, attachments: list[str], prompt: str, *, echo: bool = True
    ) -> RunMeta:
        async with run.lock:
            if self._runs.get(run.meta.id) is not run:  # 排队时这个对话已被删除
                raise NotFound("运行不存在")
            if run.closing:
                try:
                    await self._close_session(run, strict=True)
                except Exception as exc:
                    raise SessionFailed(f"上次会话未能关闭，请稍后重试：{exc}") from exc
            # 先记下用户的话再起会话：起不来时页面上也能看到发了什么、为什么失败
            if echo:
                self._emit(run, {"type": "user", "text": message, "files": attachments})
            self._clear_awaiting(run)
            if run.session is None and (run.meta.status == QUEUED or not self._has_room(run)):
                self._enqueue(run, prompt)
                return run.meta
            await self._start_turn(run, prompt)
        return run.meta

    async def _start_turn(self, run: _Run, prompt: str) -> None:
        """持有 run.lock 时调用：需要就起进程，然后把这一轮发出去。"""
        run.last_text = ""
        if run.session is None:
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

    # ---- 排队 ----

    def _enqueue(self, run: _Run, prompt: str) -> None:
        # 排队时又发了一条：接在后面一起发
        run.meta.queued_prompt = f"{run.meta.queued_prompt}\n\n{prompt}" if run.meta.queued_prompt else prompt
        if run.meta.queued_at is None:
            run.meta.queued_at = time.time()
        first = run.meta.status != QUEUED
        self._set_status(run, QUEUED)
        self.store.save_meta(run.meta)
        if first:
            free = mem_available_mb()
            why = (f"服务器内存不够（剩 {free} MB）" if free is not None and free < self.config.min_free_mb
                   else f"同时最多跑 {self.config.max_active} 个")
            self._emit(run, {"type": "notice", "level": "info",
                             "text": f"{why}，排队中（第 {self.queue_position(run.meta.id)} 位），有空位会自动开始"})
        self._ensure_queue_tick()

    def _cancel_queue(self, run: _Run) -> bool:
        if run.meta.status != QUEUED:
            return False
        run.meta.queued_prompt = None
        run.meta.queued_at = None
        self._emit(run, {"type": "notice", "level": "info", "text": "已取消排队"})
        self._set_status(run, "idle")
        self.store.save_meta(run.meta)
        return True

    def _kick_queue(self) -> None:
        if any(run.meta.status == QUEUED for run in self._runs.values()):
            try:
                asyncio.get_running_loop().create_task(self.drain_queue())
            except RuntimeError:
                pass

    async def drain_queue(self) -> int:
        """按先来后到把能开始的排队对话发出去；排头的放不下就停（不插队）。"""
        started = 0
        async with self._drain_lock:
            while not self._runtime_maintenance:
                queued = sorted((r for r in self._runs.values() if r.meta.status == QUEUED),
                                key=lambda r: r.meta.queued_at or 0)
                if not queued or not self._has_room(queued[0]):
                    break
                run = queued[0]
                async with run.lock:
                    if run.meta.status != QUEUED or self._runs.get(run.meta.id) is not run:
                        continue
                    prompt = run.meta.queued_prompt or "继续"
                    run.meta.queued_prompt = None
                    run.meta.queued_at = None
                    self.store.save_meta(run.meta)
                    self._emit(run, {"type": "notice", "level": "info", "text": "排到了，开始"})
                    try:
                        with self.runtime_use():
                            await self._start_turn(run, prompt)
                    except Conflict:
                        break  # 正在更新运行工具：等更新完再排
                    except RunnerError:
                        logger.exception("queued run %s failed to start", run.meta.id)
                started += 1
        return started

    def _ensure_queue_tick(self) -> None:
        """内存回来了也要能开始：有人排队时每 15 秒看一眼。"""
        if self._queue_tick is not None and not self._queue_tick.done():
            return
        try:
            self._queue_tick = asyncio.get_running_loop().create_task(self._queue_loop())
        except RuntimeError:
            self._queue_tick = None

    async def _queue_loop(self) -> None:
        while any(run.meta.status == QUEUED for run in self._runs.values()):
            await asyncio.sleep(15)
            try:
                await self.drain_queue()
            except Exception:  # noqa: BLE001
                logger.exception("drain queue failed")

    def resume_queue(self) -> int:
        """服务启动时调用（在事件循环里）：重启前排着的对话接着排。"""
        count = 0
        for meta in self.store.list_meta():
            if meta.status == QUEUED:
                self._get(meta.id)
                count += 1
        if count:
            self._ensure_queue_tick()
            self._kick_queue()
        return count

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
        run.opening = True
        try:
            session = await self.session_factory(spec)
        except Exception as exc:  # noqa: BLE001
            logger.exception("failed to open session for run %s", run.meta.id)
            label = harness_label(run.meta.harness)
            self._emit(run, {"type": "error", "text": f"启动 {label} 失败：{exc}"})
            self._set_status(run, "error", f"启动 {label} 失败：{exc}")
            raise SessionFailed(str(exc)) from exc
        finally:
            run.opening = False
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
                run.meta.awaiting_reply = not event.get("is_error") and awaits_reply(run.last_text)
                self._set_status(run, "idle")
                self.store.save_meta(run.meta)
                self._schedule_idle(run)
                if run.meta.held and not event.get("is_error") and not run.interrupted and not self._session_busy(run):
                    # 正常结束一轮：挂起的消息接着发（等确认时它就是回复，不再排自动继续）
                    asyncio.get_running_loop().create_task(self._send_next_held(run))
                elif run.meta.awaiting_reply:
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
                self._schedule_detach(run)
            try:
                return await future
            finally:
                run.pending.pop(qid, None)
                # 脱离进程的提问（见 _detach_later）还算挂着：不取消自动回复、不改状态
                detached = qid in run.meta.detached_questions
                if not run.pending and not detached:
                    self._cancel_auto_reply(run)
                    self._cancel_detach(run)
                if not run.pending and run.meta.status == "waiting" and not detached:
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

    async def answer(
        self,
        run_id: str,
        qid: str,
        answers: dict[str, Any] | None = None,
        response: str | None = None,
    ) -> RunMeta:
        run = self._get(run_id)
        detached = qid in run.meta.detached_questions
        if qid not in run.pending and not detached:
            raise Conflict("这个提问已经回答过或已失效")
        payload: dict[str, Any] = {}
        if answers:
            payload["answers"] = answers
        if response:
            payload["response"] = response
        if not payload:
            raise RunnerError("回答不能为空")
        if detached:
            await self._answer_detached(run, qid, payload)
        else:
            self._resolve_question(run, qid, payload)
        return run.meta

    async def _answer_detached(self, run: _Run, qid: str, payload: dict[str, Any]) -> None:
        """进程已关的提问：记下回答，把回答作为新消息发出去（按会话 ID 续接）。"""
        questions = {qid: run.meta.detached_questions.pop(qid)}
        self.store.save_meta(run.meta)
        self._emit(run, {"type": "answer", "qid": qid, **payload})
        if run.meta.detached_questions:
            return  # 同一轮还有别的问题没答：答完再一起续
        text = answer_text(questions, payload.get("answers"), payload.get("response"))
        await self._deliver(run, text, [], text, echo=False)

    # ---- 提问挂太久：脱离进程 ----

    def _schedule_detach(self, run: _Run) -> None:
        self._cancel_detach(run)
        if self.config.question_detach_s > 0:
            run.detach_task = asyncio.create_task(self._detach_later(run))

    def _cancel_detach(self, run: _Run) -> None:
        if run.detach_task is not None and run.detach_task is not asyncio.current_task():
            run.detach_task.cancel()
        run.detach_task = None

    async def _detach_later(self, run: _Run) -> None:
        await asyncio.sleep(self.config.question_detach_s)
        run.detach_task = None
        if not run.pending or run.session is None:
            return
        async with run.lock:
            if not run.pending or run.session is None:
                return
            run.meta.detached_questions = {qid: p.questions for qid, p in run.pending.items()}
            # 先标成关闭中：拒绝提问后 agent 收尾的事件不再推给页面
            run.closing = True
            for pending in list(run.pending.values()):
                if not pending.future.done():
                    pending.future.set_result(PermissionOutcome(allow=False, message=DETACH_MESSAGE, interrupt=True))
            await self._close_session(run)
            run.pending.clear()
            run.meta.awaiting_reply = True
            self.store.save_meta(run.meta)
            self._emit(run, {"type": "notice", "level": "info",
                             "text": f"{wait_text(self.config.question_detach_s)}没回答，先关掉进程省内存；问题还在，回答后接着做"})
            self._set_status(run, "idle")

    def _resolve_question(self, run: _Run, qid: str, payload: dict[str, Any]) -> None:
        pending = run.pending[qid]
        self._emit(run, {"type": "answer", "qid": qid, **payload})
        if not pending.future.done():
            pending.future.set_result(
                PermissionOutcome(allow=True, updated_input={"questions": pending.questions, **payload})
            )

    async def interrupt(self, run_id: str) -> RunMeta:
        run = self._get(run_id)
        run.interrupted = True  # 停下后挂起的消息不自动发，留着让用户决定
        if self._cancel_queue(run):
            return run.meta
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
            self._cancel_queue(run)
            self._clear_awaiting(run)
            self._cancel_detach(run)
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
        # 关会话到归档整段持有 run.lock：期间到的消息排在后面，不会把会话重新打开
        async with run.lock:
            if self._runs.get(run_id) is not run:  # 排队时另一个删除请求已经删完了
                raise NotFound("运行不存在")
            if run.meta.status in ACTIVE_STATUSES or self._session_busy(run):
                raise Conflict("任务还在运行，先中断再删除")
            self._cancel_auto_reply(run)
            self._cancel_detach(run)
            try:
                await self._close_session(run, strict=True)
            except Exception as exc:
                raise SessionFailed(f"会话未能关闭，暂时无法删除：{exc}") from exc
            for queue in list(run.subscribers):
                queue.put_nowait(None)
            self._runs.pop(run_id, None)
            await asyncio.to_thread(self.store.archive, run_id, reason=reason, client_ip=client_ip)

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
            if run.meta.detached_questions and not run.pending:
                self._emit(run, {"type": "notice", "level": "info", "text": f"{waited}没有回答，已自动选推荐选项"})
                for qid, questions in list(run.meta.detached_questions.items()):
                    answers = {str(q.get("question", "")): recommended_answer(q) for q in questions or []}
                    try:
                        await self._answer_detached(run, qid, {"answers": answers})
                    except RunnerError:
                        logger.exception("auto reply failed for run %s", run.meta.id)
                return
            if run.pending:
                for qid, pending in list(run.pending.items()):
                    answers = {str(q.get("question", "")): recommended_answer(q) for q in pending.questions}
                    self._emit(run, {"type": "notice", "level": "info", "text": f"{waited}没有回答，已自动选推荐选项"})
                    self._resolve_question(run, qid, {"answers": answers})
                return
            if run.meta.status != "idle" or not run.meta.awaiting_reply:
                return
            self._emit(run, {"type": "notice", "level": "info", "text": f"{waited}没有回复，自动按推荐方案继续"})
            try:
                await self._deliver(run, AUTO_REPLY_TEXT, [], AUTO_REPLY_TEXT)
            except RunnerError:
                logger.exception("auto reply failed for run %s", run.meta.id)
        finally:
            if run.auto_task is task:
                run.auto_task = None

    def resume_auto_replies(self) -> int:
        """服务启动时调用（在事件循环里）：重启前排着的自动回复接着排，时间照旧。"""
        resumed = 0
        for meta in self.store.list_meta():
            if meta.status == "idle" and (meta.awaiting_reply or meta.detached_questions) and meta.auto_reply_at is not None:
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
        # 腾出了名额：排队的接着开始
        self._kick_queue()

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
            if meta.status == "waiting":
                # 挂着的提问还能答：存成脱离进程的提问，回答时续接
                questions = self._unanswered_questions(meta.id)
                if questions and meta.session_id:
                    run = self._get(meta.id)
                    run.meta.detached_questions = questions
                    run.meta.awaiting_reply = True
                    self.store.save_meta(run.meta)
                    self._emit(run, {"type": "notice", "level": "info", "text": "服务重启过，问题还在，回答后接着做"})
                    self._set_status(run, "idle")
                    recovered += 1
                    continue
            if meta.status in ACTIVE_STATUSES:
                run = self._get(meta.id)
                message = "服务重启导致任务中断，发送一条消息（比如「继续」）即可从断点接着跑"
                self._emit(run, {"type": "error", "text": message})
                self._set_status(run, "error", message)
                recovered += 1
        return recovered

    def _unanswered_questions(self, run_id: str) -> dict[str, Any]:
        asked: dict[str, Any] = {}
        for event in self.store.read_events(run_id, 0):
            if event.get("type") == "question" and event.get("qid"):
                asked[event["qid"]] = event.get("questions") or []
            elif event.get("type") == "answer":
                asked.pop(event.get("qid"), None)
        return asked

    async def shutdown(self) -> None:
        if self._queue_tick is not None:
            self._queue_tick.cancel()
        for run in list(self._runs.values()):
            self._cancel_detach(run)
            if run.auto_task is not None:
                run.auto_task.cancel()  # 不清 auto_reply_at：重启后 resume_auto_replies 接着排
            if run.session is not None:
                await self._close_session(run)
            for queue in list(run.subscribers):
                queue.put_nowait(None)
