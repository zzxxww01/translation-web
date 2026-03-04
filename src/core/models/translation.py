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

    def add_translation(self, text: str, model: str) -> None:
        """添加翻译结果"""
        self.translations[model] = TranslationRecord(text=text, model=model)
        if self.status == ParagraphStatus.PENDING:
            self.status = ParagraphStatus.TRANSLATED

    def confirm(self, text: str, source: str = "manual") -> None:
        """确认译文"""
        if self.confirmed and self.confirmed != text:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
        self.confirmed = text
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
