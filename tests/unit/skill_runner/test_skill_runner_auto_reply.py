"""等确认超时自动继续：带等待标记的一轮结束、AskUserQuestion 挂着，到时间都按推荐方案往下走。"""

import asyncio

import pytest

from skill_runner.runner import AUTO_REPLY_LIMIT, AWAIT_MARK, Runner, awaits_reply, recommended_answer
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
    assert session.sent[-1] == "继续，按照你的想法做就行了，不需要和我确认"
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


async def test_dismissing_awaiting_cancels_this_turns_auto_reply(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    session = factory.last
    await end_turn(session, f"做完了，要不要再加个测试？\n{AWAIT_MARK}")
    meta = runner.dismiss_awaiting(run_id)
    assert meta.status == "idle" and not meta.awaiting_reply and meta.auto_reply_at is None
    last = store.read_events(run_id)[-1]
    assert last["type"] == "status" and last["status"] == "idle" and last["awaiting"] is False

    await asyncio.sleep(0.1)
    await settle()
    assert len(session.sent) == 1 and runner.meta(run_id).auto_replies == 0

    # 下一轮又停在等确认：照常计时
    await runner.send_message(run_id, "好", [])
    await end_turn(session, f"还要确认一下\n{AWAIT_MARK}")
    assert runner.meta(run_id).awaiting_reply and runner.meta(run_id).auto_reply_at is not None


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
    await runner.answer(run_id, "tu-1", {"术语表可以吗？": "修改"})
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


@pytest.mark.parametrize("text, expected", [
    (f"术语表如下……\n{AWAIT_MARK}", True),
    (f"术语表如下……\n{AWAIT_MARK}  \n", True),
    (f"术语表如下……{AWAIT_MARK}", True),
    # 做完了，只是正文里提到这个标记（比如解释自动继续的规则）：不算在等
    (f"上一轮最后写了「{AWAIT_MARK}」，所以自动继续了。\n\n全部做完了。", False),
    ("全部做完了。", False),
    ("", False),
])
def test_only_a_mark_at_the_end_means_waiting(text, expected):
    assert awaits_reply(text) is expected


async def test_finished_turn_that_mentions_the_mark_does_not_auto_continue(runner, store, factory):
    run_id = await start(runner, auto_reply_s=0.05)
    await end_turn(factory.last, f"之前那条结尾写了{AWAIT_MARK}，所以会自动继续。\n现在都做完了。")
    meta = store.load_meta(run_id)
    assert not meta.awaiting_reply and meta.auto_reply_at is None
