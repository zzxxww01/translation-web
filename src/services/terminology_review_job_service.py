"""Persistent status storage for terminology review preparation jobs."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from src.core.file_utils import read_json, write_json_atomic


_WORKER_EPOCH = uuid4().hex


class ActiveTerminologyReviewModelConflict(RuntimeError):
    """Raised when an active project job uses a different requested model."""

    def __init__(
        self,
        *,
        project_id: str,
        requested_model: Optional[str],
        active_job: Dict[str, Any],
    ) -> None:
        self.project_id = project_id
        self.requested_model = requested_model
        self.active_job = dict(active_job)
        active_model = active_job.get("model")
        super().__init__(
            "Terminology review is already running with a different model "
            f"(active={active_model or 'default'}, "
            f"requested={requested_model or 'default'})."
        )


class TerminologyReviewJobStore:
    """Store job state beside project artifacts so every API worker can poll it."""

    STALE_AFTER = timedelta(hours=2)
    _locks: Dict[str, threading.RLock] = {}
    _locks_guard = threading.Lock()

    def __init__(
        self,
        projects_path: Path | str,
        *,
        worker_epoch: Optional[str] = None,
    ) -> None:
        self.projects_path = Path(projects_path)
        self.worker_epoch = worker_epoch or _WORKER_EPOCH

    @classmethod
    def _get_lock(cls, project_id: str) -> threading.RLock:
        with cls._locks_guard:
            return cls._locks.setdefault(project_id, threading.RLock())

    def create(self, project_id: str, model: Optional[str] = None) -> Dict[str, Any]:
        job, _created = self.create_or_get_active(project_id, model)
        return job

    def create_or_get_active(
        self,
        project_id: str,
        model: Optional[str] = None,
    ) -> tuple[Dict[str, Any], bool]:
        normalized_model = self._normalize_model(model)
        with self._get_lock(project_id):
            active = self._find_active(project_id)
            if active is not None:
                active_model = self._normalize_model(active.get("model"))
                if active_model != normalized_model:
                    raise ActiveTerminologyReviewModelConflict(
                        project_id=project_id,
                        requested_model=normalized_model,
                        active_job=active,
                    )
                return active, False

            now = self._now()
            job = {
                "job_id": uuid4().hex,
                "project_id": project_id,
                "model": normalized_model,
                "worker_epoch": self.worker_epoch,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }
            self._write(job)
        return job, True

    def get(self, project_id: str, job_id: str) -> Dict[str, Any]:
        path = self._job_path(project_id, job_id)
        with self._get_lock(project_id):
            job = read_json(path)
            return self._normalize_active_job(job)

    def mark_running(self, project_id: str, job_id: str) -> Dict[str, Any]:
        return self._update(
            project_id,
            job_id,
            status="running",
            started_at=self._now(),
            error=None,
        )

    def mark_succeeded(
        self,
        project_id: str,
        job_id: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._update(
            project_id,
            job_id,
            status="succeeded",
            completed_at=self._now(),
            result=result,
            error=None,
        )

    def mark_failed(
        self,
        project_id: str,
        job_id: str,
        error: str,
    ) -> Dict[str, Any]:
        return self._update(
            project_id,
            job_id,
            status="failed",
            completed_at=self._now(),
            error=error,
        )

    def _update(self, project_id: str, job_id: str, **updates: Any) -> Dict[str, Any]:
        with self._get_lock(project_id):
            job = read_json(self._job_path(project_id, job_id))
            if job["status"] in {"succeeded", "failed"}:
                return job
            job.update(updates)
            job["updated_at"] = self._now()
            self._write(job)
            return job

    def _expire_stale_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        if job.get("status") not in {"queued", "running"}:
            return job

        timestamp = job.get("started_at") or job.get("created_at")
        try:
            age = datetime.now() - datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            age = self.STALE_AFTER + timedelta(seconds=1)

        if age <= self.STALE_AFTER:
            return job

        job.update(
            {
                "status": "failed",
                "updated_at": self._now(),
                "completed_at": self._now(),
                "error": "Terminology review job stopped before completion.",
            }
        )
        self._write(job)
        return job

    def _normalize_active_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job = self._expire_stale_job(job)
        if (
            job.get("status") in {"queued", "running"}
            and job.get("worker_epoch") != self.worker_epoch
        ):
            now = self._now()
            job.update(
                {
                    "status": "failed",
                    "updated_at": now,
                    "completed_at": now,
                    "error": "Terminology review worker restarted before completion.",
                }
            )
            self._write(job)
        return job

    def _job_path(self, project_id: str, job_id: str) -> Path:
        return self._jobs_dir(project_id) / f"{job_id}.json"

    def _jobs_dir(self, project_id: str) -> Path:
        return (
            self.projects_path
            / project_id
            / "artifacts"
            / "term-review"
            / "jobs"
        )

    def _find_active(
        self,
        project_id: str,
    ) -> Optional[Dict[str, Any]]:
        jobs_dir = self._jobs_dir(project_id)
        if not jobs_dir.exists():
            return None

        candidates: list[Dict[str, Any]] = []
        for path in jobs_dir.glob("*.json"):
            try:
                job = self._normalize_active_job(read_json(path))
            except (OSError, ValueError, TypeError):
                continue
            if job.get("status") in {"queued", "running"}:
                candidates.append(job)

        return max(
            candidates,
            key=lambda item: str(item.get("created_at") or ""),
            default=None,
        )

    def _write(self, job: Dict[str, Any]) -> None:
        write_json_atomic(
            self._job_path(job["project_id"], job["job_id"]),
            job,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _normalize_model(model: Optional[str]) -> Optional[str]:
        if model is None:
            return None
        return model.strip() or None
