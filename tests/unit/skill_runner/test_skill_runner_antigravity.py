"""Official agy stream-json contract and child-process lifecycle (no inference)."""

import asyncio
import importlib
import importlib.util
import json
import os
import signal
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from skill_runner.config import Config, HARNESSES
from skill_runner.runner import Runner, RunnerError, SessionSpec, build_prompt, harness_label
from skill_runner.store import RunStore
from skill_runner_fakes import FakeFactory, make_config, settle


@pytest.fixture
def agy(monkeypatch):
    assert importlib.util.find_spec("skill_runner.antigravity_session"), "Antigravity backend is missing"
    module = importlib.import_module("skill_runner.antigravity_session")
    create = module.asyncio.create_subprocess_exec
    async def launch(*args, **kwargs):
        # Windows cannot exec a .py fake directly; the production command stays one binary path.
        if args and str(args[0]).endswith("fake_agy.py"):
            args = (sys.executable, *args)
        return await create(*args, **kwargs)
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", launch)
    return module


def step(index=3, **values):
    return {"event": "step_update", "step_update": {
        "conversation_id": "conversation-1", "step_index": index,
        "state": "DONE", "step_type": "agent_response", **values,
    }}


def result(**values):
    return {"event": "result", "result": {
        "conversation_id": "conversation-1", "status": "SUCCESS", "response": "完成",
        "duration_seconds": 1.25, "num_turns": 2, "usage": {"total_tokens": 123}, **values,
    }}


def test_config_and_runner_support_antigravity(tmp_path):
    assert "antigravity" in HARNESSES
    config = Config.from_env({"SKILL_RUNNER_ANTIGRAVITY_BIN": "custom-agy", "SKILL_RUNNER_ANTIGRAVITY_MODEL": "available-model"})
    assert config.antigravity_bin == "custom-agy" and config.antigravity_model == "available-model"
    assert Config.from_env({}).antigravity_bin == "agy"
    assert Config.from_env({}).antigravity_model is None
    config = make_config(tmp_path)
    runner = Runner(config, RunStore(config.runs_dir), FakeFactory())
    meta = runner.create("", "问题", "antigravity")
    assert meta.harness == "antigravity"
    assert harness_label("antigravity") == "Gemini"
    with pytest.raises(RunnerError):
        runner.create("", "问题", "unknown")


def test_skill_prompt_uses_explicit_shared_skill_file(tmp_path):
    prompt = build_prompt("four-step-translate", "翻译", ["input/article.html"], "antigravity", tmp_path)
    assert str(tmp_path / "four-step-translate" / "SKILL.md") in prompt
    assert "input/article.html" in prompt
    assert not prompt.startswith("/four-step-translate")


def test_command_uses_stdin_explicit_resume_and_model_override(agy, tmp_path):
    config = make_config(tmp_path, sandbox=False, antigravity_model="configured-model")
    command = agy.build_command(config, "exact-conversation", "selected-model")
    assert command[:5] == ["agy", "--input-format", "stream-json", "--output-format", "stream-json"]
    assert command[command.index("--conversation") + 1] == "exact-conversation"
    assert command[command.index("--model") + 1] == "selected-model"
    assert command[command.index("--print-timeout") + 1] == "0s"
    assert "--dangerously-skip-permissions" in command
    assert "--continue" not in command and "-p" not in command
    first = agy.build_command(config, None)
    assert "--conversation" not in first and "configured-model" in first
    assert "--model" not in agy.build_command(make_config(tmp_path, sandbox=False), None)


def test_sandbox_requirement_fails_closed(agy, tmp_path):
    with pytest.raises(ValueError, match="沙箱|sandbox"):
        agy.build_command(make_config(tmp_path, sandbox=True), None)


def test_command_preserves_native_executable_path_and_expands_home(agy, tmp_path):
    binary = r"C:\Program Files\Antigravity\bin\agy.exe"
    config = make_config(tmp_path, sandbox=False, antigravity_bin=binary)
    assert agy.build_command(config, None)[0] == binary
    config = make_config(tmp_path, sandbox=False, antigravity_bin="~/.local/bin/agy")
    assert agy.build_command(config, None)[0] == str(Path("~/.local/bin/agy").expanduser())


