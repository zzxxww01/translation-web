"""Terminology-review artifact schema markers."""

from __future__ import annotations

from typing import Any, Dict


TERM_REVIEW_SCHEMA = "translation-agent.term-review"
TERM_REVIEW_SCHEMA_VERSION = 2
SUBMISSION_PENDING = "pending"
SUBMISSION_SUBMITTED = "submitted"


def is_current_term_review_artifact(payload: Dict[str, Any]) -> bool:
    return (
        payload.get("schema") == TERM_REVIEW_SCHEMA
        and payload.get("schema_version") == TERM_REVIEW_SCHEMA_VERSION
    )


def is_legacy_term_review_artifact(payload: Dict[str, Any]) -> bool:
    """Recognize the schema-less candidate payload emitted before version 2."""
    return (
        "schema" not in payload
        and "schema_version" not in payload
        and "submission_status" not in payload
        and isinstance(payload.get("project_id"), str)
        and isinstance(payload.get("sections"), list)
    )
