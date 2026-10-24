import asyncio

import pytest

from skill_runner.runner import Busy, Conflict, Runner, SessionFailed, build_prompt, make_title
from skill_runner.store import RunStore

from skill_runner_fakes import make_config, settle


def kinds(store, run_id):
    return [e["type"] for e in store.read_events(run_id)]


async def start(runner, message="翻译这篇", files=None, skill="four-step-translate"):
    files = files or []
    meta = runner.create(skill, make_title(message, files))
    await runner.begin(meta.id, message, files)
    return meta.id


def test_prompt_dispatches_skill_and_lists_attachments():
    assert build_prompt("four-step-translate", "精翻", ["input/a.html"]) == (
        "/four-step-translate 精翻\n\n附件（已保存在当前运行目录）：\n- input/a.html"
    )
    assert build_prompt(None, "  继续 ", []) == "继续"
    assert build_prompt("", "你好", []) == "你好"
    assert make_title("", ["input/a.html"]) == "a.html"
    assert make_title("第一行\n第二行", []) == "第一行"


async def test_turn_runs_to_idle_and_records_session(runner, store, factory):
    run_id = await start(runner, files=["input/a.html"])
    session = factory.last
    assert session.sent == [build_prompt("four-step-translate", "翻译这篇", ["input/a.html"])]
    assert session.spec.resume is None
    assert runner.meta(run_id).status == "running"

    session.push({"type": "session", "session_id": "sess-1"})
    session.push({"type": "text", "text": "术语表如下", "parent": None})
    session.push({"type": "result", "session_id": "sess-1", "is_error": False})
    await settle()

    meta = runner.meta(run_id)
    assert meta.status == "idle"
    assert meta.session_id == "sess-1"
    assert store.load_meta(run_id).session_id == "sess-1"
    assert kinds(store, run_id) == ["user", "status", "text", "result", "status"]
    events = store.read_events(run_id)
    assert [e["seq"] for e in events] == [1, 2, 3, 4, 5]
    assert events[0] == {**events[0], "type": "user", "text": "翻译这篇", "files": ["input/a.html"]}


async def test_question_waits_for_answer_and_returns_answers(runner, store, factory):
    run_id = await start(runner)
    session = factory.last
    questions = [{"question": "术语表可以吗？", "header": "术语", "options": [{"label": "确认"}, {"label": "修改"}], "multiSelect": False}]
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": questions}, "tu-1"))
    await settle()
    assert runner.meta(run_id).status == "waiting"
    assert not asked.done()
    question = store.read_events(run_id)[-2]
    assert question == {**question, "type": "question", "qid": "tu-1", "questions": questions}

    with pytest.raises(Conflict):
        runner.answer(run_id, "other", {"术语表可以吗？": "确认"})
    runner.answer(run_id, "tu-1", {"术语表可以吗？": "确认"})
    outcome = await asked
    assert outcome.allow
    assert outcome.updated_input == {"questions": questions, "answers": {"术语表可以吗？": "确认"}}
    assert runner.meta(run_id).status == "running"
    with pytest.raises(Conflict):
        runner.answer(run_id, "tu-1", {"术语表可以吗？": "确认"})


async def test_composer_text_answers_pending_question_as_free_text(runner, store, factory):
    run_id = await start(runner)
    session = factory.last
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": []}, "tu-9"))
    await settle()
    await runner.send_message(run_id, "fleet 改成机队", [])
    outcome = await asked
    assert outcome.updated_input == {"questions": [], "response": "fleet 改成机队"}
    assert session.sent == [build_prompt("four-step-translate", "翻译这篇", [])]  # 没有另发一条消息
    assert kinds(store, run_id)[-3:] == ["user", "answer", "status"]


async def test_policy_denial_is_reported_to_page(runner, store, factory):
    run_id = await start(runner)
    outcome = await factory.last.spec.on_permission("Write", {"file_path": "/etc/passwd"}, "tu-2")
    assert not outcome.allow
    notice = store.read_events(run_id)[-1]
    assert notice["type"] == "notice" and "已拦截 Write" in notice["text"]
    allowed = await factory.last.spec.on_permission("Write", {"file_path": "out/zh.md"}, "tu-3")
    assert allowed.allow
    # 沙箱为白名单外的域名发来的权限请求：拒绝，页面上能看到具体原因
    network = await factory.last.spec.on_permission("Bash", {"command": "curl https://pypi.org"}, "tu-4", "Claude wants to access pypi.org")
    assert not network.allow
    assert "pypi.org" in store.read_events(run_id)[-1]["text"]


async def test_interrupt_rejects_pending_question_and_signals_session(runner, factory):
    run_id = await start(runner)
    session = factory.last
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": []}, "tu-4"))
    await settle()
    await runner.interrupt(run_id)
    outcome = await asked
    assert not outcome.allow and outcome.interrupt
    assert session.interrupted