def test_mapper_buffers_fragments_and_does_not_repeat_final_response(agy):
    mapper = agy.AntigravityMapper()
    initial = mapper.map({"event": "init", "conversation_id": "conversation-1", "init": {"model": "chosen"}})
    assert initial == [{"type": "session", "session_id": "conversation-1", "model": "chosen"}]
    assert mapper.map(step(state="ACTIVE", text_delta="等待")) == []
    assert mapper.map(step(state="ACTIVE", text_delta="确认")) == []
    assert mapper.map(step(text_delta="\n【等待确认】")) == [{"type": "text", "text": "等待确认\n【等待确认】", "parent": None}]
    final = mapper.map(result(response="等待确认\n【等待确认】"))
    assert [event["type"] for event in final] == ["result"]
    assert final[0]["session_id"] == "conversation-1"
    assert final[0]["duration_ms"] == 1250 and final[0]["num_turns"] == 2
    assert final[0]["usage"] == {"total_tokens": 123} and not final[0]["is_error"]


def test_mapper_handles_result_fallback_and_omits_unknown_actual_model(agy):
    mapper = agy.AntigravityMapper()
    assert "model" not in mapper.map({"event": "init", "conversation_id": "conversation-1", "init": {}})[0]
    events = mapper.map(result())
    assert [event["type"] for event in events] == ["text", "result"]
    assert events[0]["text"] == "完成"
    assert mapper.map(result()) == []


def test_result_fallback_keeps_final_answer_after_earlier_commentary(agy):
    mapper = agy.AntigravityMapper()
    mapper.map(step(text_delta="正在处理"))
    assert mapper.map(result())[0] == {"type": "text", "text": "完成", "parent": None}


@pytest.mark.parametrize("status", ["ERROR", "CANCELED", "INTERRUPTED", "INVALID", "WAITING", "RUNNING", "UNKNOWN"])
def test_non_success_statuses_are_errors_with_resumable_id(agy, status):
    mapper = agy.AntigravityMapper()
    events = mapper.map(result(status=status, error="failure", response=""))
    final = events[-1]
    assert final["is_error"] and final["session_id"] == "conversation-1"
    assert final["errors"] == ["failure"]
    assert final["subtype"] == ("interrupted" if status in {"CANCELED", "INTERRUPTED"} else "error")


def test_tool_steps_map_to_bounded_page_events_once(agy):
    mapper = agy.AntigravityMapper()
    tool = {"step_type": "tool", "tool_name": "run_command", "tool_info": {
        "name": "run_command", "parameters": {"CommandLine": "echo hello"}, "output": "x" * 5000,
    }}
    started = mapper.map(step(4, state="ACTIVE", **tool))
    assert len(started) == 1 and started[0]["name"] == "Bash" and started[0]["summary"] == "echo hello"
    assert mapper.map(step(4, state="ACTIVE", **tool)) == []
    ended = mapper.map(step(4, **tool))
    assert len(ended) == 1 and ended[0]["type"] == "tool_result" and ended[0]["ok"]
    assert ended[0]["id"] == started[0]["id"] and len(ended[0]["text"]) < 2100
    assert mapper.map(step(4, **tool)) == []
    failed = mapper.map(step(5, step_type="tool", tool_name="write_to_file", tool_info={
        "parameters": {"TargetFile": "translated.md"}, "error": {"type": "DENIED", "message": "permission denied"},
    }))
    assert failed[0]["name"] == "Write" and failed[0]["summary"] == "translated.md"
    assert failed[1]["ok"] is False and "permission denied" in failed[1]["text"]


FAKE_AGY = textwrap.dedent('''
    import json, os, sys, time
    from pathlib import Path
    args = sys.argv[1:]
    inputs = sys.stdin.buffer.read().decode("utf-8").splitlines()
    assert len(inputs) == 1
    user = json.loads(inputs[0])
    assert user["event"] == "user"
    prompt = user["message"]["content"]
    conversation = args[args.index("--conversation") + 1] if "--conversation" in args else "conversation-1"
    with Path("received.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"prompt": prompt, "args": args, "pid": os.getpid()}) + "\\n")
    def emit(event): print(json.dumps(event), flush=True)
    emit({"event": "init", "conversation_id": conversation, "init": {}})
    mode = prompt.strip().splitlines()[-1]
    if mode == "missing-result":
        print("not json output", flush=True)
        sys.exit(0)
    if mode == "invalid-json-type":
        emit([])
        time.sleep(30)
    if mode == "sleep":
        time.sleep(30)
    if mode == "oversized-output":
        import signal, threading
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        def stderr():
            sys.stderr.buffer.write(b'e' * 4000000)
            sys.stderr.buffer.flush()
        threading.Thread(target=stderr, daemon=True).start()
        sys.stdout.buffer.write(b'x' * 4000000)
        sys.stdout.buffer.flush()
        time.sleep(30)
    if mode in {"descendant-pipes", "descendant-detached-output"}:
        import subprocess
        child_code = "import os, signal, time; from pathlib import Path; signal.signal(signal.SIGINT, signal.SIG_IGN); Path('descendant.pid').write_text(str(os.getpid())); time.sleep(30)"
        child = subprocess.Popen([sys.executable, "-c", child_code],
                                 stdout=subprocess.DEVNULL if mode == "descendant-detached-output" else None,
                                 stderr=subprocess.DEVNULL if mode == "descendant-detached-output" else None)
        while not Path("descendant.pid").exists(): time.sleep(.01)
        if mode == "descendant-pipes":
            sys.exit(0)
    emit({"event": "step_update", "step_update": {"conversation_id": conversation, "step_index": 3,
          "state": "DONE", "step_type": "agent_response", "text_delta": mode}})
    emit({"event": "result", "result": {"conversation_id": conversation, "status": "SUCCESS", "response": mode}})
    sys.exit(7 if mode == "nonzero-exit" else 0)
''')


