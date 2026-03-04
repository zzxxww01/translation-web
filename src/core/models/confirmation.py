"""Paragraph confirmation workflow models."""

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class TranslationVersion(BaseModel):
    """翻译版本（导入的参考译文）"""

    id: str
    name: str
    source_type: str
    paragraphs: Dict[str, Optional[str]] = Field(default_factory=dict)
    metadata: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ParagraphConfirmation(BaseModel):
    """段落确认状态"""

    paragraph_id: str
    selected_version_id: Optional[str] = None
    custom_translation: Optional[str] = None
    confirmed_at: Optional[datetime] = None


class AIInsight(BaseModel):
    """AI透明度数据（四步法翻译结果）"""

    overall_score: float
    is_excellent: bool
    applied_terms: List[str]
    style: str
    steps: Dict[str, bool]

    understanding: Optional[str] = None
    scores: Optional[Dict[str, float]] = None
    issues: Optional[List[Dict]] = None


class RetranslateOption(BaseModel):
    """重新翻译选项"""

    id: str
    label: str
    description: str
    instruction: str
