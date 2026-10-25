"""等确认超时自动继续：带等待标记的一轮结束、AskUserQuestion 挂着，到时间都按推荐方案往下走。"""

import asyncio

from skill_runner.runner import AUTO_REPLY_LIMIT, AWAIT_MARK, Runner, recommended_answer
from skill_runner.store import RunStore

from skill_runner_fakes import settle

QUESTIONS = [{
    "question": "术语表可以吗？",
    "header": "术语",
    "options": [{"label": "修改"}, {"label": "确认 (Recommended)"}],
    "multiSelect": False,
}]


async def start(runner: Runner, auto_reply_s: float) -> str:
    meta = runner.create("four-step-translate", "精翻", auto_reply_s=auto_reply_s)
    await runner.begin(meta.id, "精翻", [])
    return meta.id


async def end_turn(session, text: str) -> None:
    session.push({"type": "text", "text": text, "parent": None})
    session.push({"type": "result", "session_id": "sess-1", "is_error": False})
    await settle()


def notices(store: RunStore, run_id: str) -> list[str]:
    return [e["text"] for e in store.read_events(run_id) if e["type"] == "notice"]


async def test_turn_ending_with_mark_is_awaiting_and_auto_continues(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    session = factory.last
    await end_turn(session, f"术语表如下……确认后开始翻译。\n{AWAIT_MARK}")

    meta = store.load_meta(run_id)
    assert meta.status == "idle" and meta.awaiting_reply and meta.auto_reply_at is not None
    assert any("会自动按推荐方案继续" in text for text in notices(store, run_id))

    await asyncio.sleep(0.1)
    await settle()
    meta = runner.meta(run_id)
    assert meta.status == "running"
    assert not meta.awaiting_reply and meta.auto_reply_at is None and meta.auto_replies == 1
    assert "（自动确认）" in session.sent[-1]
    assert store.read_events(run_id)[-2]["type"] == "user"  # 自动回复也记成一条消息，页面上看得到


async def test_finished_turn_without_mark_is_not_awaiting(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    session = factory.last
    await end_turn(session, "全部完成，zh.md 已生成。")
    await asyncio.sleep(0.1)
    await settle()
    meta = runner.meta(run_id)
    assert meta.status == "idle" and not meta.awaiting_reply
    assert len(session.sent) == 1


async def test_user_reply_cancels_auto_reply(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    session = factory.last
    await end_turn(session, f"术语表如下\n{AWAIT_MARK}")
    await runner.send_message(run_id, "第 3 条改成「机柜」", [])
    await asyncio.sleep(0.1)
    await settle()
    assert session.sent[-1] == "第 3 条改成「机柜」"
    assert runner.meta(run_id).auto_replies == 0


async def test_without_auto_reply_it_waits_but_still_marks_awaiting(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0)
    session = factory.last
    await end_turn(session, f"请确认术语表\n{AWAIT_MARK}")
    meta = runner.meta(run_id)
    assert meta.awaiting_reply and meta.auto_reply_at is None
    assert notices(store, run_id) == []


async def test_pending_question_gets_the_recommended_option(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    session = factory.last
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-1"))
    await settle()
    assert runner.meta(run_id).auto_reply_at is not None

    outcome = await asyncio.wait_for(asked, 1)
    assert outcome.allow
    assert outcome.updated_input["answers"] == {"术语表可以吗？": "确认 (Recommended)"}
    meta = runner.meta(run_id)
    assert meta.status == "running" and meta.auto_reply_at is None


async def test_answering_in_time_cancels_the_timer(runner, store, factory):
    run_id = await start(runner, auto_reply_s=5)
    session = factory.last
    asked = asyncio.create_task(session.spec.on_permission("AskUserQuestion", {"questions": QUESTIONS}, "tu-1"))
    await settle()
    runner.answer(run_id, "tu-1", {"术语表可以吗？": "修改"})
    outcome = await asked
    assert outcome.updated_input["answers"] == {"术语表可以吗？": "修改"}
    assert runner.meta(run_id).auto_reply_at is None
    assert runner._get(run_id).auto_task is None


async def test_auto_replies_stop_after_the_limit(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.02)
    session = factory.last
    for _ in range(AUTO_REPLY_LIMIT + 1):
        await end_turn(session, f"还要确认一下\n{AWAIT_MARK}")
        await asyncio.sleep(0.05)
        await settle()
    assert runner.meta(run_id).auto_replies == AUTO_REPLY_LIMIT
    assert runner.meta(run_id).awaiting_reply  # 最后一次就一直等用户


async def test_auto_reply_resumes_after_restart(config, store, factory):
    first = Runner(config, store, factory)
    run_id = await start(first, auto_reply_s=60)
    await end_turn(factory.last, f"请确认\n{AWAIT_MARK}")
    await first.shutdown()
    assert store.load_meta(run_id).auto_reply_at is not None

    second = Runner(config, store, factory)
    assert second.resume_auto_replies() == 1
    assert second._get(run_id).auto_task is not None
    await second.shutdown()


def test_recommended_answer_prefers_marked_option_then_first():
    assert recommended_answer(QUESTIONS[0]) == "确认 (Recommended)"
    assert recommended_answer({"options": [{"label": "A"}, {"label": "B"}], "multiSelect": True}) == ["A"]
    assert recommended_answer({"options": []}) == "按你的建议"
