"""Inspect durable paragraph checkpoints for long-form resume runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from src.services.translation_artifact_service import TranslationArtifactService


RESUMABLE_RUN_STATUSES = {
    "cancelled",
    "cancelling",
    "failed",
    "incomplete",
    "processing",
    "starting",
}


@dataclass(frozen=True)
class TranslationResumeCheckpoint:
    """A read-only snapshot of the paragraphs already committed to disk."""

    project_id: str
    resumable: bool
    translated_paragraphs: int
    total_paragraphs: int
    translated_sections: int
    total_sections: int
    remaining_paragraphs: int
    source_run_id: Optional[str] = None
    source_run_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_translation_resume(
    project_manager,
    project_id: str,
) -> TranslationResumeCheckpoint:
    """Return whether a terminated long-form run has a usable disk checkpoint.

    Paragraph snapshots are the source of truth: a resumed run may skip only
    text that was successfully merged into the project, never an in-memory LLM
    result or a half-written phase artifact. A prior run artifact is required so
    a project containing a few manual translations is not mistaken for a
    terminated full-translation task.
    """

    sections = project_manager.get_sections(project_id)
    total_paragraphs = sum(len(section.paragraphs) for section in sections)
    translated_paragraphs = sum(
        1
        for section in sections
        for paragraph in section.paragraphs
        if paragraph.has_usable_translation()
    )
    translated_sections = sum(
        1
        for section in sections
        if section.paragraphs
        and all(
            paragraph.has_usable_translation()
            for paragraph in section.paragraphs
        )
    )

    artifact_service = TranslationArtifactService(project_manager.projects_path)
    latest_summary, latest_state = artifact_service.load_latest_run_snapshot(
        project_id
    )
    source_run_id: Optional[str] = None
    source_run_status: Optional[str] = None
    if latest_state is not None:
        source_run_id = latest_state.run_id
        source_run_status = latest_state.status.strip().lower() or None
    elif latest_summary is not None:
        source_run_id = str(latest_summary.get("run_id") or "").strip() or None
        source_run_status = (
            str(latest_summary.get("status") or "").strip().lower() or None
        )
    has_prior_run = bool(source_run_id or latest_summary)
    resumable = bool(
        has_prior_run
        and 0 < translated_paragraphs < total_paragraphs
        and (source_run_status or "processing") in RESUMABLE_RUN_STATUSES
    )

    return TranslationResumeCheckpoint(
        project_id=project_id,
        resumable=resumable,
        translated_paragraphs=translated_paragraphs,
        total_paragraphs=total_paragraphs,
        translated_sections=translated_sections,
        total_sections=len(sections),
        remaining_paragraphs=max(
            total_paragraphs - translated_paragraphs,
            0,
        ),
        source_run_id=source_run_id,
        source_run_status=source_run_status or None,
    )
