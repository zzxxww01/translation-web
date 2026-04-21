import asyncio

import pytest

from src.services.translation_run_registry import TranslationRunRegistry


@pytest.mark.asyncio
async def test_claim_translation_slot_acquires_when_idle():
    registry = TranslationRunRegistry()

    async def cancel_callback(_project_id: str):
        return {"status": "not_found"}

    result = await registry.claim_translation_slot("project-a", cancel_callback)

    assert result["status"] == "acquired"
    active = registry.get_active_run()
    assert active is not None
    assert active.project_id == "project-a"
    assert active.status == "starting"


@pytest.mark.asyncio
async def test_claim_translation_slot_waits_for_cancelled_run_to_release():
    registry = TranslationRunRegistry()
    registry.set_active_run("project-a", run_id="run-1", status="processing")

    async def cancel_callback(project_id: str):
        registry.release_active_run(project_id, run_id="run-1")
        return {"status": "cancelling", "project_id": project_id}

    result = await registry.claim_translation_slot(
        "project-b",
        cancel_callback,
        wait_timeout=1.0,
        poll_interval=0.01,
    )

    assert result["status"] == "acquired_after_cancel"
    active = registry.get_active_run()
    assert active is not None
    assert active.project_id == "project-b"


def test_cancel_markers_are_tracked_per_project():
    registry = TranslationRunRegistry()

    registry.mark_cancelled("project-a")
    assert registry.is_cancelled("project-a") is True

    registry.clear_cancelled("project-a")
    assert registry.is_cancelled("project-a") is False
