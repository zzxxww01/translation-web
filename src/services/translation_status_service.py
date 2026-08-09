"""Lightweight translation status reads for frequently-polled API routes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.models import ProjectStatus
from src.core.project import ProjectManager, ProjectTranslationSummary
from src.llm.usage_metrics import llm_usage_metrics
from src.services.progress_tracker import ProgressTracker
from src.services.translation_artifact_service import TranslationArtifactService
from src.services.translation_run_registry import (
    TranslationRunRegistry,
    translation_run_registry,
)


class TranslationStatusService:
    """Read live or persisted status without constructing any LLM providers."""

    def __init__(
        self,
        project_manager: ProjectManager,
        progress_tracker: ProgressTracker,
        *,
        run_registry: TranslationRunRegistry = translation_run_registry,
        artifact_service: Optional[TranslationArtifactService] = None,
    ) -> None:
        self.project_manager = project_manager
        self.progress_tracker = progress_tracker
        self.run_registry = run_registry
        self.artifact_service = artifact_service or TranslationArtifactService(
            project_manager.projects_path
        )

    @staticmethod
    def _compact_usage(
        run_id: Optional[str],
        stored: Any = None,
    ) -> Optional[Dict[str, Any]]:
        usage = stored if isinstance(stored, dict) else None
        if usage is None and run_id:
            current = llm_usage_metrics.summary(run_id, include_calls=False)
            if current.get("api_calls"):
                usage = current
        if usage is None:
            return None
        return {key: value for key, value in usage.items() if key != "calls"}

    async def get_translation_progress(self, project_id: str) -> Dict[str, Any]:
        """Return current progress using memory first and cached disk summaries second."""

        progress = self.progress_tracker.get(project_id)
        active_run = self.run_registry.get_active_run(project_id)
        is_active_project = active_run is not None
        active_run_id = active_run.run_id if active_run else None
        if (
            progress is not None
            and is_active_project
            and (active_run_id is None or progress.run_id != active_run_id)
        ):
            progress = None

        def attach_active_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
            terminal_statuses = {"completed", "cancelled", "failed", "incomplete"}
            effective_status = str(
                payload.get("final_status") or payload.get("status") or ""
            )
            payload["active_project_id"] = (
                active_run.project_id if active_run else None
            )
            payload["active_run_id"] = active_run.run_id if active_run else None
            payload["can_stop"] = is_active_project and payload.get("status") in (
                "processing",
                "starting",
                "cancelling",
            )
            payload["is_cancelling"] = bool(
                effective_status not in terminal_statuses
                and (
                    (progress and progress.cancel_requested)
                    or (
                        is_active_project
                        and active_run
                        and active_run.status == "cancelling"
                    )
                    or payload.get("status") == "cancelling"
                )
            )
            run_id = payload.get("run_id")
            if run_id and "llm_usage" not in payload:
                usage = self._compact_usage(str(run_id))
                if usage is not None:
                    payload["llm_usage"] = usage
            return payload

        if progress:
            payload = progress.to_dict()
            if progress.final_status:
                return attach_active_fields(
                    {
                        "status": progress.final_status,
                        **payload,
                    }
                )

            stalled_seconds = max(
                int((datetime.now() - progress.last_updated_at).total_seconds()),
                0,
            )
            return attach_active_fields(
                {
                    "status": "completed" if progress.is_complete else "processing",
                    "stalled_seconds": stalled_seconds,
                    **payload,
                }
            )

        if is_active_project and active_run_id is None:
            project_summary = await asyncio.to_thread(
                self.project_manager.get_translation_summary,
                project_id,
            )
            latest_run = None
            latest_run_state = None
        else:
            project_summary, run_snapshot = await asyncio.gather(
                asyncio.to_thread(
                    self.project_manager.get_translation_summary,
                    project_id,
                ),
                asyncio.to_thread(
                    self.artifact_service.load_latest_run_snapshot,
                    project_id,
                ),
            )
            latest_run, latest_run_state = run_snapshot

        return self._build_persisted_payload(
            project_summary=project_summary,
            latest_run=latest_run,
            latest_run_state=latest_run_state,
            active_run=active_run,
            active_run_id=active_run_id,
            is_active_project=is_active_project,
            attach_active_fields=attach_active_fields,
        )

    async def cancel_translation(self, project_id: str) -> Dict[str, Any]:
        """Cancel a registered run without resolving or constructing an LLM."""

        active_run = self.run_registry.mark_active_cancelled(project_id)
        if active_run is None:
            self.run_registry.clear_cancelled(project_id)
            return {"status": "not_found", "project_id": project_id}

        progress = self.progress_tracker.get(project_id)
        if (
            progress is not None
            and not progress.final_status
            and progress.run_id == active_run.run_id
        ):
            progress.cancel_requested = True
            progress.current_step = "取消中"
            self.progress_tracker.touch(progress)
            if progress.run_id:
                await asyncio.to_thread(
                    self.artifact_service.write_run_state,
                    project_id,
                    progress.run_id,
                    {
                        "status": "processing",
                        **progress.to_dict(),
                    },
                )

        return {
            "status": "cancelling",
            "project_id": project_id,
            "run_id": active_run.run_id,
        }

    def _build_persisted_payload(
        self,
        *,
        project_summary: ProjectTranslationSummary,
        latest_run: Optional[Dict[str, Any]],
        latest_run_state: Any,
        active_run: Any,
        active_run_id: Optional[str],
        is_active_project: bool,
        attach_active_fields,
    ) -> Dict[str, Any]:
        total_paragraphs = project_summary.total_paragraphs
        translated = project_summary.translated_paragraphs
        translated_sections = project_summary.translated_sections
        total_sections = project_summary.total_sections
        is_complete = total_paragraphs > 0 and translated >= total_paragraphs
        latest_run_is_active = bool(
            is_active_project
            and active_run_id is not None
            and latest_run_state
            and latest_run_state.run_id == active_run_id
        )

        if is_active_project and active_run_id is None:
            return attach_active_fields(
                {
                    "status": active_run.status,
                    "current_step": (
                        active_run.current_step or active_run.status
                    ),
                    "progress_percent": (
                        translated / total_paragraphs * 100
                        if total_paragraphs > 0
                        else 0
                    ),
                    "translated_paragraphs": translated,
                    "total_paragraphs": total_paragraphs,
                    "is_complete": False,
                }
            )

        # A newly claimed worker may have a run id before its first progress or
        # run-state write. Do not surface an older run's completed summary in
        # that window: it hides the stop control and makes a live run look done.
        if is_active_project and active_run_id and not latest_run_is_active:
            return attach_active_fields(
                {
                    "status": active_run.status,
                    "progress_percent": (
                        translated / total_paragraphs * 100
                        if total_paragraphs > 0
                        else 0
                    ),
                    "translated_paragraphs": translated,
                    "total_paragraphs": total_paragraphs,
                    "translated_sections": translated_sections,
                    "total_sections": total_sections,
                    "current_step": (
                        active_run.current_step or active_run.status
                    ),
                    "is_complete": False,
                    "started_at": active_run.started_at,
                    "last_updated_at": active_run.updated_at,
                    "run_id": active_run_id,
                }
            )

        if (
            latest_run_is_active
            and latest_run
            and latest_run_state
            and latest_run_state.run_id != str(latest_run.get("run_id") or "")
        ):
            return attach_active_fields(
                {
                    "status": latest_run_state.status,
                    "progress_percent": (
                        translated / total_paragraphs * 100
                        if total_paragraphs > 0
                        else 0
                    ),
                    "translated_paragraphs": translated,
                    "total_paragraphs": total_paragraphs,
                    "translated_sections": translated_sections,
                    "total_sections": total_sections,
                    "current_section": latest_run_state.current_section,
                    "current_step": latest_run_state.current_step,
                    "is_complete": False,
                    "error_count": latest_run_state.error_count,
                    "started_at": latest_run_state.started_at,
                    "last_updated_at": latest_run_state.updated_at,
                    "finished_at": latest_run_state.finished_at,
                    "final_status": None,
                    "run_id": latest_run_state.run_id,
                }
            )

        if latest_run:
            latest_status = str(latest_run.get("status") or "").strip() or "processing"
            latest_total = int(
                latest_run.get("total_paragraphs") or total_paragraphs or 0
            )
            latest_translated = int(
                latest_run.get("translated_paragraphs") or translated or 0
            )
            return attach_active_fields(
                {
                    "status": latest_status,
                    "progress_percent": (
                        latest_translated / latest_total * 100
                        if latest_total > 0
                        else 0
                    ),
                    "translated_paragraphs": latest_translated,
                    "total_paragraphs": latest_total,
                    "translated_sections": int(
                        latest_run.get("translated_sections") or 0
                    ),
                    "total_sections": int(
                        latest_run.get("total_sections") or total_sections
                    ),
                    "current_section": (
                        latest_run_state.current_section if latest_run_state else None
                    ),
                    "current_step": (
                        latest_run_state.current_step
                        if latest_run_state
                        else latest_status
                    ),
                    "is_complete": latest_status == "completed",
                    "error_count": int(latest_run.get("error_count") or 0),
                    "started_at": latest_run.get("started_at"),
                    "last_updated_at": (
                        latest_run_state.updated_at if latest_run_state else None
                    ),
                    "finished_at": latest_run.get("finished_at"),
                    "final_status": latest_status,
                    "run_id": latest_run.get("run_id")
                    or (latest_run_state.run_id if latest_run_state else None),
                    "llm_usage": self._compact_usage(
                        str(latest_run.get("run_id") or ""),
                        latest_run.get("llm_usage"),
                    ),
                }
            )

        if latest_run_is_active and latest_run_state:
            return attach_active_fields(
                {
                    "status": latest_run_state.status,
                    "progress_percent": (
                        translated / total_paragraphs * 100
                        if total_paragraphs > 0
                        else 0
                    ),
                    "translated_paragraphs": translated,
                    "total_paragraphs": total_paragraphs,
                    "translated_sections": translated_sections,
                    "total_sections": total_sections,
                    "current_section": latest_run_state.current_section,
                    "current_step": latest_run_state.current_step,
                    "is_complete": False,
                    "error_count": latest_run_state.error_count,
                    "started_at": latest_run_state.started_at,
                    "last_updated_at": latest_run_state.updated_at,
                    "finished_at": latest_run_state.finished_at,
                    "final_status": None,
                    "run_id": latest_run_state.run_id,
                }
            )

        if is_complete and project_summary.status in (
            ProjectStatus.REVIEWING,
            ProjectStatus.COMPLETED,
        ):
            status = "completed"
        elif is_active_project and project_summary.status in (
            ProjectStatus.ANALYZING,
            ProjectStatus.IN_PROGRESS,
        ):
            status = "processing"
        elif translated > 0:
            status = "partial"
        else:
            status = "not_started"

        return attach_active_fields(
            {
                "status": status,
                "progress_percent": (
                    translated / total_paragraphs * 100
                    if total_paragraphs > 0
                    else 0
                ),
                "translated_paragraphs": translated,
                "total_paragraphs": total_paragraphs,
                "is_complete": is_complete,
            }
        )
