from types import SimpleNamespace

import pytest

from src.api.routers.project_glossary import create_legacy_resume_job
from src.services.translation_resume_service import TranslationResumeCheckpoint


@pytest.mark.asyncio
async def test_legacy_term_review_endpoint_can_release_a_resume_immediately(
    tmp_path,
) -> None:
    project_manager = SimpleNamespace(
        projects_path=tmp_path,
        get=lambda _project_id: SimpleNamespace(title="Demo"),
    )
    checkpoint = TranslationResumeCheckpoint(
        project_id="demo",
        resumable=True,
        translated_paragraphs=70,
        total_paragraphs=75,
        translated_sections=3,
        total_sections=4,
        remaining_paragraphs=5,
        source_run_id="old-run",
        source_run_status="incomplete",
    )

    job = await create_legacy_resume_job(
        project_id="demo",
        pm=project_manager,
        model=None,
        checkpoint=checkpoint,
    )

    assert job["status"] == "succeeded"
    assert job["confirmation_status"] == "not_required"
    assert job["result"]["review_required"] is False
    assert job["result"]["resume_checkpoint"]["remaining_paragraphs"] == 5
