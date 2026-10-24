"""SDK 消息到页面事件的映射。CI 不装 claude-agent-sdk，这组测试在那里自动跳过。"""

import json
from pathlib import Path

import pytest

sdk = pytest.importorskip("claude_agent_sdk")

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    RateLimitEvent,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from claude_agent_sdk.types import (  # noqa: E402
    PermissionResultAllow,
    PermissionResultDeny,
    RateLimitInfo,
    ToolPermissionContext,
)

from skill_runner.runner import PermissionOutcome, SessionSpec  # noqa: E402
from skill_runner.sdk_session import MessageMapper, build_options, build_settings  # noqa: E402

from skill_runner_fakes import make_config  # noqa: E402


def map_message(message):
    return MessageMapper().map(message)


def _result(tool_use_id, text, is_error=False):
    return UserMessage(content=[ToolResultBlock(tool_use_id, text, is_error=is_error)])


def test_assistant_blocks_become_text_tool_and_todo_events():
    message = AssistantMessage(
        content=[
            TextBlock("术语表如下"),
            TextBlock("   "),
            ToolUseBlock("t1", "Bash", {"command": "python qa_check.py zh.md", "description": "跑 QA"}),
            ToolUseBlock("t2", "AskUserQuestion", {"questions": []}),
            ToolUseBlock("t3", "TodoWrite", {"todos": [{"content": "翻译", "status": "in_progress", "activeForm": "翻译中"}]}),
            ToolUseBlock("t4", "Read", {"file_path": "input/a.html"}),
        ],
        model="m",
        parent_tool_use_id=None,
    )
    assert map_message(message) == [
        {"type": "text", "text": "术语表如下", "parent": None},
        {"type": "tool", "id": "t1", "name": "Bash", "summary": "跑 QA", "parent": None},
        {"type": "todos", "items": [{"content": "翻译", "status": "in_progress"}]},
        {"type": "tool", "id": "t4", "name": "Read", "summary": "input/a.html", "parent": None},
    ]


def test_results_of_question_and_todo_tools_are_hidden():
    mapper = MessageMapper()
    mapper.map(AssistantMessage(content=[
        ToolUseBlock("q1", "AskUserQuestion", {"questions": []}),
        ToolUseBlock("w1", "TodoWrite", {"todos": []}),
        ToolUseBlock("r1", "Read", {"file_path": "a"}),
    ], model="m"))
    events = mapper.map(UserMessage(content=[
        ToolResultBlock("q1", 'Your questions have been answered: "x"="甲"'),
        ToolResultBlock("w1", "Todos have been modified"),
        ToolResultBlock("r1", "file body"),
    ]))
    assert [e["id"] for e in events] == ["r1"]


def test_incremental_task_tools_build_the_progress_list():
    mapper = MessageMapper()
    use = lambda *blocks: mapper.map(AssistantMessage(content=list(blocks), model="m"))  # noqa: E731
    assert use(ToolUseBlock("c1", "TaskCreate", {"subject": "理解原文"}), ToolUseBlock("c2", "TaskCreate", {"subject": "术语确认"})) == []
    mapper.map(_result("c1", "Task #1 created successfully: 理解原文"))
    [snapshot] = mapper.map(_result("c2", "Task #2 created successfully: 术语确认"))
    assert snapshot == {"type": "todos", "items": [
        {"content": "理解原文", "status": "pending"},
        {"content": "术语确认", "status": "pending"},
    ]}
    [updated] = use(ToolUseBlock("u1", "TaskUpdate", {"taskId": "1", "status": "completed"}))
    assert updated["items"][0]["status"] == "completed"
    [deleted] = use(ToolUseBlock("u2", "TaskUpdate", {"taskId": "2", "status": "deleted"}))
    assert deleted["items"] == [{"content": "理解原文", "status": "completed"}]
    assert use(ToolUseBlock("u3", "TaskUpdate", {"taskId": "99", "status": "completed"})) == []
    assert mapper.map(_result("u1", "Updated task #1")) == []
    assert use(ToolUseBlock("c3", "TaskCreate", {"subject": "失败的"})) == []
    assert mapper.map(_result("c3", "error", is_error=True)) == []
    # 编号优先取结构化输出；更新时模型可能把 taskId 写成 id
    assert use(ToolUseBlock("c4", "TaskCreate", {"subject": "翻译"})) == []
    [created] = mapper.map(UserMessage(
        content=[ToolResultBlock("c4", "Task created")],
        tool_use_result={"task": {"id": "t-9", "subject": "翻译"}},
    ))
    assert created["items"][-1] == {"content": "翻译", "status": "pending"}
    [moved] = use(ToolUseBlock("u4", "TaskUpdate", {"id": "t-9", "status": "in_progress"}))
    assert moved["items"][-1]["status"] == "in_progress"


def test_tool_summaries_show_paths_relative_to_run_dir():
    mapper = MessageMapper("/home/zxw/skill-runner/runs/r1")
    [read, outside] = mapper.map(AssistantMessage(content=[
        ToolUseBlock("a", "Read", {"file_path": "/home/zxw/skill-runner/runs/r1/input/a.html"}),
        ToolUseBlock("b", "Read", {"file_path": "/home/zxw/.claude/skills/x/SKILL.md"}),
    ], model="m"))
    assert read["summary"] == "input/a.html"
    assert outside["summary"] == "/home/zxw/.claude/skills/x/SKILL.md"
    win = MessageMapper(r"C:\tmp\runs\r1").map(AssistantMessage(
        content=[ToolUseBlock("c", "Write", {"file_path": r"C:\tmp\runs\r1\out\zh.md"})], model="m"))
    assert win[0]["summary"] == r"out\zh.md"


