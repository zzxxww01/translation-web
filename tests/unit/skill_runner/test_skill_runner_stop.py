import asyncio

import pytest

from skill_runner.runner import SessionFailed
from skill_runner_fakes import settle


async def test_stop_waits_for_close_and_preserves_resume_history(runner, store, factory):
    meta = runner.create('four-step-translate', 'old translation', harness='codex')
    await runner.begin(meta.id, 'translate', [])
    session = factory.last
    session.push({'type': 'session', 'session_id': 'old-thread'})
    await settle()
    closing, release = asyncio.Event(), asyncio.Event()
    original_close = session.close

    async def close():
        closing.set()
        await release.wait()
        await original_close()

    session.close = close
    stopped = asyncio.create_task(runner.stop(meta.id))
    await asyncio.wait_for(closing.wait(), timeout=1)
    assert not stopped.done()
    release.set()
    result = await stopped
    assert session.closed and runner.active_count() == 0
    assert result.status == 'error'  # interrupted, never a completed translation
    assert store.load_meta(meta.id).session_id == 'old-thread'
    assert any(event['type'] == 'user' for event in store.read_events(meta.id))
    await runner.send_message(meta.id, 'continue old conversation', [])
    assert factory.last.spec.resume == 'old-thread'
    await runner.shutdown()


async def test_stop_cancels_pending_confirmation_and_automatic_reply(runner, factory, store):
    meta = runner.create('four-step-translate', 'waiting', auto_reply_s=600)
    await runner.begin(meta.id, 'translate', [])
    session = factory.last
    question = asyncio.create_task(session.spec.on_permission('AskUserQuestion', {'questions': []}, 'q1'))
    await settle()
    assert runner.meta(meta.id).auto_reply_at is not None
    await runner.stop(meta.id)
    outcome = await question
    assert not outcome.allow and outcome.interrupt
    assert session.closed and len(session.sent) == 1
    assert store.load_meta(meta.id).auto_reply_at is None
    assert runner.meta(meta.id).status == 'error'
    await runner.shutdown()


async def test_stop_failure_is_not_reported_as_success(runner, factory):
    meta = runner.create('', 'running')
    await runner.begin(meta.id, 'work', [])
    session = factory.last
    original_close = session.close

    async def broken_close():
        raise RuntimeError('still running')

    session.close = broken_close
    with pytest.raises(SessionFailed, match='still running'):
        await runner.stop(meta.id)
    assert not session.closed
    session.close = original_close
    await runner.shutdown()
