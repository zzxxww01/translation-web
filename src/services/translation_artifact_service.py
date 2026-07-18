"""Helpers for translation run artifact persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.models import ArticleAnalysis
from src.core.file_utils import write_json_atomic
from src.services.translation_run_registry import RunStateSnapshot


logger = logging.getLogger(__name__)
_MISSING = object()


class TranslationArtifactService:
    """Persist and inspect longform translation run artifacts."""

    def __init__(self, projects_path: Path):
        self.projects_path = Path(projects_path)

    def artifacts_root(self, project_id: str) -> Path:
        return self.projects_path / project_id / "artifacts" / "runs"

    def create_run_artifact_dir(self, project_id: str) -> tuple[str, Path]:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        run_dir = self.artifacts_root(project_id) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_id, run_dir

    def normalize_payload(self, payload: Any) -> Any:
        if hasattr(payload, "model_dump"):
            return payload.model_dump(mode="json")
        if hasattr(payload, "dict"):
            return payload.dict()
        if isinstance(payload, dict):
            return {
                key: self.normalize_payload(value)
                for key, value in payload.items()
            }
        if isinstance(payload, list):
            return [self.normalize_payload(item) for item in payload]
        return payload

    def write_json(self, path: Path, payload: Any) -> None:
        write_json_atomic(path, self.normalize_payload(payload))

    def write_run_state(
        self,
        project_id: str,
        run_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Persist the latest task state so polling survives client disconnects."""
        state = dict(payload)
        state["project_id"] = project_id
        state["run_id"] = run_id
        state["updated_at"] = datetime.now().isoformat()
        self.write_json(
            self.artifacts_root(project_id) / run_id / "run-state.json",
            state,
        )

    def load_latest_analysis_snapshot(self, project_id: str) -> Optional[ArticleAnalysis]:
        artifacts_root = self.artifacts_root(project_id)
        if not artifacts_root.exists():
            return None

        run_dirs = sorted(
            (path for path in artifacts_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for run_dir in run_dirs:
            analysis_path = run_dir / "analysis.json"
            if not analysis_path.exists():
                continue
            try:
                with open(analysis_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if hasattr(ArticleAnalysis, "model_validate"):
                    return ArticleAnalysis.model_validate(payload)
                return ArticleAnalysis.parse_obj(payload)
            except Exception as exc:
                logger.warning(
                    "Failed to load analysis snapshot from %s: %s",
                    analysis_path,
                    exc,
                )
        return None

    def load_latest_run_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        artifacts_root = self.artifacts_root(project_id)
        if not artifacts_root.exists():
            return None

        run_dirs = sorted(
            (path for path in artifacts_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for run_dir in run_dirs:
            summary_path = run_dir / "run-summary.json"
            if not summary_path.exists():
                continue
            try:
                with open(summary_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    return payload
            except Exception as exc:
                logger.warning(
                    "Failed to load run summary from %s: %s",
                    summary_path,
                    exc,
                )
        return None

    def get_latest_run_dir(self, project_id: str) -> Optional[Path]:
        run_dirs = self._get_run_dirs(project_id)
        return run_dirs[0] if run_dirs else None

    def load_latest_run_snapshot(
        self,
        project_id: str,
    ) -> tuple[Optional[Dict[str, Any]], Optional[RunStateSnapshot]]:
        """Load polling state and the newest summary with one directory scan."""
        run_dirs = self._get_run_dirs(project_id)
        if not run_dirs:
            return None, None

        latest_run_dir = run_dirs[0]
        latest_summary = self._read_run_summary(latest_run_dir)
        summary = latest_summary
        if summary is None:
            for run_dir in run_dirs[1:]:
                summary = self._read_run_summary(run_dir)
                if summary is not None:
                    break

        state = self._infer_run_state_from_dir(
            latest_run_dir,
            summary_payload=latest_summary,
        )
        return summary, state

    def infer_run_state(self, project_id: str) -> Optional[RunStateSnapshot]:
        return self.load_latest_run_snapshot(project_id)[1]

    def _get_run_dirs(self, project_id: str) -> list[Path]:
        artifacts_root = self.artifacts_root(project_id)
        if not artifacts_root.exists():
            return []
        return sorted(
            (path for path in artifacts_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def _read_run_summary(self, run_dir: Path) -> Optional[Dict[str, Any]]:
        summary_path = run_dir / "run-summary.json"
        if not summary_path.exists():
            return None
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except Exception as exc:
            logger.warning("Failed to parse run summary from %s: %s", summary_path, exc)
            return None

    def _infer_run_state_from_dir(
        self,
        run_dir: Path,
        *,
        summary_payload: Any = _MISSING,
    ) -> RunStateSnapshot:
        if summary_payload is _MISSING:
            summary_payload = self._read_run_summary(run_dir)

        if isinstance(summary_payload, dict):
            return RunStateSnapshot(
                run_id=str(summary_payload.get("run_id") or run_dir.name),
                status=str(summary_payload.get("status") or "processing"),
                current_step=str(summary_payload.get("status") or "processing"),
                current_section=None,
                updated_at=datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(),
                started_at=summary_payload.get("started_at"),
                finished_at=summary_payload.get("finished_at"),
                error_count=int(
                    summary_payload.get("error_count")
                    or len(summary_payload.get("errors") or [])
                ),
            )

        state_path = run_dir / "run-state.json"
        if state_path.exists():
            try:
                payload = json.loads(state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return RunStateSnapshot(
                        run_id=str(payload.get("run_id") or run_dir.name),
                        status=str(
                            payload.get("final_status")
                            or payload.get("status")
                            or "processing"
                        ),
                        current_step=str(payload.get("current_step") or "processing"),
                        current_section=payload.get("current_section"),
                        updated_at=payload.get("updated_at"),
                        started_at=payload.get("started_at"),
                        finished_at=payload.get("finished_at"),
                        error_count=int(payload.get("error_count") or 0),
                    )
            except Exception as exc:
                logger.warning("Failed to parse run state from %s: %s", state_path, exc)

        latest_file: Optional[Path] = None
        latest_section: Optional[str] = None
        latest_step = "processing"
        step_map = {
            "analysis.json": "深度分析全文",
            "source-metadata.json": "翻译来源说明",
            "consistency.json": "一致性审查",
            "section-context": "准备章节上下文",
            "section-prescan": "章节术语预扫描",
            "section-draft": "章节初译",
            "section-critique": "章节反思",
            "section-revision": "章节润色",
        }

        for candidate in run_dir.rglob("*.json"):
            if latest_file is None or candidate.stat().st_mtime > latest_file.stat().st_mtime:
                latest_file = candidate

        if latest_file is not None:
            parent_name = latest_file.parent.name
            latest_step = step_map.get(latest_file.name, step_map.get(parent_name, "processing"))
            if parent_name.startswith("section-"):
                latest_section = latest_file.stem

        updated_at = datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat()
        return RunStateSnapshot(
            run_id=run_dir.name,
            status="processing",
            current_step=latest_step,
            current_section=latest_section,
            updated_at=updated_at,
            started_at=datetime.fromtimestamp(run_dir.stat().st_ctime).isoformat(),
            finished_at=None,
            error_count=0,
        )
