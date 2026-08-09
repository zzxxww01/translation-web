import asyncio
import threading
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from src.api.routers import confirmation_translation


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/projects/demo/translate-all",
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )


@pytest.mark.asyncio
async def test_confirmation_start_returns_before_background_translation_finishes():
    started = threading.Event()
    allow_finish = threading.Event()
    releases = []

    class FakeService:
        project_manager = SimpleNamespace(get=lambda _project_id: object())

        async def claim_translation_slot(self, project_id):
            return {
                "status": "acquired",
                "project_id": project_id,
                "run_id": None,
                "lease_id": "lease-1",
            }

        async def translate_project(self, project_id):
            started.set()
            while not allow_finish.is_set():
                await asyncio.sleep(0.01)
            return {"project_id": project_id, "status": "completed"}

        def _release_active_run(self, project_id, **kwargs):
            releases.append((project_id, kwargs))

    response = await confirmation_translation.start_translation(
        _request(),
        "demo",
        FakeService(),
    )

    assert response == {
        "status": "started",
        "project_id": "demo",
        "run_id": None,
    }
    assert await asyncio.to_thread(started.wait, 1)
    assert confirmation_translation._confirmation_translation_tasks

    allow_finish.set()
    for _ in range(100):
        if not confirmation_translation._confirmation_translation_tasks:
            break
        await asyncio.sleep(0.01)

    assert not confirmation_translation._confirmation_translation_tasks
    assert releases == [("demo", {"lease_id": "lease-1"})]


@pytest.mark.asyncio
async def test_confirmation_start_rejects_missing_project_before_claiming_slot():
    class MissingProjectManager:
        def get(self, _project_id):
            raise FileNotFoundError("missing")

    class FakeService:
        project_manager = MissingProjectManager()

        async def claim_translation_slot(self, _project_id):
            raise AssertionError("missing projects must not claim a translation slot")

    with pytest.raises(confirmation_translation.NotFoundException):
        await confirmation_translation.start_translation(
            _request(),
            "missing",
            FakeService(),
        )
