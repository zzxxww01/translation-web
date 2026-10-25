"""Analysis and four-step translation models."""

from __future__ import annotations

from typing import Annotated, Any, Optional, Dict, List
from pydantic import BaseModel, BeforeValidator, Field, field_validator

from .enums import TranslationStrategy
from .glossary import GlossaryTerm


def _as_text(value: Any) -> str:
    """模型输出里的文字字段：写成对象或数组时拼成一句（如 {"argument": …, "evidence": …}）。

    提示词只列字段名、不给类型，模型常按字段名自由发挥；一个字段类型不对不能让整篇翻译中止。
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "；".join(part for part in (_as_text(item) for item in value.values()) if part)
    if isinstance(value, (list, tuple)):
        return "；".join(part for part in (_as_text(item) for item in value) if part)
    return str(value)


def _as_optional_text(value: Any) -> Any:
    return None if value is None else _as_text(value)


def _as_text_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value] if _as_text(value).strip() else []
    return value


# 模型输出模型的文字字段统一用这几个类型
LooseText = Annotated[str, BeforeValidator(_as_text)]
OptionalLooseText = Annotated[Optional[str], BeforeValidator(_as_optional_text)]
LooseTextList = Annotated[List[LooseText], BeforeValidator(_as_text_list)]


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

    term: LooseText
    context_meaning: LooseText = ""
    translation: OptionalLooseText = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    first_occurrence_note: bool = False
    rationale: OptionalLooseText = None
    alternatives: LooseTextList = Field(default_factory=list)
    avoid: LooseTextList = Field(default_factory=list)
    source_quote: LooseText = ""

    # 这些字段来自模型输出。一个术语的字段类型写错，不能让整篇翻译中止。
    @field_validator("first_occurrence_note", mode="before")
    @classmethod
    def _coerce_note_flag(cls, value: Any) -> Any:
        # 模型有时把它写成一句加注说明（「首现作“CoWoS（…）”，其后保留」）：写了说明就是要首现加注，
        # 只有明确说不需要才算否。
        if value is None:
            return False
        if isinstance(value, str):
            text = value.strip().lower()
            if not text or text in {"false", "no", "none", "null", "0", "n/a"} or text.startswith(("不", "无", "否", "没")):
                return False
            return True
        return value


class ArticleStyle(BaseModel):
    """文章风格分析"""

    tone: LooseText = "professional"
    target_audience: LooseText = ""
    translation_voice: LooseText = ""


class TranslationChallenge(BaseModel):
    """翻译难点"""

    type: LooseText = "accuracy"  # terminology|metaphor|cultural_reference|cross_domain_term|rhetorical_tone|structure|accuracy
    location: LooseText
    issue: LooseText
    suggestion: OptionalLooseText = None


class SectionUnderstanding(BaseModel):
    """章节理解结果（四步法 Step 1 输出）"""

    role_in_article: LooseText = ""
    relation_to_previous: LooseText = ""
    relation_to_next: LooseText = ""
    key_points: LooseTextList = Field(default_factory=list)
    translation_notes: LooseTextList = Field(default_factory=list)
    paragraph_structure: List[Dict[str, Any]] = Field(default_factory=list)


class ArticleAnalysis(BaseModel):
    """全文深度分析结果（Phase 0 输出）"""

    checkpoint_eligible: bool = True
    incomplete_stages: List[str] = Field(default_factory=list)
    theme: LooseText = ""
    key_arguments: LooseTextList = Field(default_factory=list)
    structure_summary: LooseText = ""

    terminology: List[EnhancedTerm] = Field(default_factory=list)
    style: ArticleStyle = Field(default_factory=ArticleStyle)
    challenges: List[TranslationChallenge] = Field(default_factory=list)
    guidelines: LooseTextList = Field(default_factory=list)

    section_roles: Dict[str, SectionUnderstanding] = Field(default_factory=dict)

    section_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0


class TranslationIssue(BaseModel):
    """翻译问题"""

    paragraph_index: int
    priority: str = "P2"
    issue_type: str
    severity: str = "medium"
    original_text: str = ""
    translation_text: str = ""
    description: str
    why_it_matters: str = ""
    suggestion: str = ""
    auto_fixed: bool = False
    revision_attempted: bool = False
    revised_text: Optional[str] = None
    fix_method: Optional[str] = None


class ReflectionResult(BaseModel):
    """反思结果（四步法 Step 3 输出）"""

    overall_score: float = 0.0
    scores_available: bool = True

    # 6 维度评分（方案 C）
    terminology_score: float = 0.0  # 术语一致性
    fluency_score: float = 0.0      # 流畅度
    accuracy_score: float = 0.0     # 准确性
    cultural_score: float = 0.0     # 文化适配
    professional_score: float = 0.0 # 专业性
    readability_score: float = 0.0  # 可读性

    # 兼容旧字段
    conciseness_score: float = 0.0
    consistency_score: float = 0.0
    logic_score: float = 0.0

    is_excellent: bool = False
    issues: List[TranslationIssue] = Field(default_factory=list)
    revised_translations: Optional[Dict[int, str]] = None
    reviewed_version: str = ""
    review_status: str = "complete"
    coverage: float = 1.0


class QualityAssessment(BaseModel):
    """质量评估结果"""

    scores_available: bool = True
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
    revision_attempted: bool = False
    review_history: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_bundle_version: str = ""
    # 降级标记：反思/润色出错时会直接返回初译，此时上层看到的仍是「成功」，
    # 需要靠这两个字段区分「四步成品」与「未经反思/润色/质量门禁的初译」
    degraded: bool = False
    degraded_reason: str = ""
    paused: bool = False
    budget_exhausted: bool = False
    workflow_status: str = "review_pending"


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
    annotation_plan: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class SectionQualityScore(BaseModel):
    """章节质量评分"""

    section_id: str
    section_title: str
    overall_score: float
    readability_score: float
    accuracy_score: float
    conciseness_score: float
    is_excellent: bool
    issue_count: int
    auto_fixed_count: int
    revision_attempted_count: int = 0
    manual_review_count: int
    paragraph_count: int = 0


class QualityReportIssue(BaseModel):
    """质量报告中的可定位问题"""

    section_id: str
    section_title: str
    paragraph_index: int
    issue_type: str
    severity: str
    original_text: str = ""
    translation_text: str = ""
    description: str
    why_it_matters: str = ""
    suggestion: str = ""
    auto_fixed: bool = False
    revision_attempted: bool = False
    auto_fixable: bool = False
    revised_text: Optional[str] = None
    fix_method: Optional[str] = None


class QualityReportSummary(BaseModel):
    """质量报告摘要"""

    run_id: str
    project_id: str
    timestamp: str
    overall_score: float
    sections: List[SectionQualityScore]
    total_issues: int
    auto_fixed_issues: int
    revision_attempted_issues: int = 0
    manual_review_issues: int
    consistency_stats: Dict[str, Any] = Field(default_factory=dict)
    issues: List[QualityReportIssue] = Field(default_factory=list)
    issue_type_counts: Dict[str, int] = Field(default_factory=dict)
    severity_counts: Dict[str, int] = Field(default_factory=dict)
