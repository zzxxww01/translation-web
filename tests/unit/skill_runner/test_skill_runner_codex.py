import asyncio
import json
import sys
import textwrap

import pytest

from skill_runner.codex_session import CodexMapper, CodexSession, build_command, latest_model
from skill_runner.runner import Runner, RunnerError, SessionSpec, build_prompt
from skill_runner.store import RunStore

from skill_runner_fakes import FakeFactory, make_config

# 2026-10-25 服务器上 codex-cli 0.164.0 `codex exec --json` 的真实输出
REAL_EVENTS = [
    {"type": "thread.started", "thread_id": "01a1735c-1056-78c2-a965-d3fa546bc716"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "我现在执行该命令。"}},
    {"type": "item.started", "item": {"id": "item_1", "type": "command_execution", "command": "/bin/bash -lc 'echo hi > a.txt'",
                                      "aggregated_output": "", "exit_code": None, "status": "in_progress"}},
    {"type": "item.completed", "item": {"id": "item_1", "type": "command_execution", "command": "/bin/bash -lc 'echo hi > a.txt'",
                                        "aggregated_output": "", "exit_code": 0, "status": "completed"}},
    {"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": "完成"}},
    {"type": "turn.completed", "usage": {"input_tokens": 27948, "output_tokens": 78}},
]


def test_real_codex_events_map_to_page_events():
    mapper = CodexMapper()
    events = [mapped for event in REAL_EVENTS for mapped in mapper.map(event)]
    assert [e["type"] for e in events] == ["session", "text", "tool", "tool_result", "text", "result"]
    assert events[0]["session_id"] == "01a1735c-1056-78c2-a965-d3fa546bc716"
    assert events[2]["name"] == "Bash" and events[2]["summary"] == "echo hi > a.txt"
    assert events[3]["ok"] is True and events[3]["id"] == events[2]["id"]
    assert events[-1]["session_id"] == mapper.thread_id and events[-1]["is_error"] is False


def test_failed_turns_and_todo_lists_are_shown():
    mapper = CodexMapper()
    todo = mapper.map({"type": "item.updated", "item": {"id": "t", "type": "todo_list",
                                                       "items": [{"text": "转写", "completed": True}, {"text": "翻译", "completed": False}]}})
    assert todo == [{"type": "todos", "items": [{"content": "转写", "status": "completed"}, {"content": "翻译", "status": "pending"}]}]
    failed = mapper.map({"type": "turn.failed", "error": {"message": "usage limit"}})
    assert failed[0]["level"] == "error" and failed[1]["is_error"] is True
    command = mapper.map({"type": "item.completed", "item": {"id": "c", "type": "command_execution", "command": "ls nope",
                                                            "aggregated_output": "No such file", "exit_code": 2, "status": "failed"}})
    assert [e["type"] for e in command] == ["tool", "tool_result"] and command[1]["ok"] is False


def test_latest_model_is_the_top_listed_one(tmp_path):
    (tmp_path / "models_cache.json").write_text(json.dumps({"models": [
        {"slug": "gpt-5.6-sol", "visibility": "list", "priority": 6},
        {"slug": "gpt-reserve", "visibility": "hide", "priority": 0},
        {"slug": "gpt-6.1-sol", "visibility": "list", "priority": 1},
    ]}), encoding="utf-8")
    assert latest_model(tmp_path) == "gpt-6.1-sol"
    assert latest_model(tmp_path / "missing") is None


def test_command_skips_confirmations_and_resumes_by_thread(tmp_path):
    config = make_config(tmp_path, sandbox=False, codex_model="gpt-6.1-sol")
    first = build_command(config, None)
    assert first[:2] == ["codex", "exec"] and "--dangerously-bypass-approvals-and-sandbox" in first
    assert first[-1] == "-" and first[first.index("-m") + 1] == "gpt-6.1-sol"
    again = build_command(config, "thread-1")
    assert again[1:3] == ["exec", "resume"] and again[-2:] == ["thread-1", "-"]


def test_codex_skill_prompt_points_at_the_shared_skill(tmp_path):
    prompt = build_prompt("four-step-translate", "精翻这篇", [], "codex", tmp_path / "skills")
    assert str(tmp_path / "skills" / "four-step-translate" / "SKILL.md") in prompt and prompt.endswith("精翻这篇")
    assert build_prompt("four-step-translate", "精翻这篇", []).startswith("/four-step-translate ")


FAKE_CODEX = textwrap.dedent('''
    import json, sys
    args = sys.argv[1:]
    prompt = sys.stdin.buffer.read().decode("utf-8")
    resumed = "resume" in args
    thread = args[-2] if resumed else "thread-1"
    def emit(event): print(json.dumps(event), flush=True)  # 纯 ASCII，和平台编码无关
    emit({"type": "thread.started", "thread_id": thread})
    emit({"type": "turn.started"})
    text = ("接着聊：" if resumed else "第一轮：") + prompt.strip().splitlines()[-1]
    emit({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": text}})
    emit({"type": "turn.completed", "usage": {}})
''')


@pytest.mark.asyncio
async def test_session_runs_one_process_per_turn_and_resumes(tmp_path):
    script = tmp_path / "fake_codex.py"
    script.write_text(FAKE_CODEX, encoding="utf-8")
    config = make_config(tmp_path, sandbox=False, codex_bin=f'"{sys.executable}" "{script}"'.replace("\\", "/"),
                         codex_home=tmp_path)

    async def deny(*_args):
        raise AssertionError("Codex 不走权限回调")

    spec = SessionSpec(run_id="r1", cwd=tmp_path, resume=None, on_permission=deny, harness="codex")
    session = await CodexSession.open(config, spec)
    seen = []

    async def collect(until: int):
        async for event in session.events():
            seen.append(event)
            if sum(e["type"] == "result" for e in seen) == until:
                return

    await session.send("你好")
    await asyncio.wait_for(collect(1), 30)
    await session.send("再说一句")
    await asyncio.wait_for(collect(2), 30)
    await session.close()

    texts = [e["text"] for e in seen if e["type"] == "text"]
    assert texts == ["第一轮：你好", "接着聊：再说一句"]
    assert [e["session_id"] for e in seen if e["type"] == "session"] == ["thread-1", "thread-1"]


@pytest.mark.asyncio
async def test_runner_records_harness_and_rejects_unknown_ones(tmp_path):
    config = make_config(tmp_path)
    factory = FakeFactory()
    runner = Runner(config, RunStore(config.runs_dir), factory)
    meta = runner.create("", "问个问题", "codex")
    assert meta.harness == "codex" and RunStore(config.runs_dir).load_meta(meta.id).harness == "codex"
    await runner.begin(meta.id, "你好", [])
    assert factory.last.spec.harness == "codex"
    with pytest.raises(RunnerError):
        runner.create("", "x", "gemini")
    await runner.shutdown()