async def open_fake(agy, tmp_path, **overrides):
    script = tmp_path / "fake_agy.py"
    script.write_text(FAKE_AGY, encoding="utf-8")
    config = make_config(tmp_path, sandbox=False, antigravity_bin=str(script))
    spec = SessionSpec(**{"run_id": "r1", "cwd": tmp_path, "resume": None,
                          "on_permission": None, "harness": "antigravity", **overrides})
    return await agy.AntigravitySession.open(config, spec)


async def collect_turn(session):
    events = []
    async for event in session.events():
        events.append(event)
        if event["type"] == "result":
            return events


async def test_session_queues_turns_and_resumes_without_exposing_prompt_in_args(agy, tmp_path):
    session = await open_fake(agy, tmp_path, prompt_note="额外说明", model="chosen-model")
    try:
        await session.send("第一轮")
        await session.send("第二轮")
        assert session.busy
        events = await asyncio.wait_for(collect_turn(session), 15)
        events += await asyncio.wait_for(collect_turn(session), 15)
        assert [e["text"] for e in events if e["type"] == "text"] == ["第一轮", "第二轮"]
        received = [json.loads(line) for line in (tmp_path / "received.jsonl").read_text(encoding="utf-8").splitlines()]
        assert received[0]["pid"] != received[1]["pid"]
        assert "【等待确认】" in received[0]["prompt"] and "input/" in received[0]["prompt"]
        assert "额外说明" in received[0]["prompt"] and received[1]["prompt"] == "第二轮"
        assert "--conversation" not in received[0]["args"]
        assert received[1]["args"][received[1]["args"].index("--conversation") + 1] == "conversation-1"
        assert "chosen-model" in received[0]["args"] and "第一轮" not in received[0]["args"]
    finally:
        await session.close()
    assert not session.busy
    with pytest.raises(RuntimeError, match="closed|关闭"):
        await session.send("late")


@pytest.mark.parametrize("prompt", ["missing-result", "nonzero-exit", "invalid-json-type"])
async def test_invalid_process_output_never_reports_success(agy, tmp_path, prompt):
    session = await open_fake(agy, tmp_path)
    try:
        await session.send(prompt)
        events = await asyncio.wait_for(collect_turn(session), 15)
        assert events[-1]["is_error"] and events[-1]["session_id"] == "conversation-1"
    finally:
        await session.close()
    assert session._proc is None or session._proc.returncode is not None


async def test_interrupt_reaps_real_child_and_keeps_session_resumable(agy, tmp_path):
    session = await open_fake(agy, tmp_path)
    try:
        await session.send("sleep")
        stream = session.events()
        assert (await asyncio.wait_for(anext(stream), 15))["type"] == "session"
        await stream.aclose()
        proc = session._proc
        await session.interrupt()
        assert proc.returncode is not None
        events = await asyncio.wait_for(collect_turn(session), 15)
        assert events[-1]["is_error"] and events[-1]["subtype"] == "interrupted"
        await session.send("继续")
        assert not (await asyncio.wait_for(collect_turn(session), 15))[-1]["is_error"]
    finally:
        await session.close()


async def test_close_waits_for_worker_cleanup(agy, tmp_path, monkeypatch):
    started, stopping, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def work(self):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopping.set()
            await release.wait()
    monkeypatch.setattr(agy.AntigravitySession, "_work", work)
    session = await open_fake(agy, tmp_path)
    await started.wait()
    closing = asyncio.create_task(session.close())
    try:
        await stopping.wait()
        assert not closing.done()
    finally:
        release.set()
        await closing
    assert session._worker.done()


