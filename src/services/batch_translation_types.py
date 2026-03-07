"""
Shared types for batch translation service.
"""

from datetime import datetime
from typing import Dict, List, Optional

from src.core.models import ProjectStatus


class TranslationProgress:
    """翻译进度"""

    def __init__(
        self,
        total_sections: int,
        total_paragraphs: int,
        original_status: ProjectStatus,
    ):
        self.total_sections = total_sections
        self.total_paragraphs = total_paragraphs
        self.original_status = original_status
        self.translated_sections = 0
        self.translated_paragraphs = 0
        self.current_section: Optional[str] = None
        self.current_step: Optional[str] = None
        self.errors: List[Dict] = []
        self.started_at = datetime.now()
        self.finished_at: Optional[datetime] = None
        self.final_status: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        """完成百分比"""
        if self.total_paragraphs == 0:
            return 0.0
        return (self.translated_paragraphs / self.total_paragraphs) * 100

    @property
    def is_complete(self) -> bool:
        """是否完成"""
        return self.translated_paragraphs >= self.total_paragraphs

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_sections": self.total_sections,
            "total_paragraphs": self.total_paragraphs,
            "translated_sections": self.translated_sections,
            "translated_paragraphs": self.translated_paragraphs,
            "progress_percent": round(self.progress_percent, 2),
            "current_section": self.current_section,
            "current_step": self.current_step,
            "original_status": self.original_status.value,
            "error_count": len(self.errors),
            "is_complete": self.is_complete,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "final_status": self.final_status,
        }
