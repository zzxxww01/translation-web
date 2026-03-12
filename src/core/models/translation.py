"""Translation record, paragraph, and section models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import ElementType, ParagraphStatus


class TranslationRecord(BaseModel):
    """One saved translation candidate for a paragraph."""

    text: str
    model: str
    created_at: datetime = Field(default_factory=datetime.now)
    tokenized_text: Optional[str] = None
    format_issues: List[str] = Field(default_factory=list)


class HistoryRecord(BaseModel):
    """Manual edit / confirmation history entry."""

    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str


class InlineElement(BaseModel):
    """Structured inline formatting span from the canonical markdown block."""

    type: str
    text: str
    start: int
    end: int
    href: Optional[str] = None
    title: Optional[str] = None
    span_id: Optional[str] = None


class Paragraph(BaseModel):
    """Working translation segment.

    A paragraph is no longer the canonical markdown block itself. It is the unit
    shown in the UI and sent to the translator. When a markdown block is split
    into multiple working segments, all child paragraphs point back to the same
    parent block metadata.
    """

    id: str
    index: int
    source: str
    source_html: Optional[str] = None
    element_type: ElementType = ElementType.P

    inline_elements: Optional[List[InlineElement]] = None
    parent_block_id: Optional[str] = None
    parent_block_index: Optional[int] = None
    parent_block_type: Optional[ElementType] = None
    parent_block_markdown: Optional[str] = None
    parent_block_plain_text: Optional[str] = None
    parent_source_html: Optional[str] = None
    parent_inline_elements: Optional[List[InlineElement]] = None
    segment_start: int = 0
    segment_end: Optional[int] = None
    expected_tokens: List[str] = Field(default_factory=list)
    format_recovery_status: str = "not_applicable"
    format_errors: List[str] = Field(default_factory=list)

    is_heading: bool = False
    heading_level: Optional[int] = None
    heading_chain: List[str] = Field(default_factory=list)

    is_metadata: bool = False
    metadata_type: Optional[str] = None

    translations: Dict[str, TranslationRecord] = Field(default_factory=dict)
    confirmed: Optional[str] = None
    confirmed_tokenized: Optional[str] = None
    confirmed_format_issues: List[str] = Field(default_factory=list)
    status: ParagraphStatus = ParagraphStatus.PENDING
    ai_insight: Optional[Dict[str, Any]] = None

    history: List[HistoryRecord] = Field(default_factory=list)

    @staticmethod
    def _has_text(text: Optional[str]) -> bool:
        return isinstance(text, str) and bool(text.strip())

    def has_confirmed_translation(self) -> bool:
        """Return True when the confirmed translation contains usable text."""
        return self._has_text(self.confirmed)

    def add_translation(
        self,
        text: str,
        model: str,
        tokenized_text: Optional[str] = None,
        format_issues: Optional[List[str]] = None,
    ) -> None:
        """Persist one translation candidate."""
        normalized = text.strip() if isinstance(text, str) else ""
        if not normalized:
            raise ValueError("Translation text cannot be empty")

        issues = list(format_issues or [])
        if self.expected_tokens and not tokenized_text and not issues:
            issues.append("Missing tokenized translation for formatted paragraph.")

        self.translations[model] = TranslationRecord(
            text=normalized,
            model=model,
            tokenized_text=tokenized_text,
            format_issues=issues,
        )
        self._update_format_state(tokenized_text=tokenized_text, format_issues=issues)
        if self.status == ParagraphStatus.PENDING:
            self.status = ParagraphStatus.TRANSLATED

    def latest_translation(
        self, non_empty: bool = False
    ) -> Optional[TranslationRecord]:
        """Return the most recently saved translation record."""
        if not self.translations:
            return None
        candidates = list(self.translations.values())
        if non_empty:
            candidates = [item for item in candidates if self._has_text(item.text)]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.created_at)

    def latest_translation_text(self, non_empty: bool = False) -> Optional[str]:
        """Return the most recent translation text, if any."""
        latest = self.latest_translation(non_empty=non_empty)
        return latest.text if latest else None

    def latest_tokenized_translation_text(
        self, non_empty: bool = False
    ) -> Optional[str]:
        """Return the most recent tokenized translation text, if any."""
        latest = self.latest_translation(non_empty=non_empty)
        if latest and latest.tokenized_text:
            return latest.tokenized_text
        return None

    def has_draft_translation(self) -> bool:
        """Return True when there is at least one non-empty draft translation."""
        return self.latest_translation(non_empty=True) is not None

    def has_export_ready_translation(self) -> bool:
        """Return True when the active translation can be safely reconstructed."""
        if self.has_confirmed_translation():
            if self.expected_tokens:
                return bool(self.confirmed_tokenized) and not self.confirmed_format_issues
            return not self.confirmed_format_issues

        latest = self.latest_translation(non_empty=True)
        if latest is None:
            return False
        if self.expected_tokens:
            return bool(latest.tokenized_text) and not latest.format_issues
        return not latest.format_issues

    def has_usable_translation(self) -> bool:
        """Return True when paragraph has either confirmed or draft translation text."""
        return self.has_confirmed_translation() or self.has_draft_translation()

    def best_translation_text(self, fallback_to_source: bool = False) -> str:
        """Prefer confirmed text, otherwise fall back to the latest draft translation."""
        if self.has_confirmed_translation():
            return self.confirmed.strip()
        latest = self.latest_translation_text(non_empty=True)
        if latest:
            return latest
        return self.source if fallback_to_source else ""

    def best_tokenized_translation_text(
        self, fallback_to_source: bool = False
    ) -> Optional[str]:
        """Return the best tokenized translation for export reconstruction."""
        if self.has_confirmed_translation() and self.confirmed_tokenized:
            return self.confirmed_tokenized

        latest = self.latest_translation(non_empty=True)
        if latest and latest.tokenized_text:
            return latest.tokenized_text

        if fallback_to_source and not self.expected_tokens:
            return self.source
        return None

    def best_format_issues(self) -> List[str]:
        """Return the export-relevant format issues for the active translation."""
        if self.has_confirmed_translation():
            return list(self.confirmed_format_issues)
        latest = self.latest_translation(non_empty=True)
        if latest:
            return list(latest.format_issues)
        return list(self.format_errors)

    def has_formatting(self) -> bool:
        """Whether this segment belongs to a block that carries formatting spans."""
        return bool(self.expected_tokens or self.parent_inline_elements)

    def unconfirm(
        self,
        next_status: ParagraphStatus = ParagraphStatus.MODIFIED,
        source: str = "manual",
    ) -> None:
        """Drop the confirmed translation so the paragraph returns to review."""
        if self.confirmed:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
            self.confirmed = None
            self.confirmed_tokenized = None
            self.confirmed_format_issues = []
        if self.status == ParagraphStatus.APPROVED:
            self.status = next_status

    def confirm(
        self,
        text: str,
        source: str = "manual",
        tokenized_text: Optional[str] = None,
        format_issues: Optional[List[str]] = None,
    ) -> None:
        """Persist the confirmed translation."""
        normalized = text.strip() if isinstance(text, str) else ""
        if not normalized:
            raise ValueError("Confirmed translation cannot be empty")

        issues = list(format_issues or [])
        if self.expected_tokens and not tokenized_text and not issues:
            issues.append("Missing tokenized translation for confirmed formatted paragraph.")

        if self.confirmed and self.confirmed != normalized:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
        self.confirmed = normalized
        self.confirmed_tokenized = tokenized_text
        self.confirmed_format_issues = issues
        self._update_format_state(tokenized_text=tokenized_text, format_issues=issues)
        self.status = ParagraphStatus.APPROVED

    def _update_format_state(
        self,
        tokenized_text: Optional[str],
        format_issues: Optional[List[str]],
    ) -> None:
        issues = list(format_issues or [])
        self.format_errors = issues
        if not self.expected_tokens:
            self.format_recovery_status = "not_applicable"
            return
        if issues:
            self.format_recovery_status = "invalid"
            return
        if tokenized_text:
            self.format_recovery_status = "ready"
            return
        self.format_recovery_status = "pending"


class Section(BaseModel):
    """A document section containing working translation segments."""

    section_id: str
    title: str
    title_translation: Optional[str] = None
    title_source: Optional[str] = None
    paragraphs: List[Paragraph] = Field(default_factory=list)

    @property
    def total_paragraphs(self) -> int:
        return len(self.paragraphs)

    @property
    def approved_count(self) -> int:
        return sum(1 for p in self.paragraphs if p.status == ParagraphStatus.APPROVED)

    @property
    def is_complete(self) -> bool:
        return all(p.status == ParagraphStatus.APPROVED for p in self.paragraphs)
