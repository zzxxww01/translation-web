"""Service for validating terminology usage in translations."""

from dataclasses import dataclass
from typing import List, Optional

from src.models.terminology import Term
from src.services.term_matcher import TermMatcher


@dataclass
class TermViolation:
    """Represents a terminology violation in translation."""

    term_original: str
    term_translation: str
    expected_translation: str
    actual_usage: str
    violation_type: str  # "missing", "incorrect", "inconsistent"
    context: str  # Surrounding text for context
    position: int  # Character position in text

    def __str__(self) -> str:
        """Format violation for display."""
        return (
            f"{self.violation_type.upper()}: '{self.term_original}' "
            f"should be '{self.expected_translation}' but found '{self.actual_usage}' "
            f"at position {self.position}"
        )


@dataclass
class ValidationReport:
    """Report of terminology validation results."""

    total_terms: int
    validated_terms: int
    violations: List[TermViolation]
    is_valid: bool

    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.violations)

    @property
    def accuracy(self) -> float:
        """Calculate terminology accuracy percentage."""
        if self.total_terms == 0:
            return 100.0
        return (self.validated_terms / self.total_terms) * 100.0

    def get_violations_by_type(self, violation_type: str) -> List[TermViolation]:
        """Get violations of a specific type."""
        return [v for v in self.violations if v.violation_type == violation_type]

    def __str__(self) -> str:
        """Format report for display."""
        lines = [
            f"Validation Report:",
            f"  Total Terms: {self.total_terms}",
            f"  Validated: {self.validated_terms}",
            f"  Violations: {self.violation_count}",
            f"  Accuracy: {self.accuracy:.1f}%",
            f"  Status: {'✓ PASS' if self.is_valid else '✗ FAIL'}"
        ]

        if self.violations:
            lines.append("\nViolations:")
            for v in self.violations:
                lines.append(f"  - {v}")

        return "\n".join(lines)


class TermValidationService:
    """Service for validating terminology usage in translations."""

    def __init__(self):
        """Initialize the validation service."""
        pass

    def validate_translation(
        self,
        source_text: str,
        translated_text: str,
        terms: List[Term],
        strict: bool = False
    ) -> ValidationReport:
        """
        Validate that translation correctly uses terminology.

        Args:
            source_text: Original source text
            translated_text: Translated text to validate
            terms: List of terms that should be used
            strict: If True, fail on any violation; if False, only report

        Returns:
            ValidationReport with validation results
        """
        violations = []
        validated_count = 0

        # Create matcher with terms
        matcher = TermMatcher(terms)

        for term in terms:
            # Check if term appears in source
            source_matches = matcher.match_term(term, source_text)

            if not source_matches:
                # Term not in source, skip validation
                continue

            # Term appears in source, validate translation
            violation = self._validate_term_usage(
                term,
                source_text,
                translated_text,
                source_matches
            )

            if violation:
                violations.append(violation)
            else:
                validated_count += 1

        total_terms = len([t for t in terms if matcher.match_term(t, source_text)])
        is_valid = len(violations) == 0 if strict else True

        return ValidationReport(
            total_terms=total_terms,
            validated_terms=validated_count,
            violations=violations,
            is_valid=is_valid
        )

    def _validate_term_usage(
        self,
        term: Term,
        source_text: str,
        translated_text: str,
        source_matches: List
    ) -> Optional[TermViolation]:
        """
        Validate a single term's usage in translation.

        Args:
            term: Term to validate
            source_text: Original source text
            translated_text: Translated text
            source_matches: Matches found in source text (List[MatchResult])

        Returns:
            TermViolation if validation fails, None if passes
        """
        expected = term.translation

        # For PRESERVE strategy, expect original term
        if term.strategy == "PRESERVE" or term.strategy == "PRESERVE_ANNOTATE":
            expected = term.original

        # Check if expected translation appears in translated text
        if expected.lower() not in translated_text.lower():
            # Find context around first source match
            first_match = source_matches[0]
            context = self._extract_context(source_text, first_match.start, first_match.end)

            return TermViolation(
                term_original=term.original,
                term_translation=term.translation,
                expected_translation=expected,
                actual_usage="<missing>",
                violation_type="missing",
                context=context,
                position=first_match.start
            )

        # Check for inconsistent usage (multiple different translations)
        # This is a simplified check - could be enhanced with fuzzy matching
        occurrences = self._count_term_occurrences(translated_text, expected)
        source_occurrences = len(source_matches)

        if occurrences < source_occurrences:
            first_match = source_matches[0]
            context = self._extract_context(source_text, first_match.start, first_match.end)

            return TermViolation(
                term_original=term.original,
                term_translation=term.translation,
                expected_translation=expected,
                actual_usage=f"<{occurrences}/{source_occurrences} occurrences>",
                violation_type="inconsistent",
                context=context,
                position=first_match.start
            )

        return None

    def _extract_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Extract context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)

        context = text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return context

    def _count_term_occurrences(self, text: str, term: str) -> int:
        """Count occurrences of a term in text (case-insensitive)."""
        text_lower = text.lower()
        term_lower = term.lower()
        count = 0
        pos = 0

        while True:
            pos = text_lower.find(term_lower, pos)
            if pos == -1:
                break
            count += 1
            pos += len(term_lower)

        return count

    def validate_batch(
        self,
        translations: List[tuple[str, str]],
        terms: List[Term],
        strict: bool = False
    ) -> List[ValidationReport]:
        """
        Validate multiple translations in batch.

        Args:
            translations: List of (source, translation) tuples
            terms: List of terms to validate
            strict: If True, fail on any violation

        Returns:
            List of ValidationReport for each translation
        """
        reports = []

        for source, translation in translations:
            report = self.validate_translation(source, translation, terms, strict)
            reports.append(report)

        return reports

    def get_summary(self, reports: List[ValidationReport]) -> dict:
        """
        Get summary statistics from multiple validation reports.

        Args:
            reports: List of validation reports

        Returns:
            Dictionary with summary statistics
        """
        total_terms = sum(r.total_terms for r in reports)
        total_validated = sum(r.validated_terms for r in reports)
        total_violations = sum(r.violation_count for r in reports)
        passed = sum(1 for r in reports if r.is_valid)

        return {
            "total_reports": len(reports),
            "passed": passed,
            "failed": len(reports) - passed,
            "total_terms": total_terms,
            "validated_terms": total_validated,
            "total_violations": total_violations,
            "average_accuracy": (total_validated / total_terms * 100.0) if total_terms > 0 else 100.0
        }
