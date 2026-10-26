import asyncio

import pytest

from skill_runner.runner import Conflict, SessionFailed
from skill_runner_fakes import settle


@pytest.mark.asyncio
async def test_update_gate_blocks_new_and_resumed_conversations(runner, factory):
    meta = runner.create("", "old")
    await runner.begin(meta.id, "hello", [])
    factory.last.push({"type": "session", "session_id": "thread"})
    factory.last.push({"type": "result", "is_error": False})
    await settle()
    runner.reserve_runtime_update()
    await runner.close_idle_for_runtime_update()
    assert factory.last.closed
    with pytest.raises(Conflict):
        runner.create("", "new")
    with pytest.raises(Conflict):
        await runner.send_message(meta.id, "continue", [])
    runner.release_runtime_update()
    await runner.send_message(meta.id, "continue", [])
    assert factory.last.spec.resume == "thread"
    await runner.shutdown()


@pytest.mark.asyncio
async def test_update_cannot_race_with_session_startup(runner, factory):
    opening = asyncio.Event()
    release = asyncio.Event()
    original = runner.session_factory

    async def slow_open(spec):
        opening.set()
        await release.wait()
        return await original(spec)

    runner.session_factory = slow_open
    meta = runner.create("", "new")
    delivery = asyncio.create_task(runner.begin(meta.id, "hello", []))
    await opening.wait()
    with pytest.raises(Conflict):
        runner.reserve_runtime_update()
    release.set()
    await delivery
    await runner.shutdown()


@pytest.mark.asyncio
async def test_update_rejects_waiting_and_running_work(runner, factory):
    meta = runner.create("", "new")
    await runner.begin(meta.id, "hello", [])
    with pytest.raises(Conflict):
        runner.reserve_runtime_update()
    factory.last.push({"type": "text", "text": "Review this 【等待确认】"})
    factory.last.push({"type": "result", "is_error": False})
    await settle()
    assert runner.meta(meta.id).awaiting_reply
    with pytest.raises(Conflict):
        runner.reserve_runtime_update()
    await runner.shutdown()


async def make_idle(runner, factory):
    meta = runner.create("", "idle")
    await runner.begin(meta.id, "hello", [])
    factory.last.push({"type": "result", "is_error": False})
    await settle()
    return meta, factory.last, runner._runs[meta.id]


async def test_failed_close_remains_tracked_on_update_retry(runner, factory):
    _, session, run = await make_idle(runner, factory)
    original_close = session.close
    attempts = 0
    async def fail_close():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("close failed")
    session.close = fail_close
    try:
        for _ in range(2):
            runner.reserve_runtime_update()
            with pytest.raises(RuntimeError, match="close failed"):
                await runner.close_idle_for_runtime_update()
            runner.release_runtime_update()
            assert run.session is session and run.closing
            assert run.pump is None
        assert attempts == 2
        session.close = original_close
        runner.reserve_runtime_update()
        await runner.close_idle_for_runtime_update()
        assert session.closed and run.session is None and not run.closing
    finally:
        runner.release_runtime_update()
        session.close = original_close
        await runner.shutdown()


@pytest.mark.parametrize("fails", [False, True])
async def test_update_waits_for_idle_close_and_rechecks_failed_close(runner, factory, fails):
    from dataclasses import replace
    _, session, run = await make_idle(runner, factory)
    runner._cancel_idle(run)
    runner.config = replace(runner.config, idle_timeout_s=0)
    entered, release = asyncio.Event(), asyncio.Event()
    original_close = session.close
    attempts = 0
    async def slow_close():
        nonlocal attempts
        attempts += 1
        entered.set()
        await release.wait()
        if fails:
            raise RuntimeError("close failed")
        await original_close()
    session.close = slow_close
    idle_close = asyncio.create_task(runner._idle_close(run))
    run.idle_task = idle_close
    update_close = None
    try:
        await entered.wait()
        # Closing streams must not revive a run or trigger auto replies.
        session.push({"type": "text", "text": "late output"})
        await settle()
        assert run.meta.status == "idle"
        runner.reserve_runtime_update()
        update_close = asyncio.create_task(runner.close_idle_for_runtime_update())
        await settle()
        assert not update_close.done() and attempts == 1
        release.set()
        await idle_close
        if fails:
            with pytest.raises(RuntimeError, match="close failed"):
                await update_close
            assert attempts == 2 and run.session is session and run.closing
        else:
            await update_close
            assert attempts == 1 and session.closed and run.session is None
    finally:
        release.set()
        await asyncio.gather(*(task for task in (idle_close, update_close) if task), return_exceptions=True)
        runner.release_runtime_update()
        session.close = original_close
        await runner.shutdown()


