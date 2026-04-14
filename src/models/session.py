"""Translation session models for managing translation workflows with terminology."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Translation session status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class TermChange(BaseModel):
    """Record of a terminology change detected during session resume."""
    term_id: str
    change_type: str  # "added", "modified", "deleted"
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None


class TranslationSession(BaseModel):
    """Translation session with terminology snapshot support.

    Manages the lifecycle of a translation task, including terminology
    snapshots for consistency and change detection for resume scenarios.

    Attributes:
        id: Unique session identifier
        project_id: Associated project
        section_id: Section being translated (optional)
        status: Current session status
        snapshot_version: Terminology snapshot version (timestamp)
        term_ids: List of term IDs in the snapshot
        progress: Translation progress metadata
        created_at: Session creation time
        updated_at: Last update time
        completed_at: Completion time (if completed)
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    section_id: Optional[str] = None
    status: SessionStatus = SessionStatus.PENDING

    # Terminology snapshot
    snapshot_version: Optional[str] = None  # ISO timestamp
    term_ids: List[str] = Field(default_factory=list)

    # Progress tracking
    progress: Dict = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def update_status(self, status: SessionStatus) -> None:
        """Update session status and timestamp."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if status == SessionStatus.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)

    def create_snapshot(self, term_ids: List[str]) -> None:
        """Create a terminology snapshot for this session."""
        self.snapshot_version = datetime.now(timezone.utc).isoformat()
        self.term_ids = term_ids
        self.updated_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Check if session is in an active state."""
        return self.status in [SessionStatus.PENDING, SessionStatus.IN_PROGRESS, SessionStatus.PAUSED]