async def test_close_during_startup_waits_for_child_reaping(agy, tmp_path, monkeypatch):
    started, release, killed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    proc = SimpleNamespace(returncode=None, send_signal=lambda _: killed.set())
    async def wait():
        await killed.wait()
        proc.returncode = 0
        return 0
    proc.wait = wait
    async def create(*args, **kwargs):
        started.set()
        await release.wait()
        return proc
    monkeypatch.setattr(agy.asyncio, "create_subprocess_exec", create)
    session = await open_fake(agy, tmp_path)
    await session.send("start")
    await started.wait()
    closing = asyncio.create_task(session.close())
    try:
        await settle()
        assert not closing.done()
    finally:
        release.set()
        await closing
    assert killed.is_set() and proc.returncode == 0 and session._worker.done()


async def test_reopened_session_resumes_exact_id_without_repeating_preface(agy, tmp_path):
    session = await open_fake(agy, tmp_path, resume="saved-session", prompt_note="extra")
    try:
        await session.send("继续")
        events = await asyncio.wait_for(collect_turn(session), 15)
        assert events[-1]["session_id"] == "saved-session" and not events[-1]["is_error"]
        received = json.loads((tmp_path / "received.jsonl").read_text(encoding="utf-8"))
        assert received["prompt"] == "继续" and "saved-session" in received["args"]
    finally:
        await session.close()


