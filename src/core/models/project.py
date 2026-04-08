"""Project-level models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from .enums import ProjectStatus
from .translation import Section


class ProjectProgress(BaseModel):
    """项目进度"""

    total_sections: int = 0
    total_paragraphs: int = 0
    approved: int = 0
    reviewing: int = 0
    pending: int = 0

    @property
    def progress_percent(self) -> float:
        if self.total_paragraphs == 0:
            return 0.0
        return (self.approved / self.total_paragraphs) * 100


class ProjectConfig(BaseModel):
    """项目配置"""

    ai_model: str = "pro"
    model_type: str = "pro"
    translation_style: str = "natural_professional"
    segment_level: str = "h2"
    max_paragraph_length: int = 800
    merge_short_paragraphs: bool = True


class ArticleMetadata(BaseModel):
    """文章元信息（作者、日期等）"""

    authors: List[str] = Field(default_factory=list)
    byline_markdown: Optional[str] = None
    access_text: Optional[str] = None
    published_date: Optional[str] = None
    subtitle: Optional[str] = None
    publication: Optional[str] = None
    original_url: Optional[str] = None
    cover_image: Optional[str] = None
    raw_metadata_html: Optional[str] = None


class ProjectMeta(BaseModel):
    """项目元信息（meta.json）"""

    id: str
    title: str
    title_translation: Optional[str] = None
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.CREATED
    progress: ProjectProgress = Field(default_factory=ProjectProgress)
    config: ProjectConfig = Field(default_factory=ProjectConfig)

    metadata: Optional[ArticleMetadata] = None

    sections: List[Section] = Field(default_factory=list)
    versions: List["TranslationVersion"] = Field(default_factory=list)
    confirmation_map: Dict[str, "ParagraphConfirmation"] = Field(default_factory=dict)
    workflow_mode: str = "paragraph_confirmation"

    def update_progress(self, sections: List[Section]) -> None:
        """更新进度统计"""
        self.progress.total_sections = len(sections)
        self.progress.total_paragraphs = sum(s.total_paragraphs for s in sections)
        self.progress.approved = sum(s.approved_count for s in sections)
        self.progress.pending = self.progress.total_paragraphs - self.progress.approved
        self.updated_at = datetime.now()


# Deferred imports for forward references
from .confirmation import TranslationVersion, ParagraphConfirmation  # noqa: E402, F401

ProjectMeta.model_rebuild()