async def test_delivery_closes_failed_session_before_reopening(runner, factory):
    meta, session, run = await make_idle(runner, factory)
    original_close = session.close
    async def fail_close():
        raise RuntimeError("close failed")
    session.close = fail_close
    try:
        await runner._close_session(run)
        with pytest.raises(SessionFailed, match="关闭"):
            await runner.send_message(meta.id, "continue", [])
        assert len(factory.sessions) == 1 and session.sent == ["hello"]
        session.close = original_close
        await runner.send_message(meta.id, "continue", [])
        assert session.closed and len(factory.sessions) == 2
        assert factory.last.sent == ["continue"]
    finally:
        session.close = original_close
        await runner.shutdown()


async def test_delete_cannot_discard_session_when_close_fails(runner, factory):
    meta, session, run = await make_idle(runner, factory)
    original_close = session.close
    async def fail_close():
        raise RuntimeError("close failed")
    session.close = fail_close
    try:
        with pytest.raises(Exception, match="close failed"):
            await runner.delete(meta.id)
        assert runner._runs[meta.id] is run and run.session is session
        assert runner.store.load_meta(meta.id) is not None
    finally:
        session.close = original_close
        await runner.shutdown()


async def test_old_pump_failure_cannot_close_replacement_session(runner, factory):
    meta, old_session, run = await make_idle(runner, factory)
    await runner._close_session(run)
    await runner.send_message(meta.id, "continue", [])
    replacement = factory.last
    old_session._queue = asyncio.Queue()
    old_session.push(RuntimeError("old stream failed after close"))
    try:
        await runner._pump(run, old_session)
        assert run.session is replacement and not replacement.closed
        assert run.meta.status == "running"
    finally:
        await runner.shutdown()


async def test_cancelled_close_remains_tracked_for_maintenance_retry(runner, factory):
    _, session, run = await make_idle(runner, factory)
    original_close = session.close
    entered = asyncio.Event()
    async def slow_close():
        entered.set()
        await asyncio.Event().wait()
    session.close = slow_close
    closing = asyncio.create_task(runner._close_session(run, strict=True))
    await entered.wait()
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing
    try:
        assert run.session is session and run.closing and run.pump is None
        session.close = original_close
        runner.reserve_runtime_update()
        await runner.close_idle_for_runtime_update()
        assert session.closed and run.session is None
    finally:
        session.close = original_close
        runner.release_runtime_update()
        await runner.shutdown()


async def test_update_cannot_interrupt_codex_queued_followup(runner, monkeypatch):
    from dataclasses import replace
    from skill_runner.codex_session import CodexSession
    first_started, first_release = asyncio.Event(), asyncio.Event()
    second_started, second_release = asyncio.Event(), asyncio.Event()
    turns = 0
    session = None
    async def controlled_turn(self, prompt):
        nonlocal turns
        turns += 1
        started, release = (first_started, first_release) if turns == 1 else (second_started, second_release)
        started.set()
        await release.wait()
        await self._queue.put(self._mapper.result(is_error=False))
    monkeypatch.setattr(CodexSession, "_turn", controlled_turn)
    async def factory(spec):
        nonlocal session
        session = await CodexSession.open(runner.config, spec)
        return session
    runner.session_factory = factory
    meta = runner.create("", "queued", "codex")
    try:
        await runner.begin(meta.id, "first", [])
        await first_started.wait()
        await runner.send_message(meta.id, "second", [])
        first_release.set()
        await second_started.wait()
        await settle()
        # The first result is already displayed, but the accepted follow-up is running.
        assert runner.meta(meta.id).status == "idle"
        with pytest.raises(Conflict):
            runner.reserve_runtime_update()
        with pytest.raises(Conflict):
            await runner.delete(meta.id)
        assert runner.active_count() == 1
        run = runner._runs[meta.id]
        runner._cancel_idle(run)
        runner.config = replace(runner.config, idle_timeout_s=0)
        await runner._idle_close(run)
        assert run.session is session and not session._closed
        runner._cancel_idle(run)
        runner.config = replace(runner.config, idle_timeout_s=60)
        second_release.set()
        await settle()
        assert not session.busy
        runner.reserve_runtime_update()
        await runner.close_idle_for_runtime_update()
        assert session._closed and session._worker.done()
    finally:
        first_release.set()
        second_release.set()
        runner.release_runtime_update()
        await runner.shutdown()