async def test_interrupt_during_startup_waits_for_child_and_emits_interrupted(agy, tmp_path, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()
    create = agy.asyncio.create_subprocess_exec
    children = []
    async def delayed(*args, **kwargs):
        started.set()
        await release.wait()
        child = await create(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(agy.asyncio, "create_subprocess_exec", delayed)
    session = await open_fake(agy, tmp_path)
    try:
        await session.send("sleep")
        await started.wait()
        interrupting = asyncio.create_task(session.interrupt())
        await settle()
        assert not interrupting.done()
        release.set()
        await asyncio.wait_for(interrupting, 15)
        assert children[0].returncode is not None
        final = (await asyncio.wait_for(collect_turn(session), 15))[-1]
        assert final["is_error"] and final["subtype"] == "interrupted"
    finally:
        release.set()
        await session.close()


async def test_old_process_cleanup_does_not_forget_new_child(agy, tmp_path):
    started, release = asyncio.Event(), asyncio.Event()
    old = SimpleNamespace(returncode=None, send_signal=lambda _: None)
    new = SimpleNamespace(returncode=None)
    async def wait():
        started.set()
        await release.wait()
        old.returncode = 0
        return 0
    old.wait = wait
    session = await open_fake(agy, tmp_path)
    session._proc = old
    stopping = asyncio.create_task(session.interrupt())
    try:
        await started.wait()
        session._proc = new  # A queued turn can start while the old interrupt waits.
        release.set()
        await stopping
        assert session._proc is new
    finally:
        release.set()
        await stopping
        session._proc = None
        await session.close()


async def test_interrupt_forces_kill_and_waits_for_reaping(agy, tmp_path, monkeypatch):
    monkeypatch.setattr(agy, "INTERRUPT_GRACE_S", 0.001)
    killed = asyncio.Event()
    proc = SimpleNamespace(returncode=None, send_signal=lambda _: None, terminate=lambda: None, kill=killed.set)
    async def wait():
        await killed.wait()
        proc.returncode = -9
        return -9
    proc.wait = wait
    session = await open_fake(agy, tmp_path)
    session._proc = proc
    try:
        await session.interrupt()
        assert killed.is_set() and proc.returncode == -9
    finally:
        await session.close()


@pytest.mark.parametrize("concurrent_interrupts", [False, True])
async def test_oversized_output_is_drained_after_force_kill_and_next_turn_runs(agy, tmp_path, monkeypatch, concurrent_interrupts):
    monkeypatch.setattr(agy, "INTERRUPT_GRACE_S", 0.05)
    create = agy.asyncio.create_subprocess_exec
    children = []
    async def small_pipe(*args, **kwargs):
        kwargs["limit"] = 1024
        proc = await create(*args, **kwargs)
        proc.send_signal = lambda _: None  # Emulate a child that ignores the graceful signal.
        children.append(proc)
        return proc
    monkeypatch.setattr(agy.asyncio, "create_subprocess_exec", small_pipe)
    session = await open_fake(agy, tmp_path)
    recovered = False
    try:
        await session.send("oversized-output")
        failed = await asyncio.wait_for(collect_turn(session), 5)
        assert failed[-1]["is_error"]
        if concurrent_interrupts:
            await asyncio.wait_for(asyncio.gather(session.interrupt(), session.interrupt()), 3)
        await session.send("recovered")
        succeeded = await asyncio.wait_for(collect_turn(session), 3)
        assert not succeeded[-1]["is_error"]
        assert children[0].returncode is not None
        recovered = True
    finally:
        if not recovered and children:
            # Keep the failing regression from leaking handles before the fix exists.
            proc = children[0]
            if proc.returncode is None:
                proc.kill()
            async def drain(stream):
                while await stream.read(65536):
                    pass
            await asyncio.wait_for(asyncio.gather(drain(proc.stdout), drain(proc.stderr)), 5)
        await asyncio.wait_for(session.close(), 5)


@pytest.mark.skipif(os.name != "posix", reason="Production process-group containment runs on POSIX")
@pytest.mark.parametrize("mode", ["descendant-pipes", "descendant-detached-output"])
async def test_linux_cleanup_kills_descendants_even_after_leader_exit(agy, tmp_path, monkeypatch, mode):
    monkeypatch.setattr(agy, "INTERRUPT_GRACE_S", 0.05)
    session = await open_fake(agy, tmp_path)
    descendant = None
    try:
        await session.send(mode)
        async def ready():
            while not (tmp_path / "descendant.pid").exists():
                await asyncio.sleep(0.01)
            return int((tmp_path / "descendant.pid").read_text())
        descendant = await asyncio.wait_for(ready(), 5)
        if mode == "descendant-pipes":
            await asyncio.wait_for(session.interrupt(), 3)
        await asyncio.wait_for(collect_turn(session), 3)
        await asyncio.wait_for(session.close(), 3)
        async def child_exited():
            while True:
                try:
                    # A dead orphan may remain a zombie until the container's init reaps it.
                    state = Path(f"/proc/{descendant}/stat").read_text().split(") ", 1)[1].split()[0]
                except FileNotFoundError:
                    return
                if state == "Z":
                    return
                await asyncio.sleep(0.01)
        await asyncio.wait_for(child_exited(), 3)
        assert not session.busy
    finally:
        if descendant is not None:
            try:
                os.kill(descendant, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await asyncio.wait_for(session.close(), 5)


async def test_busy_keeps_completed_events_until_consumed(agy, tmp_path, monkeypatch):
    async def turn(self, prompt):
        await self._queue.put(self._mapper.result(is_error=False))
    monkeypatch.setattr(agy.AntigravitySession, "_turn", turn)
    session = await open_fake(agy, tmp_path)
    try:
        await session.send("finish")
        await settle()
        assert session.busy
        stream = session.events()
        assert (await anext(stream))["type"] == "result"
        await stream.aclose()
        assert not session.busy
    finally:
        await session.close()


async def test_app_dispatches_all_harnesses_explicitly(agy, tmp_path, monkeypatch):
    from skill_runner import app, codex_session
    factories = {name: FakeFactory() for name in ("claude", "codex", "antigravity")}
    monkeypatch.setitem(sys.modules, "skill_runner.sdk_session", SimpleNamespace(make_factory=lambda config: factories["claude"]))
    monkeypatch.setattr(codex_session, "make_codex_factory", lambda config: factories["codex"])
    monkeypatch.setattr(agy, "make_antigravity_factory", lambda config: factories["antigravity"])
    runner = app.create_app(make_config(tmp_path)).state.runner
    for harness in factories:
        spec = SessionSpec(run_id=harness, cwd=tmp_path, resume=None, on_permission=None, harness=harness)
        assert await runner.session_factory(spec) is factories[harness].last
    with pytest.raises(RunnerError):
        await runner.session_factory(SessionSpec(run_id="x", cwd=tmp_path, resume=None, on_permission=None, harness="unknown"))


def test_user_facing_text_calls_it_gemini():
    import inspect
    from skill_runner import antigravity_session, models, runner, runtime_updates
    for module in (antigravity_session, models, runner, runtime_updates):
        for line in inspect.getsource(module).splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "Antigravity" not in stripped:
                continue
            # 只允许类名、文档字符串、英文日志/异常，以及写给模型看的运行环境说明里出现 Antigravity
            assert any(token in stripped for token in (
                "class Antigravity", "Antigravity CLI backend", "AntigravityMapper", "AntigravitySession",
                "Antigravity model output", "Antigravity model discovery", "Antigravity 的审阅界面",
            )), f"{module.__name__}: {stripped}"