async def test_message_during_run_is_sent_and_new_output_reactivates(runner, factory):
    run_id = await start(runner)
    session = factory.last
    await runner.send_message(run_id, "顺便把标题也译了", [])
    assert len(session.sent) == 2
    session.push({"type": "result", "session_id": "s"})
    await settle()
    assert runner.meta(run_id).status == "idle"
    session.push({"type": "text", "text": "好的，标题是……"})
    await settle()
    assert runner.meta(run_id).status == "running"


async def test_idle_session_is_closed_and_next_message_resumes(tmp_path, factory):
    config = make_config(tmp_path, idle_timeout_s=0.01)
    store = RunStore(config.runs_dir)
    runner = Runner(config, store, factory)
    run_id = await start(runner)
    first = factory.last
    first.push({"type": "session", "session_id": "sess-7"})
    first.push({"type": "result", "session_id": "sess-7"})
    await settle()
    await asyncio.sleep(0.05)
    assert first.closed
    assert runner.meta(run_id).status == "idle"

    await runner.send_message(run_id, "继续", [])
    second = factory.last
    assert second is not first
    assert second.spec.resume == "sess-7"
    assert second.sent == ["继续"]
    assert runner.meta(run_id).status == "running"


async def test_stream_crash_marks_error_and_message_resumes(runner, store, factory):
    run_id = await start(runner)
    session = factory.last
    session.push({"type": "session", "session_id": "sess-x"})
    session.push(RuntimeError("boom"))
    await settle()
    meta = runner.meta(run_id)
    assert meta.status == "error" and "boom" in meta.error
    assert session.closed
    await runner.send_message(run_id, "继续", [])
    assert factory.last.spec.resume == "sess-x"


async def test_unexpected_stream_end_while_running_is_an_error(runner, factory):
    run_id = await start(runner)
    factory.last.end_stream()
    await settle()
    assert runner.meta(run_id).status == "error"
    assert "意外退出" in runner.meta(run_id).error


async def test_open_failure_records_message_and_error(runner, store, factory):
    meta = runner.create("four-step-translate", "t")
    factory.fail_with = RuntimeError("not logged in")
    with pytest.raises(SessionFailed):
        await runner.begin(meta.id, "翻译", [])
    assert runner.meta(meta.id).status == "error"
    assert kinds(store, meta.id) == ["user", "error", "status"]


async def test_concurrency_limit_counts_running_and_waiting(tmp_path, factory):
    config = make_config(tmp_path, max_active=1)
    store = RunStore(config.runs_dir)
    runner = Runner(config, store, factory)
    first = await start(runner)
    with pytest.raises(Busy):
        runner.create("four-step-translate", "second")
    factory.last.push({"type": "result", "session_id": "s"})
    await settle()
    second = await start(runner)
    # 第一个已经空闲，它想继续时第二个正占着名额
    factory.sessions[0].push({"type": "text", "text": "x"})
    await settle()
    assert runner.meta(first).status == "running"
    assert runner.meta(second).status == "running"


async def test_unknown_skill_is_rejected(runner):
    from skill_runner.runner import RunnerError

    with pytest.raises(RunnerError):
        runner.create("rm-rf", "x")


async def test_recover_marks_interrupted_runs_after_restart(config, store, factory):
    meta = store.create("four-step-translate", "t")
    meta.status = "waiting"
    meta.session_id = "sess-r"
    store.save_meta(meta)
    runner = Runner(config, store, factory)
    assert runner.recover() == 1
    recovered = store.load_meta(meta.id)
    assert recovered.status == "error" and "服务重启" in recovered.error
    await runner.send_message(meta.id, "继续", [])
    assert factory.last.spec.resume == "sess-r"


async def test_delete_requires_inactive_run_and_removes_directory(runner, store, factory):
    run_id = await start(runner)
    with pytest.raises(Conflict):
        await runner.delete(run_id)
    factory.last.push({"type": "result", "session_id": "s"})
    await settle()
    backlog, queue = runner.subscribe(run_id)
    await runner.delete(run_id)
    assert not store.exists(run_id)
    assert factory.last.closed
    assert queue.get_nowait() is None  # SSE 订阅者收到结束信号


async def test_subscribe_replays_backlog_then_streams_live(runner, factory):
    run_id = await start(runner)
    backlog, queue = runner.subscribe(run_id, after_seq=1)
    assert [e["seq"] for e in backlog] == [2]
    factory.last.push({"type": "text", "text": "hi"})
    await settle()
    live = queue.get_nowait()
    assert live["seq"] == 3 and live["text"] == "hi"
    runner.unsubscribe(run_id, queue)
    factory.last.push({"type": "text", "text": "again"})
    await settle()
    assert queue.empty()


async def test_shutdown_closes_sessions(runner, factory):
    await start(runner)
    await runner.shutdown()
    assert factory.last.closed
