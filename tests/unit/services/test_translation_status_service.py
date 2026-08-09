import json

import pytest

from src.core.models import Paragraph, ProjectMeta, ProjectStatus, Section
from src.core.project import ProjectManager
from src.services.progress_tracker import ProgressTracker
from src.services.translation_run_registry import TranslationRunRegistry
from src.services.translation_status_service import TranslationStatusService


@pytest.mark.asyncio
async def test_persisted_status_uses_cached_project_translation_summary(tmp_path):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager.save_meta(
        ProjectMeta(
            id="demo",
            title="Demo",
            source_file="source.md",
            status=ProjectStatus.REVIEWING,
            progress={"total_sections": 1, "total_paragraphs": 1},
        )
    )
    paragraph = Paragraph(id="p1", index=0, source="Source")
    paragraph.add_translation("译文", "pro")
    manager.save_section_only(
        "demo",
        Section(section_id="s1", title="Section", paragraphs=[paragraph]),
    )
    service = TranslationStatusService(
        project_manager=manager,
        progress_tracker=ProgressTracker(),
        run_registry=TranslationRunRegistry(),
    )

    payload = await service.get_translation_progress("demo")

    assert payload["status"] == "completed"
    assert payload["translated_paragraphs"] == 1
    assert payload["total_paragraphs"] == 1
    assert payload["is_complete"] is True


@pytest.mark.asyncio
async def test_live_status_never_touches_project_disk(tmp_path, monkeypatch):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    tracker = ProgressTracker()
    registry = TranslationRunRegistry()
    progress = tracker.create(
        "demo",
        total_sections=2,
        total_paragraphs=10,
        original_status=ProjectStatus.CREATED,
    )
    progress.run_id = "run-1"
    progress.translated_paragraphs = 3
    registry.set_active_run("demo", run_id="run-1", status="processing")
    monkeypatch.setattr(
        manager,
        "get_translation_summary",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("live in-memory status must not scan project files")
        ),
    )
    service = TranslationStatusService(
        project_manager=manager,
        progress_tracker=tracker,
        run_registry=registry,
    )

    payload = await service.get_translation_progress("demo")

    assert payload["status"] == "processing"
    assert payload["translated_paragraphs"] == 3
    assert payload["active_run_id"] == "run-1"


@pytest.mark.asyncio
async def test_cancel_does_not_need_llm_and_persists_cancelling_state(tmp_path):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    tracker = ProgressTracker()
    registry = TranslationRunRegistry()
    progress = tracker.create(
        "demo",
        total_sections=1,
        total_paragraphs=1,
        original_status=ProjectStatus.CREATED,
    )
    progress.run_id = "run-1"
    registry.set_active_run("demo", run_id="run-1", status="processing")
    run_dir = manager.projects_path / "demo" / "artifacts" / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    service = TranslationStatusService(
        project_manager=manager,
        progress_tracker=tracker,
        run_registry=registry,
    )

    result = await service.cancel_translation("demo")

    assert result == {
        "status": "cancelling",
        "project_id": "demo",
        "run_id": "run-1",
    }
    assert progress.cancel_requested is True
    assert registry.is_cancelled("demo") is True
    state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
    assert state["cancel_requested"] is True
    assert state["current_step"] == "取消中"


@pytest.mark.asyncio
async def test_new_active_run_does_not_report_previous_completed_summary(tmp_path):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager.save_meta(
        ProjectMeta(
            id="demo",
            title="Demo",
            source_file="source.md",
            status=ProjectStatus.REVIEWING,
            progress={"total_sections": 1, "total_paragraphs": 1},
        )
    )
    paragraph = Paragraph(id="p1", index=0, source="Source")
    paragraph.add_translation("旧译文", "pro")
    manager.save_section_only(
        "demo",
        Section(section_id="s1", title="Section", paragraphs=[paragraph]),
    )
    old_run_dir = manager.projects_path / "demo" / "artifacts" / "runs" / "old-run"
    old_run_dir.mkdir(parents=True)
    (old_run_dir / "run-summary.json").write_text(
        json.dumps(
            {
                "run_id": "old-run",
                "status": "completed",
                "translated_paragraphs": 1,
                "total_paragraphs": 1,
            }
        ),
        encoding="utf-8",
    )
    registry = TranslationRunRegistry()
    registry.set_active_run(
        "demo",
        run_id="new-run",
        status="starting",
        current_step="等待术语确认",
    )
    service = TranslationStatusService(
        project_manager=manager,
        progress_tracker=ProgressTracker(),
        run_registry=registry,
    )

    payload = await service.get_translation_progress("demo")

    assert payload["status"] == "starting"
    assert payload["run_id"] == "new-run"
    assert payload["active_run_id"] == "new-run"
    assert payload["current_step"] == "等待术语确认"
    assert payload["is_complete"] is False
    assert payload["can_stop"] is True
