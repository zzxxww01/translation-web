"""Core data models for the terminology system.

This module defines the foundational data structures for managing translation
terminology, including terms, metadata, and decision audit records.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def generate_term_id(scope: str, original: str, project_id: Optional[str] = None) -> str:
    """Generate a deterministic UUID v5 for a term.

    Uses DNS namespace and combines scope, project_id, and original text
    to create a consistent, reproducible ID.

    Args:
        scope: Either "global" or "project"
        original: The original term text
        project_id: Required when scope is "project", ignored for "global"

    Returns:
        A UUID v5 string

    Examples:
        >>> generate_term_id("global", "AI")
        'a1b2c3d4-...'
        >>> generate_term_id("project", "AI", "memory-mania")
        'e5f6g7h8-...'
    """
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
    if scope == "global":
        name = f"global:{original}"
    else:
        name = f"project:{project_id}:{original}"
    return str(uuid.uuid5(namespace, name))


class Term(BaseModel):
    """Core terminology entity containing translation-essential fields.

    This model represents a single term with its translation and associated
    metadata needed during the translation process.

    Attributes:
        id: Unique identifier (UUID v5, deterministically generated)
        original: Source language term
        translation: Target language translation
        strategy: Translation strategy (optional, defaults to empty string)
        note: Additional context or disambiguation notes (optional)
        status: Term activation status, either "active" or "inactive"
    """

    id: str
    original: str
    translation: str
    strategy: str = ""
    note: Optional[str] = None
    status: Literal["active", "inactive"] = "active"

    @field_validator("original")
    @classmethod
    def original_not_empty(cls, v: str) -> str:
        """Validate that original term is not empty."""
        if not v or not v.strip():
            raise ValueError("original cannot be empty")
        return v

    @field_validator("translation")
    @classmethod
    def translation_not_empty(cls, v: str) -> str:
        """Validate that translation is not empty."""
        if not v or not v.strip():
            raise ValueError("translation cannot be empty")
        return v

    @classmethod
    def create(
        cls,
        original: str,
        translation: str,
        scope: str,
        project_id: Optional[str] = None,
        strategy: str = "",
        note: Optional[str] = None,
        status: Literal["active", "inactive"] = "active",
    ) -> "Term":
        """Factory method to create a Term with auto-generated ID.

        Args:
            original: Source language term
            translation: Target language translation
            scope: Either "global" or "project"
            project_id: Required when scope is "project"
            strategy: Translation strategy (optional)
            note: Additional context (optional)
            status: Activation status (defaults to "active")

        Returns:
            A new Term instance with generated ID

        Examples:
            >>> term = Term.create("AI", "人工智能", "global")
            >>> term.id
            'a1b2c3d4-...'
        """
        term_id = generate_term_id(scope, original, project_id)
        return cls(
            id=term_id,
            original=original,
            translation=translation,
            strategy=strategy,
            note=note,
            status=status,
        )

    def is_active(self) -> bool:
        """Check if the term is currently active.

        Returns:
            True if status is "active", False otherwise
        """
        return self.status == "active"


class TermMetadata(BaseModel):
    """Metadata for term management and statistics.

    This model stores administrative information, usage statistics, and
    relationship data for terms. It's separated from Term to keep the core
    translation data lightweight.

    Attributes:
        term_id: Reference to the associated Term.id
        scope: Either "global" or "project"
        project_id: Required when scope is "project"
        term_original: Redundant copy of original text (for soft-delete queries)
        term_translation: Redundant copy of translation (for soft-delete queries)
        overrides_term_id: ID of global term that this project term overrides
        promoted_from_term_id: ID of project term this was promoted from
        tags: List of classification tags
        source: Origin of the term (e.g., "manual", "auto-extracted")
        usage_count: Number of times term has been used in translations
        is_deleted: Soft deletion flag
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    term_id: str
    scope: Literal["global", "project"]
    project_id: Optional[str] = None

    # Redundant fields for soft-delete queries
    term_original: str
    term_translation: str

    # Relationship fields
    overrides_term_id: Optional[str] = None
    promoted_from_term_id: Optional[str] = None

    # Management fields
    tags: List[str] = Field(default_factory=list)
    source: str = "manual"
    usage_count: int = 0

    # Audit fields
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode='after')
    def validate_project_id_for_project_scope(self) -> 'TermMetadata':
        """Validate that project_id is provided when scope is 'project'."""
        if self.scope == "project" and not self.project_id:
            raise ValueError("project_id is required when scope is 'project'")
        return self

    def mark_deleted(self) -> None:
        """Mark this term metadata as deleted.

        Updates is_deleted flag and updated_at timestamp.
        """
        self.is_deleted = True
        self.updated_at = datetime.now(timezone.utc)


class DecisionRecord(BaseModel):
    """Audit record for terminology decisions.

    Tracks all user decisions during term confirmation and management,
    providing a complete audit trail for terminology changes.

    Attributes:
        id: Unique record identifier (UUID v4)
        session_id: Translation session identifier
        project_id: Project identifier
        term_original: Original term text
        action: Type of decision made
        existing_translation: Previous translation (for conflicts)
        new_translation: Proposed new translation (for conflicts)
        chosen_translation: Final chosen translation (for conflicts)
        reason: User-provided reason for the decision
        context: Additional contextual information
        timestamp: When the decision was made
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    project_id: str
    term_original: str
    action: Literal["accept", "custom", "skip", "resolve_conflict"]

    # Conflict resolution details
    existing_translation: Optional[str] = None
    new_translation: Optional[str] = None
    chosen_translation: Optional[str] = None

    # Context
    reason: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
