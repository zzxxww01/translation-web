"""Consistency review models."""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class ConsistencyIssue(BaseModel):
    """一致性问题"""

    section_id: str
    paragraph_index: int
    issue_type: str
    description: str
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None


class ConsistencyReport(BaseModel):
    """一致性审查报告"""

    is_consistent: bool = True
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    auto_fixable: List[ConsistencyIssue] = Field(default_factory=list)
    manual_review: List[ConsistencyIssue] = Field(default_factory=list)

    term_stats: Dict[str, Dict] = Field(default_factory=dict)
    style_score: float = 100.0
    suggestions: List[Dict] = Field(default_factory=list)


class TermUsageStats(BaseModel):
    """术语使用统计"""

    term: str
    expected_translation: str
    actual_translations: List[str] = Field(default_factory=list)
    occurrences: int = 0
    consistent: bool = True


class StyleScore(BaseModel):
    """风格评分"""

    dimension: str
    score: float
    notes: str = ""


class ConsistencyReviewResult(BaseModel):
    """增强版一致性审查结果"""

    is_consistent: bool = True
    overall_score: float = 0.0

    terminology_stats: List[TermUsageStats] = Field(default_factory=list)
    style_scores: List[StyleScore] = Field(default_factory=list)
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    suggestions: List[Dict] = Field(default_factory=list)
    auto_fixable: List[ConsistencyIssue] = Field(default_factory=list)
    manual_review: List[ConsistencyIssue] = Field(default_factory=list)
