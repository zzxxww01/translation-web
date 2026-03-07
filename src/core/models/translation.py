"""Translation record, paragraph, and section models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from .enums import ElementType, ParagraphStatus


class TranslationRecord(BaseModel):
    """单次翻译记录"""

    text: str
    model: str
    created_at: datetime = Field(default_factory=datetime.now)


class HistoryRecord(BaseModel):
    """修改历史记录"""

    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str


class InlineElement(BaseModel):
    """内联元素（链接、强调等）"""

    type: str
    text: str
    start: int
    end: int
    href: Optional[str] = None
    title: Optional[str] = None


class Paragraph(BaseModel):
    """段落"""

    id: str
    index: int
    source: str
    source_html: Optional[str] = None
    element_type: ElementType = ElementType.P

    inline_elements: Optional[List[InlineElement]] = None

    is_heading: bool = False
    heading_level: Optional[int] = None
    heading_chain: List[str] = Field(default_factory=list)

    is_metadata: bool = False
    metadata_type: Optional[str] = None

    translations: Dict[str, TranslationRecord] = Field(default_factory=dict)
    confirmed: Optional[str] = None
    status: ParagraphStatus = ParagraphStatus.PENDING

    history: List[HistoryRecord] = Field(default_factory=list)

    @staticmethod
    def _has_text(text: Optional[str]) -> bool:
        return isinstance(text, str) and bool(text.strip())

    def has_confirmed_translation(self) -> bool:
        """Return True when the confirmed translation contains usable text."""
        return self._has_text(self.confirmed)

    def add_translation(self, text: str, model: str) -> None:
        """添加翻译结果"""
        normalized = text.strip() if isinstance(text, str) else ""
        if not normalized:
            raise ValueError("Translation text cannot be empty")

        self.translations[model] = TranslationRecord(text=normalized, model=model)
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
            candidates = [
                item for item in candidates if self._has_text(item.text)
            ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.created_at)

    def latest_translation_text(self, non_empty: bool = False) -> Optional[str]:
        """Return the most recent translation text, if any."""
        latest = self.latest_translation(non_empty=non_empty)
        return latest.text if latest else None

    def has_draft_translation(self) -> bool:
        """Return True when there is at least one non-empty draft translation."""
        return self.latest_translation(non_empty=True) is not None

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

    def unconfirm(
        self,
        next_status: ParagraphStatus = ParagraphStatus.MODIFIED,
        source: str = "manual",
    ) -> None:
        """Drop the confirmed translation so the paragraph returns to review."""
        if self.confirmed:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
            self.confirmed = None
        if self.status == ParagraphStatus.APPROVED:
            self.status = next_status

    def confirm(self, text: str, source: str = "manual") -> None:
        """确认译文"""
        normalized = text.strip() if isinstance(text, str) else ""
        if not normalized:
            raise ValueError("Confirmed translation cannot be empty")

        if self.confirmed and self.confirmed != normalized:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
        self.confirmed = normalized
        self.status = ParagraphStatus.APPROVED


class Section(BaseModel):
    """章节"""

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
