import pytest

from src.core.models import Paragraph, Section
from src.services.translation_artifact_service import TranslationArtifactService
from src.services.translation_resume_service import inspect_translation_resume


class _ProjectManager:
    def __init__(self, projects_path, sections):
        self.projects_path = projects_path
        self._sections = sections

    def get_sections(self, _project_id):
        return [section.model_copy(deep=True) for section in self._sections]


def _partial_sections():
    completed = Paragraph(id="p1", index=0, source="one")
    completed.add_translation("一", "pro")
    return [
        Section(
            section_id="s1",
            title="First",
            paragraphs=[
                completed,
                Paragraph(id="p2", index=1, source="two"),
            ],
        )
    ]


def test_partial_manual_work_without_a_prior_run_is_not_a_resume(tmp_path):
    manager = _ProjectManager(tmp_path, _partial_sections())

    checkpoint = inspect_translation_resume(manager, "demo")

    assert checkpoint.translated_paragraphs == 1
    assert checkpoint.remaining_paragraphs == 1
    assert checkpoint.resumable is False


@pytest.mark.parametrize(
    "run_status",
    ["cancelled", "failed", "incomplete", "processing"],
)
def test_terminated_run_with_persisted_paragraphs_is_resumable(
    tmp_path,
    run_status,
):
    manager = _ProjectManager(tmp_path, _partial_sections())
    artifacts = TranslationArtifactService(tmp_path)
    run_id, run_dir = artifacts.create_run_artifact_dir("demo")
    artifacts.write_json(
        run_dir / "run-summary.json",
        {
            "run_id": run_id,
            "status": run_status,
            "translated_paragraphs": 1,
            "total_paragraphs": 2,
        },
    )

    checkpoint = inspect_translation_resume(manager, "demo")

    assert checkpoint.resumable is True
    assert checkpoint.source_run_id == run_id
    assert checkpoint.source_run_status == run_status
    assert checkpoint.to_dict()["remaining_paragraphs"] == 1


def test_completed_checkpoint_is_not_resumed(tmp_path):
    sections = _partial_sections()
    sections[0].paragraphs[1].add_translation("二", "pro")
    manager = _ProjectManager(tmp_path, sections)
    artifacts = TranslationArtifactService(tmp_path)
    run_id, run_dir = artifacts.create_run_artifact_dir("demo")
    artifacts.write_json(
        run_dir / "run-summary.json",
        {"run_id": run_id, "status": "completed"},
    )

    checkpoint = inspect_translation_resume(manager, "demo")

    assert checkpoint.translated_paragraphs == 2
    assert checkpoint.remaining_paragraphs == 0
    assert checkpoint.resumable is False


def test_partial_project_from_completed_run_is_not_resumed(tmp_path):
    manager = _ProjectManager(tmp_path, _partial_sections())
    artifacts = TranslationArtifactService(tmp_path)
    run_id, run_dir = artifacts.create_run_artifact_dir("demo")
    artifacts.write_json(
        run_dir / "run-summary.json",
        {"run_id": run_id, "status": "completed"},
    )

    checkpoint = inspect_translation_resume(manager, "demo")

    assert checkpoint.translated_paragraphs == 1
    assert checkpoint.remaining_paragraphs == 1
    assert checkpoint.resumable is False
