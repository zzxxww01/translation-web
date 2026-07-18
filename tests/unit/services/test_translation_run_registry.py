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
async def test_claim_translation_slot_allows_a_different_project():
    registry = TranslationRunRegistry()
    registry.set_active_run("project-a", run_id="run-1", status="processing")

    result = await registry.claim_translation_slot("project-b")

    assert result["status"] == "acquired"
    assert registry.get_active_run("project-a").run_id == "run-1"
    assert registry.get_active_run("project-b").status == "starting"


@pytest.mark.asyncio
async def test_claim_translation_slot_rejects_duplicate_project_run():
    registry = TranslationRunRegistry()
    registry.set_active_run("project-a", run_id="run-1", status="processing")

    result = await registry.claim_translation_slot("project-a")

    assert result == {
        "status": "busy",
        "project_id": "project-a",
        "active_project_id": "project-a",
        "active_run_id": "run-1",
        "active_status": "processing",
    }


def test_cancel_markers_are_tracked_per_project():
    registry = TranslationRunRegistry()

    registry.mark_cancelled("project-a")
    assert registry.is_cancelled("project-a") is True

    registry.clear_cancelled("project-a")
    assert registry.is_cancelled("project-a") is False


@pytest.mark.asyncio
async def test_new_slot_clears_stale_marker_but_preserves_early_stop():
    registry = TranslationRunRegistry()
    registry.mark_cancelled("project-a")

    claimed = await registry.claim_translation_slot("project-a")
    assert claimed["status"] == "acquired"
    assert registry.is_cancelled("project-a") is False

    active = registry.mark_active_cancelled("project-a")
    assert active is not None
    assert active.lease_id == claimed["lease_id"]
    assert active.status == "cancelling"
    assert registry.is_cancelled("project-a") is True


@pytest.mark.asyncio
async def test_stop_cannot_mark_a_new_lease_through_a_stale_snapshot():
    registry = TranslationRunRegistry()
    first = await registry.claim_translation_slot("project-a")
    registry.release_active_run("project-a", lease_id=first["lease_id"])
    second = await registry.claim_translation_slot("project-a")

    assert second["lease_id"] != first["lease_id"]
    assert registry.is_cancelled("project-a") is False


@pytest.mark.asyncio
async def test_old_lease_cannot_release_a_new_run():
    registry = TranslationRunRegistry()
    first = await registry.claim_translation_slot("project-a")
    registry.set_active_run("project-a", run_id="run-1", status="processing")
    registry.release_active_run("project-a", run_id="run-1")

    second = await registry.claim_translation_slot("project-a")
    assert second["status"] == "acquired"
    assert second["lease_id"] != first["lease_id"]

    registry.release_active_run("project-a", lease_id=first["lease_id"])

    active = registry.get_active_run("project-a")
    assert active is not None
    assert active.lease_id == second["lease_id"]
