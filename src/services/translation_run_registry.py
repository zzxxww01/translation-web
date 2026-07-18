"""Shared translation run registry."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Set
from uuid import uuid4


@dataclass
class RunStateSnapshot:
    run_id: str
    status: str
    current_step: str
    current_section: Optional[str]
    updated_at: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    error_count: int = 0


@dataclass
class ActiveRunLock:
    project_id: str
    run_id: Optional[str]
    lease_id: str
    status: str
    started_at: str
    updated_at: str


class TranslationRunRegistry:
    """Track active longform runs independently for each project."""

    def __init__(self) -> None:
        self._cancelled_projects: Set[str] = set()
        self._cancelled_lock = threading.Lock()
        self._active_run_lock = threading.Lock()
        self._active_runs: Dict[str, ActiveRunLock] = {}

    def is_cancelled(self, project_id: str) -> bool:
        with self._cancelled_lock:
            return project_id in self._cancelled_projects

    def mark_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.add(project_id)

    def mark_active_cancelled(
        self,
        project_id: str,
    ) -> Optional[ActiveRunLock]:
        """Atomically mark the currently leased run as cancelled.

        Holding the active-run lock across the marker write prevents an old
        stop request from racing with release + reacquire and cancelling a new
        lease for the same project.
        """

        with self._active_run_lock:
            active = self._active_runs.get(project_id)
            if active is None:
                return None
            with self._cancelled_lock:
                self._cancelled_projects.add(project_id)
            now = datetime.now().isoformat()
            active.status = "cancelling"
            active.updated_at = now
            return self._copy_active_run(active)

    def clear_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.discard(project_id)

    @staticmethod
    def _copy_active_run(active: ActiveRunLock) -> ActiveRunLock:
        return ActiveRunLock(
            project_id=active.project_id,
            run_id=active.run_id,
            lease_id=active.lease_id,
            status=active.status,
            started_at=active.started_at,
            updated_at=active.updated_at,
        )

    def get_active_run(
        self,
        project_id: Optional[str] = None,
    ) -> Optional[ActiveRunLock]:
        """Return one project's run.

        The no-argument form is kept for compatibility with older callers. It
        returns the most recently updated run when several projects are active.
        New code should always pass ``project_id``.
        """
        with self._active_run_lock:
            if project_id is not None:
                active = self._active_runs.get(project_id)
            else:
                active = max(
                    self._active_runs.values(),
                    key=lambda item: item.updated_at,
                    default=None,
                )
            if active is None:
                return None
            return self._copy_active_run(active)

    def list_active_runs(self) -> list[ActiveRunLock]:
        with self._active_run_lock:
            return [
                self._copy_active_run(active)
                for active in self._active_runs.values()
            ]

    def set_active_run(
        self,
        project_id: str,
        *,
        run_id: Optional[str],
        status: str,
    ) -> ActiveRunLock:
        now = datetime.now().isoformat()
        with self._active_run_lock:
            existing = self._active_runs.get(project_id)
            started_at = existing.started_at if existing else now
            active = ActiveRunLock(
                project_id=project_id,
                run_id=run_id,
                lease_id=existing.lease_id if existing else uuid4().hex,
                status=status,
                started_at=started_at,
                updated_at=now,
            )
            self._active_runs[project_id] = active
            return self._copy_active_run(active)

    def release_active_run(
        self,
        project_id: str,
        *,
        run_id: Optional[str] = None,
        lease_id: Optional[str] = None,
    ) -> None:
        with self._active_run_lock:
            active = self._active_runs.get(project_id)
            if active is None:
                return
            if run_id is not None and active.run_id not in (None, run_id):
                return
            if lease_id is not None and active.lease_id != lease_id:
                return
            self._active_runs.pop(project_id, None)

    def try_acquire_slot(
        self, project_id: str, *, status: str = "starting"
    ) -> Optional[ActiveRunLock]:
        """Atomically reserve a slot for one project.

        Runs for different projects are independent. A second run for the same
        project is rejected so two workers cannot overwrite the same document.
        """
        with self._active_run_lock:
            if project_id in self._active_runs:
                return None
            # Clear only while creating a new lease. Once the placeholder is
            # visible, a stop request owns a real run and must not be erased by
            # worker startup.
            with self._cancelled_lock:
                self._cancelled_projects.discard(project_id)
            now = datetime.now().isoformat()
            active = ActiveRunLock(
                project_id=project_id,
                run_id=None,
                lease_id=uuid4().hex,
                status=status,
                started_at=now,
                updated_at=now,
            )
            self._active_runs[project_id] = active
            return self._copy_active_run(active)

    async def claim_translation_slot(
        self,
        project_id: str,
        cancel_callback=None,
        *,
        wait_timeout: float = 300.0,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        """Reserve a project slot without affecting runs for other projects.

        ``cancel_callback``, ``wait_timeout`` and ``poll_interval`` remain in
        the signature for API compatibility. Starting one project no longer
        cancels an unrelated active translation.
        """
        placeholder = self.try_acquire_slot(project_id, status="starting")
        if placeholder is not None:
            return {
                "status": "acquired",
                "project_id": project_id,
                "run_id": placeholder.run_id,
                "lease_id": placeholder.lease_id,
            }

        active = self.get_active_run(project_id)
        return {
            "status": "busy",
            "project_id": project_id,
            "active_project_id": project_id,
            "active_run_id": active.run_id if active else None,
            "active_status": active.status if active else "starting",
        }


translation_run_registry = TranslationRunRegistry()