def test_subagent_tool_calls_carry_parent_and_results_are_clipped():
    use = AssistantMessage(content=[ToolUseBlock("c1", "Write", {"file_path": "chunks/1.md"})], model="m", parent_tool_use_id="agent-1")
    assert map_message(use)[0]["parent"] == "agent-1"
    long_text = "字" * 5000
    result = UserMessage(
        content=[ToolResultBlock("c1", [{"type": "text", "text": long_text}, {"type": "image"}], is_error=True)],
        parent_tool_use_id="agent-1",
    )
    [event] = map_message(result)
    assert event["type"] == "tool_result" and event["ok"] is False and event["parent"] == "agent-1"
    assert event["text"].startswith("字" * 2000) and "已截断" in event["text"]
    assert map_message(UserMessage(content="/four-step-translate 展开的 skill 内容")) == []


def test_result_init_and_rate_limit_events():
    result = ResultMessage(subtype="success", duration_ms=10, duration_api_ms=5, is_error=False, num_turns=3, session_id="s1")
    assert map_message(result) == [{
        "type": "result", "session_id": "s1", "is_error": False, "subtype": "success",
        "duration_ms": 10, "num_turns": 3, "errors": [],
    }]
    init = SystemMessage(subtype="init", data={"session_id": "s1", "model": "claude-x"})
    assert map_message(init) == [{"type": "session", "session_id": "s1", "model": "claude-x"}]
    assert map_message(SystemMessage(subtype="task_started", data={})) == []
    ok = RateLimitEvent(rate_limit_info=RateLimitInfo(status="allowed"), uuid="u", session_id="s")
    assert map_message(ok) == []
    warn = RateLimitEvent(
        rate_limit_info=RateLimitInfo(status="allowed_warning", rate_limit_type="five_hour", utilization=0.85),
        uuid="u",
        session_id="s",
    )
    [notice] = map_message(warn)
    assert notice["level"] == "warn" and "5 小时额度" in notice["text"] and "85%" in notice["text"]


def _spec(tmp_path, outcome):
    async def on_permission(name, data, tool_use_id, reason=None):
        on_permission.calls.append((name, data, tool_use_id, reason))
        return outcome

    on_permission.calls = []
    return SessionSpec(run_id="r", cwd=tmp_path, resume="sess-1", on_permission=on_permission)


def test_settings_enable_strict_sandbox_with_run_dir_and_whitelist(tmp_path):
    config = make_config(tmp_path, extra_write=(Path("/srv/glossary.json"),), unsandboxed_commands=("python tts.py *",))
    sandbox = build_settings(config, _spec(tmp_path, PermissionOutcome(True)))["sandbox"]
    assert sandbox["enabled"] and sandbox["failIfUnavailable"] and not sandbox["allowUnsandboxedCommands"]
    assert sandbox["filesystem"]["allowWrite"] == [str(tmp_path), str(Path("/srv/glossary.json"))]
    assert sandbox["excludedCommands"] == ["python tts.py *"]
    assert "generativelanguage.googleapis.com" in sandbox["network"]["allowedDomains"]
    assert build_settings(make_config(tmp_path, sandbox=False), _spec(tmp_path, PermissionOutcome(True))) == {}


async def test_options_load_user_skills_and_route_permissions(tmp_path):
    spec = _spec(tmp_path, PermissionOutcome(True, updated_input={"answers": {"q": "a"}}))
    options = build_options(make_config(tmp_path), spec)
    assert options.setting_sources == ["user"]
    assert options.permission_mode == "default"
    assert options.env == {"CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"}
    assert options.cwd == str(tmp_path) and options.resume == "sess-1"
    assert json.loads(options.settings)["sandbox"]["enabled"] is True
    assert "momo" in options.system_prompt["append"]

    context = ToolPermissionContext(tool_use_id="tu-1")
    allowed = await options.can_use_tool("AskUserQuestion", {"questions": []}, context)
    assert isinstance(allowed, PermissionResultAllow) and allowed.updated_input == {"answers": {"q": "a"}}
    assert spec.on_permission.calls == [("AskUserQuestion", {"questions": []}, "tu-1", None)]

    # Claude Code 给的请求原因（如要访问哪个域名）原样传给 runner
    await options.can_use_tool("Bash", {"command": "curl x"}, ToolPermissionContext(tool_use_id="tu-2", title="Claude wants to access pypi.org"))
    assert spec.on_permission.calls[-1][3] == "Claude wants to access pypi.org"

    passthrough = build_options(make_config(tmp_path), _spec(tmp_path, PermissionOutcome(True)))
    same = await passthrough.can_use_tool("Read", {"file_path": "a"}, context)
    assert same.updated_input == {"file_path": "a"}

    denying = build_options(make_config(tmp_path), _spec(tmp_path, PermissionOutcome(False, message="不行", interrupt=True)))
    denied = await denying.can_use_tool("Write", {"file_path": "/etc/x"}, context)
    assert isinstance(denied, PermissionResultDeny) and denied.message == "不行" and denied.interrupt
