"""Analysis and four-step translation models."""

from __future__ import annotations

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field

from .enums import TranslationStrategy
from .glossary import GlossaryTerm


class StyleGuide(BaseModel):
    """翻译风格指南"""

    tone: str = "professional"
    person: str = "third"
    formality: str = "formal"
    notes: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """全文分析结果（基础版，保留兼容性）"""

    title: str
    summary: Optional[str] = None
    detected_terms: List[GlossaryTerm] = Field(default_factory=list)
    style_guide: StyleGuide = Field(default_factory=StyleGuide)
    section_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0


class EnhancedTerm(BaseModel):
    """增强版术语条目"""

    term: str
    context_meaning: str = ""
    translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    first_occurrence_note: bool = False
    rationale: Optional[str] = None


class ArticleStyle(BaseModel):
    """文章风格分析"""

    tone: str = "professional"
    target_audience: str = ""
    translation_voice: str = ""


class TranslationChallenge(BaseModel):
    """翻译难点"""

    location: str
    issue: str
    suggestion: Optional[str] = None


class SectionUnderstanding(BaseModel):
    """章节理解结果（四步法 Step 1 输出）"""

    role_in_article: str = ""
    relation_to_previous: str = ""
    relation_to_next: str = ""
    key_points: List[str] = Field(default_factory=list)
    translation_notes: List[str] = Field(default_factory=list)


class ArticleAnalysis(BaseModel):
    """全文深度分析结果（Phase 0 输出）"""

    theme: str = ""
    key_arguments: List[str] = Field(default_factory=list)
    structure_summary: str = ""

    terminology: List[EnhancedTerm] = Field(default_factory=list)
    style: ArticleStyle = Field(default_factory=ArticleStyle)
    challenges: List[TranslationChallenge] = Field(default_factory=list)
    guidelines: List[str] = Field(default_factory=list)

    section_roles: Dict[str, SectionUnderstanding] = Field(default_factory=dict)

    section_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0


class TranslationIssue(BaseModel):
    """翻译问题"""

    paragraph_index: int
    issue_type: str
    severity: str = "medium"
    original_text: str = ""
    description: str
    why_it_matters: str = ""
    suggestion: str = ""


class ReflectionResult(BaseModel):
    """反思结果（四步法 Step 3 输出）"""

    overall_score: float = 0.0
    readability_score: float = 0.0
    accuracy_score: float = 0.0
    is_excellent: bool = False
    issues: List[TranslationIssue] = Field(default_factory=list)


class QualityAssessment(BaseModel):
    """质量评估结果"""

    passed: bool = False
    overall_score: float = 0.0
    scores: Dict[str, float] = Field(default_factory=dict)
    failed_criteria: List[str] = Field(default_factory=list)
    action: str = "pass"


class SectionTranslationResult(BaseModel):
    """章节翻译结果"""

    section_id: str
    translations: List[str] = Field(default_factory=list)
    draft_translations: List[str] = Field(default_factory=list)
    revised_translations: List[str] = Field(default_factory=list)
    translation_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    understanding: Optional[SectionUnderstanding] = None
    reflection: Optional[ReflectionResult] = None
    assessment: Optional[QualityAssessment] = None


class TermUsageTracker(BaseModel):
    """术语使用追踪"""

    used_translations: Dict[str, List[str]] = Field(default_factory=dict)
    first_occurrences: Dict[str, str] = Field(default_factory=dict)

    def record_usage(self, term: str, translation: str, section_id: str) -> None:
        """记录术语使用"""
        key = term.lower()
        if key not in self.used_translations:
            self.used_translations[key] = []
            self.first_occurrences[key] = section_id
        if translation not in self.used_translations[key]:
            self.used_translations[key].append(translation)

    def get_preferred_translation(self, term: str) -> Optional[str]:
        """获取首选翻译（首次使用的译法）"""
        translations = self.used_translations.get(term.lower(), [])
        return translations[0] if translations else None


class LayeredContext(BaseModel):
    """分层翻译上下文"""

    article_theme: str = ""
    article_structure: str = ""
    guidelines: List[str] = Field(default_factory=list)
    terminology: List[EnhancedTerm] = Field(default_factory=list)

    section_role: str = ""
    section_understanding: Optional[SectionUnderstanding] = None
    previous_section_title: Optional[str] = None
    next_section_title: Optional[str] = None

    previous_paragraphs: List[tuple] = Field(default_factory=list)
    next_preview: List[str] = Field(default_factory=list)

    term_usage: Dict[str, List[str]] = Field(default_factory=dict)
    defined_abbreviations: Dict[str, str] = Field(default_factory=dict)
