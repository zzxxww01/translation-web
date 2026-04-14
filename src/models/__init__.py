"""Data models for the translation agent."""

from .terminology import Term, TermMetadata, DecisionRecord, generate_term_id

__all__ = ["Term", "TermMetadata", "DecisionRecord", "generate_term_id"]
