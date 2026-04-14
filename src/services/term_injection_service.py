"""Term injection service for building translation prompts with terminology constraints.

This service constructs the terminology section of translation prompts, organizing
terms by their translation strategy and tracking first occurrences for annotation.
"""

from typing import Dict, List, Set

from src.models.terminology import Term


class TermInjectionService:
    """Service for injecting terminology constraints into translation prompts."""

    def __init__(self):
        """Initialize the term injection service."""
        self.first_occurrence_tracker: Dict[str, Set[str]] = {}

    def build_constraints_block(
        self,
        terms: List[Term],
        session_id: str,
        track_first_occurrence: bool = True
    ) -> str:
        """Build the terminology constraints block for a translation prompt.

        Args:
            terms: List of terms to inject
            session_id: Session identifier for tracking first occurrences
            track_first_occurrence: Whether to track and mark first occurrences

        Returns:
            Formatted constraints block as a string
        """
        if not terms:
            return ""

        # Initialize tracker for this session if needed
        if session_id not in self.first_occurrence_tracker:
            self.first_occurrence_tracker[session_id] = set()

        # Group terms by strategy
        grouped = self._group_by_strategy(terms)

        blocks = []

        # TRANSLATE strategy (default)
        if "TRANSLATE" in grouped or "" in grouped:
            translate_terms = grouped.get("TRANSLATE", []) + grouped.get("", [])
            if translate_terms:
                blocks.append(self._format_translate_block(translate_terms))

        # PRESERVE strategy
        if "PRESERVE" in grouped:
            blocks.append(self._format_preserve_block(grouped["PRESERVE"]))

        # FIRST_ANNOTATE strategy
        if "FIRST_ANNOTATE" in grouped:
            first_annotate_terms = grouped["FIRST_ANNOTATE"]
            blocks.append(self._format_first_annotate_block(
                first_annotate_terms,
                session_id,
                track_first_occurrence
            ))

        # PRESERVE_ANNOTATE strategy
        if "PRESERVE_ANNOTATE" in grouped:
            blocks.append(self._format_preserve_annotate_block(grouped["PRESERVE_ANNOTATE"]))

        if not blocks:
            return ""

        header = "## Terminology Constraints\n\n"
        return header + "\n\n".join(blocks)

    def mark_terms_used(self, session_id: str, term_originals: List[str]) -> None:
        """Mark terms as used (first occurrence has happened).

        Args:
            session_id: Session identifier
            term_originals: List of original term texts that were used
        """
        if session_id not in self.first_occurrence_tracker:
            self.first_occurrence_tracker[session_id] = set()

        self.first_occurrence_tracker[session_id].update(term_originals)

    def reset_session_tracker(self, session_id: str) -> None:
        """Reset the first occurrence tracker for a session.

        Args:
            session_id: Session identifier
        """
        if session_id in self.first_occurrence_tracker:
            del self.first_occurrence_tracker[session_id]

    def get_used_terms(self, session_id: str) -> Set[str]:
        """Get the set of terms that have been used in a session.

        Args:
            session_id: Session identifier

        Returns:
            Set of original term texts that have been used
        """
        return self.first_occurrence_tracker.get(session_id, set()).copy()

    def _group_by_strategy(self, terms: List[Term]) -> Dict[str, List[Term]]:
        """Group terms by their translation strategy."""
        grouped: Dict[str, List[Term]] = {}
        for term in terms:
            strategy = term.strategy or "TRANSLATE"
            if strategy not in grouped:
                grouped[strategy] = []
            grouped[strategy].append(term)
        return grouped

    def _format_translate_block(self, terms: List[Term]) -> str:
        """Format terms with TRANSLATE strategy."""
        lines = ["**Standard Translations:**"]
        for term in terms:
            line = f"- {term.original} → {term.translation}"
            if term.note:
                line += f" ({term.note})"
            lines.append(line)
        return "\n".join(lines)

    def _format_preserve_block(self, terms: List[Term]) -> str:
        """Format terms with PRESERVE strategy."""
        lines = ["**Preserve Original (Do Not Translate):**"]
        originals = [term.original for term in terms]
        lines.append(f"- {', '.join(originals)}")
        return "\n".join(lines)

    def _format_first_annotate_block(
        self,
        terms: List[Term],
        session_id: str,
        track: bool
    ) -> str:
        """Format terms with FIRST_ANNOTATE strategy."""
        lines = ["**Translate with First-Occurrence Annotation:**"]
        used_terms = self.first_occurrence_tracker.get(session_id, set())

        for term in terms:
            is_first = term.original not in used_terms if track else True
            marker = " [FIRST OCCURRENCE - ADD ANNOTATION]" if is_first else ""
            line = f"- {term.original} → {term.translation}{marker}"
            if term.note:
                line += f" ({term.note})"
            lines.append(line)

        return "\n".join(lines)

    def _format_preserve_annotate_block(self, terms: List[Term]) -> str:
        """Format terms with PRESERVE_ANNOTATE strategy."""
        lines = ["**Preserve with Annotation:**"]
        for term in terms:
            line = f"- {term.original} (add annotation: {term.translation})"
            if term.note:
                line += f" - {term.note}"
            lines.append(line)
        return "\n".join(lines)
