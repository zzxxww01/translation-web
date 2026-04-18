"""
Progress Tracker — manage translation progress caching with TTL and thread safety.

Extracted from BatchTranslationService to follow the Single Responsibility Principle.
"""

import threading
import time as _time
from datetime import datetime
from typing import Dict, Optional

from src.core.models import ProjectStatus
from src.services.batch_translation_types import TranslationProgress


class ProgressTracker:
    """Thread-safe, TTL-based translation progress cache."""

    _TTL_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        self._cache: Dict[str, TranslationProgress] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        project_id: str,
        total_sections: int,
        total_paragraphs: int,
        original_status: ProjectStatus,
    ) -> TranslationProgress:
        """Create and register a new progress entry."""
        progress = TranslationProgress(
            total_sections=total_sections,
            total_paragraphs=total_paragraphs,
            original_status=original_status,
        )
        progress._mono_ts = _time.monotonic()
        with self._lock:
            self._evict_stale()
            self._cache[project_id] = progress
        return progress

    def get(self, project_id: str) -> Optional[TranslationProgress]:
        """Return cached progress for *project_id*, or ``None``."""
        with self._lock:
            self._evict_stale()
            return self._cache.get(project_id)

    def remove(self, project_id: str) -> Optional[TranslationProgress]:
        """Pop and return progress for *project_id*, or ``None``."""
        with self._lock:
            return self._cache.pop(project_id, None)

    def touch(self, progress: TranslationProgress) -> None:
        """Refresh TTL and last-updated timestamp for an existing progress object."""
        progress.last_updated_at = datetime.now()
        progress._mono_ts = _time.monotonic()

    def record_error(
        self,
        progress: TranslationProgress,
        error: str,
        section_id: Optional[str] = None,
    ) -> None:
        """Append a standardized error payload to *progress*."""
        item: Dict = {
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        if section_id:
            item["section"] = section_id
        progress.errors.append(item)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evict_stale(self) -> None:
        """Remove entries older than TTL (call while holding _lock)."""
        now = _time.monotonic()
        stale = [
            pid
            for pid, p in self._cache.items()
            if hasattr(p, "_mono_ts") and now - p._mono_ts > self._TTL_SECONDS
        ]
        for pid in stale:
            del self._cache[pid]
