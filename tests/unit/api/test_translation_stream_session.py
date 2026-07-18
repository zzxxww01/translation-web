import asyncio

import pytest

from src.api.streaming.translation_stream_session import (
    TranslationStreamSession,
    resolve_live_conflict,
)
from src.core.models import TermConflict


class DummyRequest:
    def __init__(self, *, disconnect_after: int | None = None):
        self.disconnect_checks = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self):
        self.disconnect_checks += 1
        if self.disconnect_after is not None:
            return self.disconnect_checks >= self.disconnect_after
        return False


@pytest.mark.asyncio
async def test_resolve_live_conflict_returns_false_without_waiter():
    resolved = resolve_live_conflict("demo-project", "GPU", "GPU", True)
    assert resolved is False


@pytest.mark.asyncio
async def test_translation_stream_session_emits_complete_event():
    request = DummyRequest()
    released = []

    async def fake_run_translation(on_progress, _on_term_conflict):
        on_progress("working", 1, 2)
        await asyncio.sleep(0)
        return {"status": "completed", "translated_paragraphs": 2}

    async def fake_cancel_translation(_project_id: str):
        return {"status": "cancelling"}

    session = TranslationStreamSession(
        project_id="demo-project",
        request=request,
        total_paragraphs=2,
        total_sections=1,
        run_translation=fake_run_translation,
        cancel_translation=fake_cancel_translation,
        release_slot=lambda project_id: released.append(project_id),
    )

    events = []
    async for chunk in session.generate():
        events.append(chunk)
        if '"type": "complete"' in chunk:
            break

    assert any('"type": "start"' in chunk for chunk in events)
    assert any('"type": "progress"' in chunk for chunk in events)
    assert any('"type": "complete"' in chunk for chunk in events)
    assert released == ["demo-project"]


@pytest.mark.asyncio
async def test_translation_continues_after_client_disconnect():
    request = DummyRequest(disconnect_after=1)
    cancelled = []
    released = []
    completed = asyncio.Event()

    async def fake_run_translation(_on_progress, _on_term_conflict):
        await asyncio.sleep(0.01)
        completed.set()
        return {"status": "completed", "translated_paragraphs": 2}

    async def fake_cancel_translation(project_id: str):
        cancelled.append(project_id)
        return {"status": "cancelling"}

    session = TranslationStreamSession(
        project_id="demo-project",
        request=request,
        total_paragraphs=2,
        total_sections=1,
        run_translation=fake_run_translation,
        cancel_translation=fake_cancel_translation,
        release_slot=lambda project_id: released.append(project_id),
    )

    events = [chunk async for chunk in session.generate()]

    await asyncio.wait_for(completed.wait(), timeout=1)

    assert any('"type": "start"' in chunk for chunk in events)
    assert cancelled == []
    assert released == ["demo-project"]


@pytest.mark.asyncio
async def test_closing_after_start_frame_does_not_leak_worker_or_slot():
    request = DummyRequest()
    released = []
    completed = asyncio.Event()

    async def fake_run_translation(_on_progress, _on_term_conflict):
        await asyncio.sleep(0.01)
        completed.set()
        return {"status": "completed", "translated_paragraphs": 1}

    async def fake_cancel_translation(_project_id: str):
        raise AssertionError("detaching the stream must not cancel the worker")

    session = TranslationStreamSession(
        project_id="close-after-start",
        request=request,
        total_paragraphs=1,
        total_sections=1,
        run_translation=fake_run_translation,
        cancel_translation=fake_cancel_translation,
        release_slot=lambda project_id: released.append(project_id),
    )

    stream = session.generate()
    first_frame = await anext(stream)
    assert '"type": "start"' in first_frame
    await stream.aclose()

    await asyncio.wait_for(completed.wait(), timeout=1)
    await asyncio.sleep(0)
    assert released == ["close-after-start"]


@pytest.mark.asyncio
async def test_parallel_same_term_conflicts_are_serialized_and_reuse_resolution():
    session = TranslationStreamSession(
        project_id="parallel-conflict",
        request=DummyRequest(),
        total_paragraphs=2,
        total_sections=2,
        run_translation=lambda *_args: None,
        cancel_translation=lambda *_args: None,
        release_slot=lambda _project_id: None,
    )
    session._init_conflict_state()
    first_conflict = TermConflict(
        term="token",
        existing_translation="token",
        new_translation="词元",
        new_section_id="s1",
    )
    second_conflict = first_conflict.model_copy(
        update={"new_translation": "令牌", "new_section_id": "s2"}
    )

    first_task = asyncio.create_task(
        session._handle_term_conflict_on_main(first_conflict)
    )
    second_task = asyncio.create_task(
        session._handle_term_conflict_on_main(second_conflict)
    )
    event = await asyncio.wait_for(session._progress_queue.get(), timeout=1)
    assert event["type"] == "term_conflict"

    assert resolve_live_conflict(
        "parallel-conflict",
        "token",
        "token",
        True,
    )
    first_result, second_result = await asyncio.wait_for(
        asyncio.gather(first_task, second_task),
        timeout=1,
    )

    assert first_result == second_result == {
        "chosen_translation": "token",
        "apply_to_all": True,
    }
    assert session._progress_queue.empty()
    session._clear_conflict_state()


@pytest.mark.asyncio
async def test_old_session_cannot_clear_new_session_conflict_state():
    def make_session():
        return TranslationStreamSession(
            project_id="reused-project",
            request=DummyRequest(),
            total_paragraphs=1,
            total_sections=1,
            run_translation=lambda *_args: None,
            cancel_translation=lambda *_args: None,
            release_slot=lambda _project_id: None,
        )

    old_session = make_session()
    new_session = make_session()
    old_session._init_conflict_state()
    new_session._init_conflict_state()

    old_session._clear_conflict_state()
    conflict = TermConflict(
        term="GPU",
        existing_translation="GPU",
        new_translation="图形处理器",
    )
    waiter = asyncio.create_task(
        new_session._handle_term_conflict_on_main(conflict)
    )
    await asyncio.wait_for(new_session._progress_queue.get(), timeout=1)

    assert resolve_live_conflict(
        "reused-project",
        "GPU",
        "GPU",
        True,
    )
    assert await asyncio.wait_for(waiter, timeout=1) == {
        "chosen_translation": "GPU",
        "apply_to_all": True,
    }
    new_session._clear_conflict_state()
