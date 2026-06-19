"""Shared translation run registry."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Set


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
    status: str
    started_at: str
    updated_at: str


class TranslationRunRegistry:
    """Process-local registry for active longform translation runs."""

    def __init__(self) -> None:
        self._cancelled_projects: Set[str] = set()
        self._cancelled_lock = threading.Lock()
        self._active_run_lock = threading.Lock()
        self._active_run: Optional[ActiveRunLock] = None

    def is_cancelled(self, project_id: str) -> bool:
        with self._cancelled_lock:
            return project_id in self._cancelled_projects

    def mark_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.add(project_id)

    def clear_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.discard(project_id)

    def get_active_run(self) -> Optional[ActiveRunLock]:
        with self._active_run_lock:
            if self._active_run is None:
                return None
            return ActiveRunLock(
                project_id=self._active_run.project_id,
                run_id=self._active_run.run_id,
                status=self._active_run.status,
                started_at=self._active_run.started_at,
                updated_at=self._active_run.updated_at,
            )

    def set_active_run(
        self,
        project_id: str,
        *,
        run_id: Optional[str],
        status: str,
    ) -> ActiveRunLock:
        now = datetime.now().isoformat()
        with self._active_run_lock:
            if self._active_run and self._active_run.project_id == project_id:
                started_at = self._active_run.started_at
            else:
                started_at = now
            self._active_run = ActiveRunLock(
                project_id=project_id,
                run_id=run_id,
                status=status,
                started_at=started_at,
                updated_at=now,
            )
            return self._active_run

    def release_active_run(
        self,
        project_id: str,
        *,
        run_id: Optional[str] = None,
    ) -> None:
        with self._active_run_lock:
            active = self._active_run
            if active is None or active.project_id != project_id:
                return
            if run_id is not None and active.run_id not in (None, run_id):
                return
            self._active_run = None

    def try_acquire_slot(
        self, project_id: str, *, status: str = "starting"
    ) -> Optional[ActiveRunLock]:
        """原子 check-and-set:仅当当前没有任何活动 run 时占用槽并返回它,否则返回
        None。消除 get_active_run()+set_active_run() 之间的竞态窗口(审计 C4),
        避免两个不同 project 同时通过 'active is None' 判断而都获得唯一槽。"""
        with self._active_run_lock:
            if self._active_run is not None:
                return None
            now = datetime.now().isoformat()
            self._active_run = ActiveRunLock(
                project_id=project_id,
                run_id=None,
                status=status,
                started_at=now,
                updated_at=now,
            )
            return self._active_run

    async def claim_translation_slot(
        self,
        project_id: str,
        cancel_callback,
        *,
        wait_timeout: float = 300.0,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        # 原子 check-and-set,消除 get_active_run()/set_active_run() 之间的竞态窗口(审计 C4)。
        placeholder = self.try_acquire_slot(project_id, status="starting")
        if placeholder is not None:
            return {
                "status": "acquired",
                "project_id": project_id,
                "run_id": placeholder.run_id,
                "previous_project_id": None,
            }

        active = self.get_active_run()
        previous_project_id = active.project_id if active else None
        previous_run_id = active.run_id if active else None
        cancel_result = await cancel_callback(previous_project_id)

        deadline = time.monotonic() + wait_timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)
            placeholder = self.try_acquire_slot(project_id, status="starting")
            if placeholder is not None:
                return {
                    "status": "acquired_after_cancel",
                    "project_id": project_id,
                    "run_id": placeholder.run_id,
                    "previous_project_id": previous_project_id,
                    "previous_run_id": previous_run_id,
                    "cancel_result": cancel_result,
                }

        active = self.get_active_run()
        return {
            "status": "busy",
            "project_id": project_id,
            "active_project_id": active.project_id if active else previous_project_id,
            "active_run_id": active.run_id if active else previous_run_id,
            "active_status": active.status if active else "cancelling",
        }


translation_run_registry = TranslationRunRegistry()
