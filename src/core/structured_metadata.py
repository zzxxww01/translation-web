"""Shared helpers for structured metadata paragraphs."""

from __future__ import annotations

from typing import Final


STRUCTURED_METADATA_TYPES: Final[set[str]] = {
    "source",
    "subtitle",
    "byline",
    "date_access",
}


def is_structured_metadata_paragraph(paragraph) -> bool:
    """Return True when a paragraph is handled by metadata-specific translation."""
    return bool(
        getattr(paragraph, "is_metadata", False)
        and getattr(paragraph, "metadata_type", None) in STRUCTURED_METADATA_TYPES
    )
