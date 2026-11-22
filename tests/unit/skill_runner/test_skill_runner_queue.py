"""名额、排队、不常驻、提问脱离进程。"""

import asyncio

import pytest

from skill_runner import runner as runner_mod
from skill_runner.runner import Runner, make_title
from skill_runner.store import RunStore

from skill_runner_fakes import make_config, settle

QUESTIONS = [{"question": "术语表可以吗？", "header": "术语",
              "options": [{"label": "确认 (Recommended)"}, {"label": "修改"}], "multiSelect": False}]


@pytest.fixture(autouse=True)
def plenty_of_memory(monkeypatch):
    monkeypatch.setattr(runner_mod, "mem_available_mb", lambda: 2000)


def make_runner(tmp_path, factory, **overrides):
    config = make_config(tmp_path, **overrides)
    return Runner(config, RunStore(config.runs_dir), factory)


async def start(runner, message="翻译这篇", skill="four-step-translate"):
    meta = runner.create(skill, make_title(message, []))
    await runner.begin(meta.id, message, [])
    return meta.id


def finish(session, sid="s"):
    session.push({"type": "session", "session_id": sid})
    session.push({"type": "result", "session_id": sid, "is_error": False})


async def test_full_slots_queue_instead_of_rejecting_and_start_when_freed(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=1, idle_timeout_s=0.01)
    first = await start(runner)
    second = await start(runner, "第二篇")
    assert runner.meta(second).status == "queued"
    assert runner.meta(second).queued_prompt
    assert len(factory.sessions) == 1

    finish(factory.sessions[0])
    await settle()
    await asyncio.sleep(0.05)
    await settle()
    assert factory.sessions[0].closed  # 不常驻：一轮结束就关
    assert runner.meta(first).status == "idle"
    assert runner.meta(second).status == "running"
    assert factory.last.sent == ["/four-step-translate 第二篇"]
    assert runner.meta(second).queued_prompt is None


async def test_heavy_skill_takes_two_slots(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=3)
    await start(runner, skill="podcast-cn-dubber")
    await start(runner)
    assert runner.slots_used() == 3
    third = await start(runner, "第三篇")
    assert runner.meta(third).status == "queued"


async def test_first_run_always_starts_even_if_heavy_or_low_memory(tmp_path, factory, monkeypatch):
    monkeypatch.setattr(runner_mod, "mem_available_mb", lambda: 100)
    runner = make_runner(tmp_path, factory, max_active=1)
    run_id = await start(runner, skill="podcast-cn-dubber")
    assert runner.meta(run_id).status == "running"


async def test_low_memory_queues_second_run(tmp_path, factory, monkeypatch):
    runner = make_runner(tmp_path, factory, max_active=3)
    await start(runner)
    monkeypatch.setattr(runner_mod, "mem_available_mb", lambda: 100)
    second = await start(runner, "第二篇")
    assert runner.meta(second).status == "queued"


async def test_message_while_queued_is_appended_and_interrupt_cancels(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=1)
    await start(runner)
    second = await start(runner, "第二篇")
    await runner.send_message(second, "补充一句", [])
    assert runner.meta(second).queued_prompt.endswith("补充一句")
    await runner.interrupt(second)
    assert runner.meta(second).status == "idle"
    assert runner.meta(second).queued_prompt is None


async def test_queue_is_fifo(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=1, idle_timeout_s=0.01)
    await start(runner)
    second = await start(runner, "第二篇")
    third = await start(runner, "第三篇")
    assert runner.queue_position(third) == 2
    finish(factory.sessions[0])
    await settle()
    await asyncio.sleep(0.05)
    await settle()
    assert runner.meta(second).status == "running"
    assert runner.meta(third).status == "queued"


async def test_queued_run_survives_restart(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=1)
    await start(runner)
    second = await start(runner, "第二篇")
    fresh = Runner(runner.config, runner.store, factory)
    fresh.recover()
    assert fresh.resume_queue() == 1
    await settle(10)
    assert fresh.meta(second).status == "running"


async def test_unanswered_question_detaches_and_answer_resumes(tmp_path, factory):
    runner = make_runner(tmp_path, factory, question_detach_s=0.01)
    run_id = await start(runner)
    session = factory.last
    session.push({"type": "session", "session_id": "sess-q"})
    await settle()
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-1"))
    await settle()
    assert runner.meta(run_id).status == "waiting"
    await asyncio.sleep(0.05)
    await settle()
    outcome = await asked
    assert outcome.allow is False
    meta = runner.meta(run_id)
    assert session.closed
    assert meta.status == "idle" and meta.awaiting_reply
    assert list(meta.detached_questions) == ["tu-1"]
    assert runner.slots_used() == 0

    await runner.answer(run_id, "tu-1", {"术语表可以吗？": "修改"})
    resumed = factory.last
    assert resumed is not session and resumed.spec.resume == "sess-q"
    assert "术语表可以吗？：修改" in resumed.sent[0]
    meta = runner.meta(run_id)
    assert meta.status == "running" and meta.detached_questions == {}
    kinds = [e["type"] for e in runner.store.read_events(run_id)]
    assert kinds.count("user") == 1  # 回答不再多出一条用户消息


