import asyncio

import pytest

from src.api.streaming.translation_stream_session import (
    TranslationStreamSession,
    resolve_live_conflict,
)


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
