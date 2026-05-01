"""Translation completeness and quality validator."""

from __future__ import annotations

import re
from typing import List, Optional
from dataclasses import dataclass

from .models import Paragraph, Section


@dataclass
class ValidationIssue:
    """Translation validation issue."""

    severity: str  # "error", "warning", "info"
    type: str  # "untranslated", "latex_broken", "variable_error", etc.
    paragraph_id: str
    section_id: str
    message: str
    source_text: Optional[str] = None
    translation_text: Optional[str] = None


class TranslationValidator:
    """Validate translation completeness and quality."""

    # Pattern to detect untranslated English text
    _ENGLISH_SENTENCE_PATTERN = re.compile(
        r'\b[A-Z][a-z]+\s+[a-z]+\s+[a-z]+\b'  # At least 3 English words
    )

    # Pattern to detect LaTeX formulas
    _LATEX_DISPLAY_PATTERN = re.compile(r'(\\\[.*?\\\]|\$\$.*?\$\$)', re.DOTALL)
    _LATEX_INLINE_PATTERN = re.compile(r'(\\\(.*?\\\)|\$[^\$\n]+\$)')

    # Pattern to detect broken LaTeX (missing backslashes)
    _BROKEN_LATEX_PATTERN = re.compile(
        r'(text\{|frac\{|big\(|times\s|sum_|int_)'
    )

    # Pattern to detect variable placeholders that weren't replaced
    _VARIABLE_PLACEHOLDER_PATTERN = re.compile(
        r'(\{\{[A-Z_]+\}\}|\[\$\/[A-Z\-]+\]:|Storage\s*\[\$\/[A-Z\-]+\]:)'
    )

    def validate_section(self, section: Section) -> List[ValidationIssue]:
        """Validate all paragraphs in a section."""
        issues: List[ValidationIssue] = []

        for paragraph in section.paragraphs:
            issues.extend(self.validate_paragraph(paragraph, section.section_id))

        return issues

    def validate_paragraph(
        self,
        paragraph: Paragraph,
        section_id: str = ""
    ) -> List[ValidationIssue]:
        """Validate a single paragraph."""
        issues: List[ValidationIssue] = []

        # Check if paragraph has translation
        if not paragraph.has_usable_translation():
            if paragraph.status.value not in ["pending", "translating"]:
                issues.append(ValidationIssue(
                    severity="error",
                    type="untranslated",
                    paragraph_id=paragraph.id,
                    section_id=section_id,
                    message="Paragraph has no translation",
                    source_text=paragraph.source[:100] if paragraph.source else None,
                ))
            return issues

        translation = paragraph.best_translation_text()
        if not translation:
            return issues

        # Check for untranslated English text
        if self._has_untranslated_english(translation, paragraph.source):
            issues.append(ValidationIssue(
                severity="warning",
                type="untranslated",
                paragraph_id=paragraph.id,
                section_id=section_id,
                message="Translation contains untranslated English text",
                source_text=paragraph.source[:100] if paragraph.source else None,
                translation_text=translation[:100],
            ))

        # Check for broken LaTeX formulas
        if self._has_broken_latex(translation):
            issues.append(ValidationIssue(
                severity="error",
                type="latex_broken",
                paragraph_id=paragraph.id,
                section_id=section_id,
                message="Translation contains broken LaTeX formulas (missing backslashes)",
                translation_text=translation[:200],
            ))

        # Check for unreplaced variable placeholders
        if self._has_variable_placeholders(translation):
            issues.append(ValidationIssue(
                severity="error",
                type="variable_error",
                paragraph_id=paragraph.id,
                section_id=section_id,
                message="Translation contains unreplaced variable placeholders",
                translation_text=translation[:200],
            ))

        # Validate LaTeX formulas match between source and translation
        source_latex = self._extract_latex_formulas(paragraph.source or "")
        trans_latex = self._extract_latex_formulas(translation)

        if source_latex != trans_latex:
            issues.append(ValidationIssue(
                severity="warning",
                type="latex_mismatch",
                paragraph_id=paragraph.id,
                section_id=section_id,
                message=f"LaTeX formulas don't match: source has {len(source_latex)}, translation has {len(trans_latex)}",
                source_text=str(source_latex)[:100],
                translation_text=str(trans_latex)[:100],
            ))

        return issues

    def _has_untranslated_english(self, translation: str, source: str) -> bool:
        """Check if translation contains significant untranslated English text."""
        # Skip if source is empty
        if not source:
            return False

        # Extract English sentences from translation
        matches = self._ENGLISH_SENTENCE_PATTERN.findall(translation)

        # If we find English text that's also in the source, it might be untranslated
        if matches:
            # Check if it's a significant portion (more than 50 characters of English)
            english_text = " ".join(matches)
            if len(english_text) > 50 and english_text in source:
                return True

        return False

    def _has_broken_latex(self, text: str) -> bool:
        """Check if text contains broken LaTeX (missing backslashes)."""
        # Look for LaTeX commands without backslashes
        return bool(self._BROKEN_LATEX_PATTERN.search(text))

    def _has_variable_placeholders(self, text: str) -> bool:
        """Check if text contains unreplaced variable placeholders."""
        return bool(self._VARIABLE_PLACEHOLDER_PATTERN.search(text))

    def _extract_latex_formulas(self, text: str) -> List[str]:
        """Extract all LaTeX formulas from text."""
        formulas: List[str] = []

        # Extract display math
        formulas.extend(self._LATEX_DISPLAY_PATTERN.findall(text))

        # Extract inline math
        formulas.extend(self._LATEX_INLINE_PATTERN.findall(text))

        return formulas


def validate_sections(sections: List[Section]) -> List[ValidationIssue]:
    """Validate all sections and return issues."""
    validator = TranslationValidator()
    issues: List[ValidationIssue] = []

    for section in sections:
        issues.extend(validator.validate_section(section))

    return issues


def format_validation_report(issues: List[ValidationIssue]) -> str:
    """Format validation issues into a readable report."""
    if not issues:
        return "✅ No validation issues found."

    lines = [f"Found {len(issues)} validation issue(s):\n"]

    # Group by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors:
        lines.append(f"🔴 Errors ({len(errors)}):")
        for issue in errors:
            lines.append(f"  - [{issue.section_id}/{issue.paragraph_id}] {issue.type}: {issue.message}")
            if issue.translation_text:
                lines.append(f"    Translation: {issue.translation_text}")
        lines.append("")

    if warnings:
        lines.append(f"⚠️  Warnings ({len(warnings)}):")
        for issue in warnings:
            lines.append(f"  - [{issue.section_id}/{issue.paragraph_id}] {issue.type}: {issue.message}")
        lines.append("")

    return "\n".join(lines)
