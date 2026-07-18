import pytest

from src.core.models import ProjectStatus
from src.services.batch_translation_service import BatchTranslationService
from src.services.batch_translation_types import TranslationProgress
from src.services.progress_tracker import ProgressTracker
from src.services.translation_run_registry import TranslationRunRegistry


@pytest.mark.asyncio
async def test_cancel_completed_progress_does_not_recreate_active_slot() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    service._run_registry = TranslationRunRegistry()
    service._progress_tracker = ProgressTracker()
    progress = TranslationProgress(
        project_id="demo",
        total_sections=1,
        total_paragraphs=1,
        original_status=ProjectStatus.CREATED,
    )
    progress.run_id = "finished-run"
    progress.final_status = "completed"
    service._progress_tracker._cache["demo"] = progress

    result = await service.cancel_translation("demo")

    assert result == {"status": "not_found", "project_id": "demo"}
    assert service._run_registry.get_active_run("demo") is None
    assert service._run_registry.is_cancelled("demo") is False


@pytest.mark.asyncio
async def test_cancel_atomically_marks_the_current_active_lease() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    service._run_registry = TranslationRunRegistry()
    service._progress_tracker = ProgressTracker()
    claimed = await service._run_registry.claim_translation_slot("demo")

    result = await service.cancel_translation("demo")

    active = service._run_registry.get_active_run("demo")
    assert result == {
        "status": "cancelling",
        "project_id": "demo",
        "run_id": None,
    }
    assert active is not None
    assert active.lease_id == claimed["lease_id"]
    assert active.status == "cancelling"
    assert service._run_registry.is_cancelled("demo") is True
