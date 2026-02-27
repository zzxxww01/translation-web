"""
Translation Agent - Data Models

Pydantic models for project, section, paragraph, glossary, etc.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class TranslationStrategy(str, Enum):
    """术语翻译策略"""

    PRESERVE = "preserve"  # 全文保持英文原文
    FIRST_ANNOTATE = "first_annotate"  # 首次出现翻译+括号注明，后续用中文
    TRANSLATE = "translate"  # 全文直接使用中文


class ParagraphStatus(str, Enum):
    """段落翻译状态"""

    PENDING = "pending"  # 待翻译
    TRANSLATING = "translating"  # 翻译中
    TRANSLATED = "translated"  # 已翻译，待审阅
    REVIEWING = "reviewing"  # 审阅中
    MODIFIED = "modified"  # 已修改，待确认
    APPROVED = "approved"  # 已确认


class ProjectStatus(str, Enum):
    """项目状态"""

    CREATED = "created"  # 刚创建
    ANALYZING = "analyzing"  # 分析中
    IN_PROGRESS = "in_progress"  # 翻译进行中
    REVIEWING = "reviewing"  # 全文审阅中
    COMPLETED = "completed"  # 已完成


class ElementType(str, Enum):
    """HTML 元素类型"""

    H1 = "h1"
    H2 = "h2"
    H3 = "h3"
    H4 = "h4"
    P = "p"
    LI = "li"
    BLOCKQUOTE = "blockquote"
    CODE = "code"
    TABLE = "table"
    IMAGE = "image"


# ============ Glossary Models ============


class GlossaryTerm(BaseModel):
    """术语表条目"""

    original: str  # 英文原文
    translation: Optional[str] = None  # 中文翻译（preserve 策略时可为空）
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None  # 备注说明
    first_occurrence: Optional[str] = None  # 首次出现的章节 ID


class Glossary(BaseModel):
    """术语表"""

    version: int = 1
    terms: List[GlossaryTerm] = Field(default_factory=list)

    def get_term(self, original: str) -> Optional[GlossaryTerm]:
        """根据原文查找术语"""
        for term in self.terms:
            if term.original.lower() == original.lower():
                return term
        return None

    def add_term(self, term: GlossaryTerm) -> None:
        """添加术语"""
        existing = self.get_term(term.original)
        if existing:
            # 更新现有术语
            idx = self.terms.index(existing)
            self.terms[idx] = term
        else:
            self.terms.append(term)


# ============ Translation Models ============


class TranslationRecord(BaseModel):
    """单次翻译记录"""

    text: str
    model: str  # 使用的模型，如 "gemini", "claude"
    created_at: datetime = Field(default_factory=datetime.now)


class HistoryRecord(BaseModel):
    """修改历史记录"""

    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str  # "gemini", "claude", "manual"


class InlineElement(BaseModel):
    """内联元素（链接、强调等）"""

    type: str  # "link", "strong", "em", "code"
    text: str  # 显示文本
    start: int  # 在原文中的起始位置
    end: int  # 在原文中的结束位置
    href: Optional[str] = None  # 链接URL（仅用于link类型）
    title: Optional[str] = None  # 链接标题（可选）


class Paragraph(BaseModel):
    """段落"""

    id: str  # 段落 ID，如 "p001"
    index: int  # 在章节中的索引
    source: str  # 原文
    source_html: Optional[str] = None  # 原始 HTML（用于保留格式）
    element_type: ElementType = ElementType.P

    # 新增：内联元素信息（链接、强调等）
    inline_elements: Optional[List[InlineElement]] = None

    # 【新增】标题相关字段
    is_heading: bool = False  # 是否是标题
    heading_level: Optional[int] = None  # 标题层级 (1-6)
    heading_chain: List[str] = Field(default_factory=list)  # 父级标题链 ["# 主标题", "## 二级标题"]

    # 【新增】元信息相关
    is_metadata: bool = False  # 是否是元信息（作者、日期等）
    metadata_type: Optional[str] = None  # 元信息类型：author, date, tech_spec

    # 翻译结果
    translations: Dict[str, TranslationRecord] = Field(
        default_factory=dict
    )  # model -> record
    confirmed: Optional[str] = None  # 人工确认的最终译文
    status: ParagraphStatus = ParagraphStatus.PENDING

    # 修改历史
    history: List[HistoryRecord] = Field(default_factory=list)

    def add_translation(self, text: str, model: str) -> None:
        """添加翻译结果"""
        self.translations[model] = TranslationRecord(text=text, model=model)
        if self.status == ParagraphStatus.PENDING:
            self.status = ParagraphStatus.TRANSLATED

    def confirm(self, text: str, source: str = "manual") -> None:
        """确认译文"""
        # 保存历史
        if self.confirmed and self.confirmed != text:
            self.history.append(HistoryRecord(text=self.confirmed, source=source))
        self.confirmed = text
        self.status = ParagraphStatus.APPROVED


# ============ Section Models ============


class Section(BaseModel):
    """章节"""

    section_id: str  # 章节 ID，如 "01-anchor-tenant"
    title: str  # 章节标题
    title_translation: Optional[str] = None  # 标题翻译
    title_source: Optional[str] = None  # 原始标题HTML（保留格式）
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


# ============ Project Models ============


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

    ai_model: str = "gemini-3-pro-preview"  # 默认使用推理模型
    model_type: str = (
        "reasoning"  # "reasoning" (gemini-3-pro-preview) 或 "flash" (gemini-3-flash-preview)
    )
    translation_style: str = "natural_professional"
    segment_level: str = "h2"  # 按 H2 分章节
    max_paragraph_length: int = 800  # 段落最大长度（优化：从500增加到800）
    merge_short_paragraphs: bool = True  # 是否合并短段落


class ArticleMetadata(BaseModel):
    """文章元信息（作者、日期等）"""

    authors: List[str] = Field(default_factory=list)  # 作者列表
    published_date: Optional[str] = None  # 发布日期
    subtitle: Optional[str] = None  # 副标题
    publication: Optional[str] = None  # 出版物/网站名称
    original_url: Optional[str] = None  # 原始URL
    cover_image: Optional[str] = None  # 封面图片路径
    raw_metadata_html: Optional[str] = None  # 原始元信息HTML（用于保留格式）


class ProjectMeta(BaseModel):
    """项目元信息（meta.json）"""

    id: str
    title: str
    title_translation: Optional[str] = None  # 文章标题翻译
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.CREATED
    progress: ProjectProgress = Field(default_factory=ProjectProgress)
    config: ProjectConfig = Field(default_factory=ProjectConfig)

    # 新增：文章元信息
    metadata: Optional[ArticleMetadata] = None

    # 分段确认工作流扩展字段
    sections: List[Section] = Field(default_factory=list)  # 章节列表
    versions: List["TranslationVersion"] = Field(
        default_factory=list
    )  # 导入的参考译文版本
    confirmation_map: Dict[str, "ParagraphConfirmation"] = Field(
        default_factory=dict
    )  # 段落确认状态
    workflow_mode: str = "paragraph_confirmation"  # 工作流模式

    def update_progress(self, sections: List[Section]) -> None:
        """更新进度统计"""
        self.progress.total_sections = len(sections)
        self.progress.total_paragraphs = sum(s.total_paragraphs for s in sections)
        self.progress.approved = sum(s.approved_count for s in sections)
        self.progress.pending = self.progress.total_paragraphs - self.progress.approved
        self.updated_at = datetime.now()


# ============ Analysis Models ============


class StyleGuide(BaseModel):
    """翻译风格指南"""

    tone: str = "professional"  # 语气：professional, casual, academic
    person: str = "third"  # 人称：first, second, third
    formality: str = "formal"  # 正式程度：formal, informal
    notes: List[str] = Field(default_factory=list)  # 其他注意事项


class AnalysisResult(BaseModel):
    """全文分析结果（基础版，保留兼容性）"""

    title: str
    summary: Optional[str] = None  # 文章摘要
    detected_terms: List[GlossaryTerm] = Field(default_factory=list)  # 检测到的术语
    style_guide: StyleGuide = Field(default_factory=StyleGuide)
    section_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0


# ============ Enhanced Analysis Models (四步法) ============


class EnhancedTerm(BaseModel):
    """增强版术语条目"""

    term: str  # 原文术语
    context_meaning: str = ""  # 在本文中的具体含义
    translation: Optional[str] = None  # 建议翻译
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    first_occurrence_note: bool = False  # 首次出现是否需要注释
    rationale: Optional[str] = None  # 翻译理由


class ArticleStyle(BaseModel):
    """文章风格分析"""

    tone: str = "professional"  # 语气：professional/casual/academic
    target_audience: str = ""  # 目标读者
    translation_voice: str = ""  # 翻译时应保持的语气
    data_density: str = "medium"  # 数据密度：high/medium/low


class TranslationChallenge(BaseModel):
    """翻译难点"""

    location: str  # 位置描述
    issue: str  # 问题描述
    suggestion: Optional[str] = None  # 处理建议


class ArticleAnalysis(BaseModel):
    """全文深度分析结果（Phase 0 输出）"""

    # 主题与论点
    theme: str = ""  # 文章核心主题
    key_arguments: List[str] = Field(default_factory=list)  # 主要论点列表
    structure_summary: str = ""  # 逻辑结构概述

    # 术语表（增强版）
    terminology: List[EnhancedTerm] = Field(default_factory=list)

    # 风格分析
    style: ArticleStyle = Field(default_factory=ArticleStyle)

    # 翻译难点
    challenges: List[TranslationChallenge] = Field(default_factory=list)

    # 翻译指南
    guidelines: List[str] = Field(default_factory=list)  # 3-5 条翻译原则

    # 章节角色分析（优化：一次性生成所有章节的角色理解）
    section_roles: Dict[str, SectionUnderstanding] = Field(
        default_factory=dict
    )  # section_id -> 理解结果

    # 统计信息
    section_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0


# ============ Four-Step Translation Models ============


class SectionUnderstanding(BaseModel):
    """章节理解结果（四步法 Step 1 输出）"""

    role_in_article: str = ""  # 在全文论证中的角色
    relation_to_previous: str = ""  # 与前一章节的逻辑关系
    relation_to_next: str = ""  # 与后一章节的逻辑关系
    key_points: List[str] = Field(default_factory=list)  # 核心信息点
    translation_notes: List[str] = Field(default_factory=list)  # 翻译注意事项


class TranslationIssue(BaseModel):
    """翻译问题"""

    paragraph_index: int  # 段落索引
    issue_type: str  # 问题类型: readability/accuracy/terminology/style
    original_text: str = ""  # 原译文片段
    description: str  # 问题描述
    suggestion: str = ""  # 修改建议


class ReflectionResult(BaseModel):
    """反思结果（四步法 Step 3 输出）"""

    overall_score: float = 0.0  # 整体评分 (0-10)
    readability_score: float = 0.0  # 可读性评分
    accuracy_score: float = 0.0  # 准确性评分
    is_excellent: bool = False  # 是否优秀（无需修改）
    issues: List[TranslationIssue] = Field(default_factory=list)


class QualityAssessment(BaseModel):
    """质量评估结果"""

    passed: bool = False  # 是否通过质量门禁
    overall_score: float = 0.0  # 综合评分
    scores: Dict[str, float] = Field(default_factory=dict)  # 各维度评分
    failed_criteria: List[str] = Field(default_factory=list)  # 未通过的标准
    action: str = "pass"  # 建议动作: pass/refine/retranslate


class SectionTranslationResult(BaseModel):
    """章节翻译结果"""

    section_id: str
    translations: List[str] = Field(default_factory=list)
    understanding: Optional[SectionUnderstanding] = None
    reflection: Optional[ReflectionResult] = None
    assessment: Optional[QualityAssessment] = None


# ============ Term Usage Tracking ============


class TermUsageTracker(BaseModel):
    """术语使用追踪"""

    used_translations: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # term -> [已使用的译法]
    first_occurrences: Dict[str, str] = Field(
        default_factory=dict
    )  # term -> 首次出现的章节ID

    def record_usage(self, term: str, translation: str, section_id: str) -> None:
        """记录术语使用"""
        if term not in self.used_translations:
            self.used_translations[term] = []
            self.first_occurrences[term] = section_id
        if translation not in self.used_translations[term]:
            self.used_translations[term].append(translation)

    def get_preferred_translation(self, term: str) -> Optional[str]:
        """获取首选翻译（首次使用的译法）"""
        translations = self.used_translations.get(term, [])
        return translations[0] if translations else None


# ============ Consistency Review Models ============


class ConsistencyIssue(BaseModel):
    """一致性问题"""

    section_id: str
    paragraph_index: int
    issue_type: str  # terminology/style/coherence/reference
    description: str
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None


class ConsistencyReport(BaseModel):
    """一致性审查报告"""

    is_consistent: bool = True
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    auto_fixable: List[ConsistencyIssue] = Field(default_factory=list)
    manual_review: List[ConsistencyIssue] = Field(default_factory=list)

    # 增强字段
    term_stats: Dict[str, Dict] = Field(default_factory=dict)  # 术语使用统计
    style_score: float = 100.0  # 风格一致性评分 (0-100)
    suggestions: List[Dict] = Field(default_factory=list)  # 建议修正列表


# ============ Enhanced Translation Context ============


class LayeredContext(BaseModel):
    """分层翻译上下文"""

    # Layer 1: 全文级上下文
    article_theme: str = ""
    article_structure: str = ""
    guidelines: List[str] = Field(default_factory=list)
    terminology: List[EnhancedTerm] = Field(default_factory=list)

    # Layer 2: 章节级上下文
    section_role: str = ""
    section_understanding: Optional[SectionUnderstanding] = None
    previous_section_title: Optional[str] = None
    next_section_title: Optional[str] = None

    # Layer 3: 局部上下文
    previous_paragraphs: List[tuple] = Field(
        default_factory=list
    )  # [(source, translation), ...]
    next_preview: List[str] = Field(default_factory=list)

    # Layer 4: 动态累积上下文
    term_usage: Dict[str, List[str]] = Field(default_factory=dict)
    defined_abbreviations: Dict[str, str] = Field(default_factory=dict)


# ============ Paragraph Confirmation Workflow Models ============


class TranslationVersion(BaseModel):
    """翻译版本（导入的参考译文）"""

    id: str  # 版本ID，如 "ref_v1_0"
    name: str  # 版本名称，如 "网友翻译v1.0"
    source_type: str  # "ai" or "imported"
    paragraphs: Dict[str, Optional[str]] = Field(
        default_factory=dict
    )  # paragraph_id -> translation
    metadata: Optional[Dict] = None  # 元数据（导入时间、来源等）
    created_at: datetime = Field(default_factory=datetime.now)


class ParagraphConfirmation(BaseModel):
    """段落确认状态"""

    paragraph_id: str  # 段落ID
    selected_version_id: Optional[str] = None  # 选中的版本ID
    custom_translation: Optional[str] = None  # 自定义编辑的译文
    confirmed_at: Optional[datetime] = None  # 确认时间


class AIInsight(BaseModel):
    """AI透明度数据（四步法翻译结果）"""

    overall_score: float  # 整体质量评分 (0-10)
    is_excellent: bool  # 是否优秀（无需修改）
    applied_terms: List[str]  # 应用的术语列表
    style: str  # 翻译风格
    steps: Dict[str, bool]  # 各步骤完成状态

    # 可选的详细信息
    understanding: Optional[str] = None  # 章节理解
    scores: Optional[Dict[str, float]] = None  # 各维度评分
    issues: Optional[List[Dict]] = None  # 发现的问题


# ============ Retranslate Options ============


class RetranslateOption(BaseModel):
    """重新翻译选项"""

    id: str  # 选项ID，如 "fluent", "professional"
    label: str  # 显示标签，如 "更流畅"
    description: str  # 描述说明
    instruction: str  # 给AI的指令


# ============ Consistency Review Enhanced Models ============


class TermUsageStats(BaseModel):
    """术语使用统计"""

    term: str  # 原文术语
    expected_translation: str  # 预期翻译
    actual_translations: List[str] = Field(default_factory=list)  # 实际使用的翻译
    occurrences: int = 0  # 出现次数
    consistent: bool = True  # 是否一致


class StyleScore(BaseModel):
    """风格评分"""

    dimension: str  # 维度名称
    score: float  # 评分 (0-10)
    notes: str = ""  # 备注


class ConsistencyReviewResult(BaseModel):
    """增强版一致性审查结果"""

    is_consistent: bool = True
    overall_score: float = 0.0  # 整体一致性评分 (0-100)

    # 术语统计
    terminology_stats: List[TermUsageStats] = Field(default_factory=list)

    # 风格评分
    style_scores: List[StyleScore] = Field(default_factory=list)

    # 问题列表
    issues: List[ConsistencyIssue] = Field(default_factory=list)

    # 建议修正
    suggestions: List[Dict] = Field(
        default_factory=list
    )  # [{paragraph_id, current, suggested, reason}]

    # 分类
    auto_fixable: List[ConsistencyIssue] = Field(default_factory=list)
    manual_review: List[ConsistencyIssue] = Field(default_factory=list)


# ============ Section Prescan Models (方案 C 新增) ============


class PrescanTerm(BaseModel):
    """预扫描提取的术语"""

    term: str  # 原文术语
    suggested_translation: str  # 建议翻译
    context: str = ""  # 出现上下文
    confidence: float = 0.8  # 置信度 (0-1)


class SectionPrescanResult(BaseModel):
    """章节预扫描结果（方案 C - Phase 1 Step 1）"""

    section_id: str
    new_terms: List[PrescanTerm] = Field(default_factory=list)  # 新发现的术语
    term_usages: Dict[str, str] = Field(default_factory=dict)  # 现有术语使用 {term: used_translation}
    scan_coverage: float = 1.0  # 扫描覆盖率
    scanned_at: datetime = Field(default_factory=datetime.now)


class TermConflict(BaseModel):
    """术语冲突信息（需要人工确认）"""

    term: str  # 冲突的术语
    existing_translation: str  # 已有翻译
    new_translation: str  # 新建议翻译
    existing_context: str = ""  # 已有翻译的上下文
    new_context: str = ""  # 新翻译的上下文
    existing_section_id: str = ""  # 首次出现的章节 ID
    new_section_id: str = ""  # 当前章节 ID
    created_at: datetime = Field(default_factory=datetime.now)


class TermConflictResolution(BaseModel):
    """术语冲突解决方案"""

    term: str  # 冲突的术语
    chosen_translation: str  # 用户选择的翻译
    apply_to_all: bool = True  # 是否应用到所有已翻译的段落
    resolved_at: datetime = Field(default_factory=datetime.now)


class TerminologyVersion(BaseModel):
    """术语表版本（支持增量更新）"""

    version: int = 1
    terms: Dict[str, EnhancedTerm] = Field(default_factory=dict)  # term -> EnhancedTerm
    conflicts: List[TermConflict] = Field(default_factory=list)  # 未解决的冲突
    resolved_conflicts: List[TermConflictResolution] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_term(self, term: EnhancedTerm) -> Optional[TermConflict]:
        """
        添加术语，如果存在冲突则返回冲突对象

        Returns:
            TermConflict: 如果有冲突返回冲突对象，否则返回 None
        """
        key = term.term.lower()
        if key in self.terms:
            existing = self.terms[key]
            # 检查翻译是否不同
            if existing.translation != term.translation:
                conflict = TermConflict(
                    term=term.term,
                    existing_translation=existing.translation or "",
                    new_translation=term.translation or "",
                    existing_context=existing.context_meaning,
                    new_context=term.context_meaning
                )
                self.conflicts.append(conflict)
                return conflict
        else:
            self.terms[key] = term
            self.version += 1
            self.updated_at = datetime.now()
        return None

    def get_term(self, term: str) -> Optional[EnhancedTerm]:
        """根据术语获取翻译"""
        return self.terms.get(term.lower())

    def resolve_conflict(self, resolution: TermConflictResolution) -> None:
        """解决冲突"""
        key = resolution.term.lower()
        # 更新术语表
        if key in self.terms:
            self.terms[key].translation = resolution.chosen_translation
        # 移除冲突记录
        self.conflicts = [c for c in self.conflicts if c.term.lower() != key]
        self.resolved_conflicts.append(resolution)
        self.version += 1
        self.updated_at = datetime.now()
