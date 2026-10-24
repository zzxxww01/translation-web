"""唯一 import claude_agent_sdk 的模块：建会话、把 SDK 消息映射成页面事件。

runner 只依赖这里实现的 AgentSession 协议，测试时用假会话替换，不需要装 SDK。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    RateLimitEvent,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from .config import Config
from .runner import SessionSpec

logger = logging.getLogger(__name__)

TOOL_RESULT_LIMIT = 2000
SUMMARY_LIMIT = 200

APPEND_SYSTEM_PROMPT = """\
你运行在 momo 的 Claude 页里。用户只能在网页上看到你的文字回复、工具调用摘要和当前目录里的文件，看不到终端。
- 用户可能指定了 skill，也可能只是直接找你对话。直接对话时正常回答；任务明显对得上某个已安装的 skill 时再用它。
- 当前工作目录就是本次运行的目录，用户上传的文件在 input/ 下。所有产出都写在当前目录内，用户可以在网页上下载。
- 需要用户做选择或确认时，优先用 AskUserQuestion 工具（会变成网页上的按钮）。要用户审阅的内容（术语表、稿件、字幕）必须先在回复正文里用 Markdown 完整展示，再提问或结束本轮等用户回复；不要只把内容写进文件或塞进提问里。
- 多步骤的任务用任务清单工具列出步骤并随进度更新，网页侧栏会显示进度。
"""

SANDBOX_NOTE = """- Bash 在沙箱里运行：只能写当前目录和少数白名单路径，网络只放行必要的域名。被拦截时如实告诉用户原因，不要尝试绕过沙箱。
"""

NO_SANDBOX_NOTE = """- 命令直接在服务器上执行，没有沙箱。这台服务器还跑着线上服务：除非用户要求或 skill 的说明需要，不要改动当前目录以外的文件，不要装系统级软件或重启服务。
"""


def build_system_prompt(config: Config) -> str:
    return APPEND_SYSTEM_PROMPT + (SANDBOX_NOTE if config.sandbox else NO_SANDBOX_NOTE)


def build_settings(config: Config, spec: SessionSpec) -> dict[str, Any]:
    if not config.sandbox:
        return {}
    return {
        "sandbox": {
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            # 不许模型用 dangerouslyDisableSandbox 绕出去；确需沙箱外运行的命令走 excludedCommands
            "allowUnsandboxedCommands": False,
            # 沙箱起不来（缺 bubblewrap/socat）时直接失败，而不是静默在沙箱外跑
            "failIfUnavailable": True,
            "excludedCommands": list(config.unsandboxed_commands),
            "filesystem": {
                "allowWrite": [str(spec.cwd), *(str(p) for p in config.extra_write)],
                "denyRead": ["~/.ssh", "~/.config/skill-runner"],
            },
            "network": {"allowedDomains": list(config.allowed_domains)},
        }
    }


def build_options(config: Config, spec: SessionSpec) -> ClaudeAgentOptions:
    async def can_use_tool(
        tool_name: str, tool_input: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        reason = context.title or context.decision_reason or context.blocked_path
        outcome = await spec.on_permission(tool_name, tool_input, context.tool_use_id, reason)
        if outcome.allow:
            updated = outcome.updated_input if outcome.updated_input is not None else tool_input
            return PermissionResultAllow(updated_input=updated)
        return PermissionResultDeny(message=outcome.message, interrupt=outcome.interrupt)

    settings = build_settings(config, spec)
    return ClaudeAgentOptions(
        cwd=str(spec.cwd),
        resume=spec.resume,
        # 只加载服务用户的 ~/.claude（skills、settings）；运行目录里不会有项目级配置
        setting_sources=["user"],
        permission_mode="default",
        can_use_tool=can_use_tool,
        system_prompt={"type": "preset", "preset": "claude_code", "append": build_system_prompt(config)},
        settings=json.dumps(settings, ensure_ascii=False) if settings else None,
        model=config.model,
        # 新模型默认不带任务清单工具，要显式打开，网页侧栏的进度才有数据（Python 的 env 是叠加在继承环境上的）
        env={"CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"},
        stderr=lambda line: logger.info("[claude %s] %s", spec.run_id, line.rstrip()),
    )


class SdkSession:
    def __init__(self, client: ClaudeSDKClient, cwd: str | None = None):
        self._client = client
        self._cwd = cwd

    @classmethod
    async def open(cls, config: Config, spec: SessionSpec) -> "SdkSession":
        client = ClaudeSDKClient(options=build_options(config, spec))
        await client.connect()
        return cls(client, str(spec.cwd))

    async def send(self, text: str) -> None:
        await self._client.query(text)

    async def interrupt(self) -> None:
        await self._client.interrupt()

    async def close(self) -> None:
        await self._client.disconnect()

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        mapper = MessageMapper(self._cwd)
        async for message in self._client.receive_messages():
            for event in mapper.map(message):
                yield event


def make_factory(config: Config):
    async def factory(spec: SessionSpec) -> SdkSession:
        return await SdkSession.open(config, spec)

    return factory


# ---- 消息映射 ----


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"…（共 {len(text)} 字，已截断）"


def _relative(path: str, cwd: str | None) -> str:
    """运行目录下的路径显示成相对路径，页面上不用看一长串临时目录前缀。"""
    if not cwd:
        return path
    for sep in ("/", "\\"):
        prefix = cwd.rstrip("/\\") + sep
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


def summarize_tool(name: str, data: dict[str, Any], cwd: str | None = None) -> str:
    if name == "Bash":
        return str(data.get("description") or data.get("command") or "")[:SUMMARY_LIMIT]
    for key in ("file_path", "notebook_path", "pattern", "url", "query", "skill", "description", "subject"):
        value = data.get(key)
        if isinstance(value, str) and value:
            if key in ("file_path", "notebook_path"):
                value = _relative(value, cwd)
            return value[:SUMMARY_LIMIT]
    return json.dumps(data, ensure_ascii=False)[:SUMMARY_LIMIT]


def _tool_result_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(f"[{item.get('type', 'content')}]")
    return "\n".join(parts)


def _todos(data: dict[str, Any]) -> list[dict[str, str]]:
    items = []
    for todo in data.get("todos") or []:
        if isinstance(todo, dict):
            items.append({
                "content": str(todo.get("content") or todo.get("subject") or ""),
                "status": str(todo.get("status") or "pending"),
            })
    return items


# 进度清单有两套工具：TodoWrite 每次给全量；TaskCreate/TaskUpdate 是增量，要自己记状态。
# 用哪套取决于 Claude Code 的运行环境，所以两套都认。它们和 AskUserQuestion 一样不进工具流。
TASK_TOOLS = {"TaskCreate", "TaskUpdate", "TaskList", "TaskGet"}
_TASK_ID_RE = re.compile(r"#(\w+)")


def _rate_limit_text(info: Any) -> str:
    kind = {"five_hour": "5 小时", "seven_day": "7 天", "seven_day_opus": "7 天（Opus）",
            "seven_day_sonnet": "7 天（Sonnet）", "overage": "超额"}.get(info.rate_limit_type or "", "")
    parts = [f"{kind}额度" if kind else "额度"]
    if info.utilization is not None:
        parts.append(f"已用 {info.utilization:.0%}")
    if info.resets_at:
        parts.append(f"{datetime.fromtimestamp(info.resets_at):%m-%d %H:%M} 重置")
    head = "额度已用尽" if info.status == "rejected" else "额度提醒"
    return f"{head}：" + "，".join(parts)


class MessageMapper:
    """把一个会话的 SDK 消息流映射成页面事件。有状态：要记住哪些工具结果不展示、任务清单的当前内容。"""

    def __init__(self, cwd: str | None = None) -> None:
        self._cwd = cwd
        self._hidden: set[str] = set()
        self._tasks: dict[str, dict[str, str]] = {}
        self._creating: dict[str, str] = {}

    def _task_snapshot(self) -> dict[str, Any]:
        return {"type": "todos", "items": list(self._tasks.values())}

    def _on_tool_use(self, block: ToolUseBlock, parent: str | None) -> list[dict[str, Any]]:
        if block.name == "AskUserQuestion":
            self._hidden.add(block.id)
            return []  # 提问由权限回调发 question 事件
        if block.name == "TodoWrite":
            self._hidden.add(block.id)
            return [{"type": "todos", "items": _todos(block.input)}]
        if block.name in TASK_TOOLS:
            self._hidden.add(block.id)
            if block.name == "TaskCreate":
                # 任务编号要等工具结果才知道
                self._creating[block.id] = str(block.input.get("subject") or block.input.get("description") or "")
                return []
            if block.name == "TaskUpdate":
                # 流里是模型原样输出的参数，键名可能是 taskId / id / task_id（执行前才会被纠正）
                task_id = str(block.input.get("taskId") or block.input.get("id") or block.input.get("task_id") or "")
                status = str(block.input.get("status") or "")
                if status == "deleted":
                    self._tasks.pop(task_id, None)
                elif task_id in self._tasks:
                    if status:
                        self._tasks[task_id]["status"] = status
                    if block.input.get("subject"):
                        self._tasks[task_id]["content"] = str(block.input["subject"])
                else:
                    return []
                return [self._task_snapshot()]
            return []
        return [{
            "type": "tool",
            "id": block.id,
            "name": block.name,
            "summary": summarize_tool(block.name, block.input, self._cwd),
            "parent": parent,
        }]

    def _on_tool_result(
        self, block: ToolResultBlock, parent: str | None, structured: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if block.tool_use_id in self._creating:
            subject = self._creating.pop(block.tool_use_id)
            if block.is_error:
                return []
            # 编号优先取结构化输出 {"task": {"id": ...}}，取不到再从结果文字里找 #N
            task = (structured or {}).get("task") or {}
            task_id = str(task.get("id") or "")
            if not task_id:
                match = _TASK_ID_RE.search(_tool_result_text(block.content))
                task_id = match.group(1) if match else block.tool_use_id
            self._tasks[task_id] = {"content": subject, "status": "pending"}
            return [self._task_snapshot()]
        if block.tool_use_id in self._hidden:
            return []
        return [{
            "type": "tool_result",
            "id": block.tool_use_id,
            "ok": not block.is_error,
            "text": _clip(_tool_result_text(block.content), TOOL_RESULT_LIMIT),
            "parent": parent,
        }]

    def map(self, message: Any) -> list[dict[str, Any]]:
        if isinstance(message, AssistantMessage):
            parent = message.parent_tool_use_id
            events: list[dict[str, Any]] = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    # 子代理的文字默认不转发；这里只会是主对话的文字
                    if block.text.strip():
                        events.append({"type": "text", "text": block.text, "parent": parent})
                elif isinstance(block, ToolUseBlock):
                    events.extend(self._on_tool_use(block, parent))
            if message.error:
                events.append({"type": "notice", "level": "error", "text": f"Claude 返回错误：{message.error}"})
            return events
        if isinstance(message, UserMessage):
            if isinstance(message.content, str):
                return []  # 用户提示词回显、skill 展开内容，页面上已有 user 事件
            events = []
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    events.extend(self._on_tool_result(block, message.parent_tool_use_id, message.tool_use_result))
            return events
        return map_message(message)


def map_message(message: Any) -> list[dict[str, Any]]:
    """无状态部分：结果、系统消息、额度事件。"""
    if isinstance(message, ResultMessage):
        return [{
            "type": "result",
            "session_id": message.session_id,
            "is_error": message.is_error,
            "subtype": message.subtype,
            "duration_ms": message.duration_ms,
            "num_turns": message.num_turns,
            "errors": message.errors or [],
        }]
    if isinstance(message, RateLimitEvent):
        info = message.rate_limit_info
        if info.status == "allowed":
            return []
        level = "error" if info.status == "rejected" else "warn"
        return [{"type": "notice", "level": level, "text": _rate_limit_text(info)}]
    if isinstance(message, SystemMessage):
        if message.subtype == "init":
            return [{
                "type": "session",
                "session_id": message.data.get("session_id"),
                "model": message.data.get("model"),
            }]
        if message.subtype == "compact_boundary":
            return [{"type": "notice", "level": "info", "text": "对话较长，Claude 已压缩上下文"}]
        if message.subtype == "api_retry":
            attempt = message.data.get("attempt")
            return [{"type": "notice", "level": "warn", "text": f"Claude API 暂时出错，正在第 {attempt} 次重试"}]
    return []