async def test_free_text_answers_detached_question(tmp_path, factory):
    runner = make_runner(tmp_path, factory, question_detach_s=0.01)
    run_id = await start(runner)
    session = factory.last
    session.push({"type": "session", "session_id": "sess-q"})
    await settle()
    asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-1"))
    await asyncio.sleep(0.05)
    await settle()
    await runner.send_message(run_id, "术语都按你的来", [])
    assert factory.last.sent[0].startswith("（回答你之前的提问）")
    assert runner.meta(run_id).detached_questions == {}


async def test_detached_question_auto_answers_with_recommended(tmp_path, factory):
    runner = make_runner(tmp_path, factory, question_detach_s=0.01)
    meta = runner.create("four-step-translate", "t", auto_reply_s=1)
    await runner.begin(meta.id, "翻译", [])
    session = factory.last
    session.push({"type": "session", "session_id": "sess-q"})
    await settle()
    asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-1"))
    await asyncio.sleep(0.05)
    await settle()
    run = runner._get(meta.id)
    assert run.auto_task is not None  # 脱离进程后自动回复照旧排着
    run.auto_task.cancel()
    await runner_mod.Runner._auto_reply_later(runner, run, 0)
    assert "确认 (Recommended)" in factory.last.sent[0]


async def test_waiting_run_recovers_as_detached_question(tmp_path, factory):
    runner = make_runner(tmp_path, factory)
    run_id = await start(runner)
    session = factory.last
    session.push({"type": "session", "session_id": "sess-r"})
    await settle()
    asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-9"))
    await settle()
    fresh = Runner(runner.config, runner.store, factory)
    fresh.recover()
    meta = fresh.meta(run_id)
    assert meta.status == "idle" and "tu-9" in meta.detached_questions


async def test_queue_mode_holds_message_until_turn_ends(tmp_path, factory):
    runner = make_runner(tmp_path, factory)
    run_id = await start(runner)
    session = factory.last
    await runner.send_message(run_id, "第一条补充", [], mode="queue")
    await runner.send_message(run_id, "第二条补充", [], mode="queue")
    held = runner.meta(run_id).held
    assert [h["text"] for h in held] == ["第一条补充", "第二条补充"]
    assert session.sent == ["/four-step-translate 翻译这篇"]

    runner.edit_held(run_id, held[1]["id"], "第二条（改过）")
    finish(session)
    await settle(10)
    assert session.sent[-1] == "第一条补充"
    assert runner.meta(run_id).status == "running"
    assert [h["text"] for h in runner.meta(run_id).held] == ["第二条（改过）"]

    finish(session)
    await settle(10)
    assert session.sent[-1] == "第二条（改过）"
    assert runner.meta(run_id).held == []
    assert "held" in [e["type"] for e in runner.store.read_events(run_id)]


async def test_held_message_can_be_sent_now_or_deleted(tmp_path, factory):
    runner = make_runner(tmp_path, factory)
    run_id = await start(runner)
    session = factory.last
    await runner.send_message(run_id, "插话", [], mode="queue")
    await runner.send_message(run_id, "算了", [], mode="queue")
    first, second = runner.meta(run_id).held
    await runner.send_held(run_id, first["id"])
    assert session.sent[-1] == "插话"
    runner.delete_held(run_id, second["id"])
    assert runner.meta(run_id).held == []


async def test_queue_mode_sends_immediately_when_idle_and_not_after_interrupt(tmp_path, factory):
    runner = make_runner(tmp_path, factory)
    run_id = await start(runner)
    session = factory.last
    finish(session)
    await settle()
    await runner.send_message(run_id, "接着做", [], mode="queue")
    assert session.sent[-1] == "接着做"

    await runner.send_message(run_id, "等会儿再发", [], mode="queue")
    await runner.interrupt(run_id)
    finish(session)
    await settle(10)
    assert session.sent[-1] == "接着做"
    assert [h["text"] for h in runner.meta(run_id).held] == ["等会儿再发"]


async def test_status_command_is_answered_by_the_runner_not_the_model(tmp_path, factory):
    runner = make_runner(tmp_path, factory, max_active=1)
    run_id = await start(runner)
    session = factory.last
    session.push({"type": "session", "session_id": "sess-s", "model": "claude-opus-5-5"})
    await settle()
    second = await start(runner, "第二篇")
    await runner.send_message(run_id, "补一句", [], mode="queue")

    await runner.send_message(run_id, " /status ", [])
    assert session.sent == ["/four-step-translate 翻译这篇"]  # 没发给模型
    report = runner.store.read_events(run_id)[-1]
    assert report["type"] == "report"
    text = "\n".join(report["lines"])
    assert "状态：进行中" in text and "sess-s" in text and "claude-opus-5-5" in text
    assert "名额：已用 1/1" in text and "挂起的消息：1 条" in text

    await runner.send_message(second, "/状态", [])
    text = "\n".join(runner.store.read_events(second)[-1]["lines"])
    assert "排队：第 1 位" in text and "进程：还没启动" in text
