"""
Translation Agent - Layered Context Manager

分层上下文管理器，为翻译提供多层次的上下文信息。

Layer 1: 全文级上下文（元信息）
Layer 2: 章节级上下文（位置感）
Layer 3: 局部上下文（精确）
Layer 4: 动态累积上下文
"""

from typing import List, Dict, Optional, Tuple

from ..core.constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from ..core.longform_context import build_translation_guidelines
from ..core.models import (
    Section, Paragraph,
    ArticleAnalysis, EnhancedTerm,
    SectionUnderstanding, TermUsageTracker,
    LayeredContext, TermConflict, TermConflictResolution,
    TerminologyVersion, PrescanTerm
)


class LayeredContextManager:
    """分层上下文管理器"""

    def __init__(
        self,
        article_analysis: Optional[ArticleAnalysis] = None,
        context_window_size: int = 3,
        preview_size: int = 2
    ):
        """
        初始化上下文管理器

        Args:
            article_analysis: 全文分析结果
            context_window_size: 前文上下文窗口大小
            preview_size: 后文预览大小
        """
        self.article_analysis = article_analysis
        self.context_window_size = context_window_size
        self.preview_size = preview_size

        # 术语使用追踪
        self.term_tracker = TermUsageTracker()

        # 章节翻译记录 {section_id: [(source, translation), ...]}
        self.section_translations: Dict[str, List[Tuple[str, str]]] = {}

        # 章节理解缓存 {section_id: SectionUnderstanding}
        self.section_understandings: Dict[str, SectionUnderstanding] = {}

        # 已定义的缩写词 {abbreviation: full_form}
        self.defined_abbreviations: Dict[str, str] = {}

        # 方案 C 新增：术语表版本管理
        self.terminology_version = TerminologyVersion()

        # 方案 C 新增：待解决的冲突列表
        self.pending_conflicts: List[TermConflict] = []

        # 方案 C 新增：冲突解决回调
        self._conflict_callback: Optional[callable] = None

    def set_article_analysis(self, analysis: ArticleAnalysis) -> None:
        """设置全文分析结果"""
        self.article_analysis = analysis

    def set_section_understanding(
        self,
        section_id: str,
        understanding: SectionUnderstanding
    ) -> None:
        """缓存章节理解结果"""
        self.section_understandings[section_id] = understanding

    def build_context(
        self,
        current_section: Section,
        current_paragraph_index: int,
        all_sections: List[Section]
    ) -> LayeredContext:
        """
        构建完整的分层上下文

        Args:
            current_section: 当前章节
            current_paragraph_index: 当前段落在章节中的索引
            all_sections: 所有章节列表

        Returns:
            LayeredContext: 分层上下文
        """
        context = LayeredContext()

        # Layer 1: 全文级上下文
        if self.article_analysis:
            context.article_theme = self.article_analysis.theme
            context.article_structure = self.article_analysis.structure_summary
            context.guidelines = build_translation_guidelines(
                self.article_analysis.guidelines
            )
            # 获取当前段落文本用于段落级过滤
            paragraph_text = ""
            if 0 <= current_paragraph_index < len(current_section.paragraphs):
                paragraph_text = current_section.paragraphs[current_paragraph_index].source
            context.terminology = self._get_relevant_terms(current_section, paragraph_text)

        # Layer 2: 章节级上下文
        section_index = self._get_section_index(current_section, all_sections)

        # 章节理解
        if current_section.section_id in self.section_understandings:
            understanding = self.section_understandings[current_section.section_id]
            context.section_understanding = understanding
            context.section_role = understanding.role_in_article

        # 前后章节标题
        if section_index > 0:
            context.previous_section_title = all_sections[section_index - 1].title
        if section_index < len(all_sections) - 1:
            context.next_section_title = all_sections[section_index + 1].title

        # Layer 3: 局部上下文
        context.previous_paragraphs = self._get_previous_paragraphs(
            current_section,
            current_paragraph_index
        )
        context.next_preview = self._get_next_preview(
            current_section,
            current_paragraph_index
        )

        # Layer 4: 动态累积上下文
        context.term_usage = self.term_tracker.used_translations.copy()
        context.defined_abbreviations = self.defined_abbreviations.copy()

        return context

    def record_translation(
        self,
        section_id: str,
        source: str,
        translation: str,
        terms_used: Optional[Dict[str, str]] = None
    ) -> None:
        """
        记录翻译结果，更新动态上下文

        Args:
            section_id: 章节 ID
            source: 原文
            translation: 译文
            terms_used: 使用的术语翻译 {term: translation}
        """
        # 记录段落翻译
        if section_id not in self.section_translations:
            self.section_translations[section_id] = []
        self.section_translations[section_id].append((source, translation))

        # 更新术语使用记录
        if terms_used:
            for term, trans in terms_used.items():
                self.term_tracker.record_usage(term, trans, section_id)

        # 检测并记录缩写词定义
        self._detect_abbreviations(translation)

    def get_section_translations(self, section_id: str) -> List[Tuple[str, str]]:
        """获取章节的所有翻译记录"""
        return self.section_translations.get(section_id, [])

    def get_all_translations(self) -> Dict[str, List[str]]:
        """获取所有章节的译文（用于一致性审查）"""
        return {
            section_id: [t[1] for t in translations]
            for section_id, translations in self.section_translations.items()
        }

    def reset_section(self, section_id: str) -> None:
        """重置章节的翻译记录（用于重新翻译）"""
        if section_id in self.section_translations:
            del self.section_translations[section_id]
        if section_id in self.section_understandings:
            del self.section_understandings[section_id]

    def reset_all(self) -> None:
        """重置所有上下文"""
        self.section_translations.clear()
        self.section_understandings.clear()
        self.term_tracker = TermUsageTracker()
        self.defined_abbreviations.clear()
        self.terminology_version = TerminologyVersion()
        self.pending_conflicts.clear()

    # ============ 方案 C 新增：术语管理方法 ============

    def set_conflict_callback(self, callback: callable) -> None:
        """
        设置冲突检测回调

        当检测到术语冲突时，会调用此回调函数

        Args:
            callback: 回调函数，签名为 (conflict: TermConflict) -> None
        """
        self._conflict_callback = callback

    def add_terms_from_analysis(self, terms: List[EnhancedTerm]) -> List[TermConflict]:
        """
        从全局分析结果添加术语到版本化术语表

        Args:
            terms: 术语列表

        Returns:
            List[TermConflict]: 检测到的冲突列表
        """
        conflicts = []
        for term in terms:
            conflict = self.terminology_version.add_term(term)
            if conflict:
                conflicts.append(conflict)
                self.pending_conflicts.append(conflict)
        return conflicts

    def add_terms_from_prescan(
        self,
        prescan_terms: List[PrescanTerm],
        section_id: str
    ) -> List[TermConflict]:
        """
        从章节预扫描结果添加术语

        检测与现有术语的冲突，如果有冲突则暂停等待用户确认

        Args:
            prescan_terms: 预扫描提取的术语列表
            section_id: 当前章节 ID

        Returns:
            List[TermConflict]: 检测到的冲突列表
        """
        conflicts = []

        for prescan_term in prescan_terms:
            # 转换为 EnhancedTerm
            enhanced_term = EnhancedTerm(
                term=prescan_term.term,
                translation=prescan_term.suggested_translation,
                context_meaning=prescan_term.context
            )

            # 检查是否存在冲突
            existing = self.terminology_version.get_term(prescan_term.term)
            if existing and existing.translation != prescan_term.suggested_translation:
                conflict = TermConflict(
                    term=prescan_term.term,
                    existing_translation=existing.translation or "",
                    new_translation=prescan_term.suggested_translation,
                    existing_context=existing.context_meaning,
                    new_context=prescan_term.context,
                    existing_note=existing.context_meaning,
                    new_note=prescan_term.context,
                    existing_section_id=self.term_tracker.first_occurrences.get(
                        prescan_term.term.lower(), ""
                    ),
                    new_section_id=section_id
                )
                conflicts.append(conflict)
                self.pending_conflicts.append(conflict)

                # 调用冲突回调
                if self._conflict_callback:
                    self._conflict_callback(conflict)
            else:
                # 没有冲突，直接添加
                self.terminology_version.add_term(enhanced_term)
                # 记录首次出现
                if prescan_term.term.lower() not in self.term_tracker.first_occurrences:
                    self.term_tracker.first_occurrences[prescan_term.term.lower()] = section_id
                # 回流到 article_analysis.terminology
                if self.article_analysis:
                    existing_terms_lower = {t.term.lower() for t in self.article_analysis.terminology}
                    if enhanced_term.term.lower() not in existing_terms_lower:
                        self.article_analysis.terminology.append(enhanced_term)

        return conflicts

    def detect_conflict(
        self,
        term: str,
        new_translation: str,
        new_context: str = "",
        section_id: str = ""
    ) -> Optional[TermConflict]:
        """
        检测术语冲突

        Args:
            term: 术语原文
            new_translation: 新翻译
            new_context: 新翻译的上下文
            section_id: 当前章节 ID

        Returns:
            TermConflict: 如果有冲突返回冲突对象，否则返回 None
        """
        existing = self.terminology_version.get_term(term)
        if existing and existing.translation and existing.translation != new_translation:
            return TermConflict(
                term=term,
                existing_translation=existing.translation,
                new_translation=new_translation,
                existing_context=existing.context_meaning,
                new_context=new_context,
                existing_note=existing.context_meaning,
                new_note=new_context,
                existing_section_id=self.term_tracker.first_occurrences.get(
                    term.lower(), ""
                ),
                new_section_id=section_id
            )
        return None

    def resolve_conflict(self, resolution: TermConflictResolution) -> int:
        """
        解决术语冲突

        Args:
            resolution: 冲突解决方案

        Returns:
            int: 受影响的段落数（如果 apply_to_all=True）
        """
        # 更新术语表
        self.terminology_version.resolve_conflict(resolution)

        # 移除待解决冲突
        self.pending_conflicts = [
            c for c in self.pending_conflicts
            if c.term.lower() != resolution.term.lower()
        ]

        # 如果需要应用到所有已翻译段落，返回受影响数量
        affected_count = 0
        if resolution.apply_to_all:
            # 统计包含该术语的段落数
            for section_id, translations in self.section_translations.items():
                for source, _ in translations:
                    if resolution.term.lower() in source.lower():
                        affected_count += 1

        return affected_count

    def has_pending_conflicts(self) -> bool:
        """检查是否有待解决的冲突"""
        return len(self.pending_conflicts) > 0

    def get_pending_conflicts(self) -> List[TermConflict]:
        """获取所有待解决的冲突"""
        return self.pending_conflicts.copy()

    def get_terminology_version(self) -> int:
        """获取当前术语表版本号"""
        return self.terminology_version.version

    def get_all_terms(self) -> Dict[str, str]:
        """获取所有术语的翻译映射"""
        return {
            term: enhanced.translation
            for term, enhanced in self.terminology_version.terms.items()
            if enhanced.translation
        }

    # ============ Private Methods ============

    def _get_section_index(
        self,
        section: Section,
        all_sections: List[Section]
    ) -> int:
        """获取章节在列表中的索引"""
        for i, s in enumerate(all_sections):
            if s.section_id == section.section_id:
                return i
        return 0

    def _get_relevant_terms(self, section: Section, paragraph_text: str = "") -> List[EnhancedTerm]:
        """
        获取与当前段落相关的术语

        合并 article_analysis.terminology 和 terminology_version 中的术语，
        有段落文本时只保留出现在段落中的术语。
        """
        if not self.article_analysis:
            return []

        # 合并 article_analysis.terminology + terminology_version 中的术语
        all_terms: List[EnhancedTerm] = list(self.article_analysis.terminology)
        seen_keys = {t.term.lower() for t in all_terms}
        for key, enhanced in self.terminology_version.terms.items():
            if key not in seen_keys:
                all_terms.append(enhanced)

        para_lower = paragraph_text.lower() if paragraph_text else ""
        relevant = []

        for term in all_terms:
            # 检查是否已使用过，用 .lower() 统一查询
            if term.term.lower() in self.term_tracker.used_translations:
                used_trans = self.term_tracker.get_preferred_translation(term.term)
                if used_trans:
                    term = term.model_copy()
                    term.translation = used_trans

            # 段落级过滤：有段落文本时只保留出现在段落中的术语
            if para_lower and term.term.lower() not in para_lower:
                continue

            relevant.append(term)
            if len(relevant) >= MAX_GLOSSARY_TERMS_IN_PROMPT:
                break

        return relevant

    def _get_previous_paragraphs(
        self,
        section: Section,
        current_index: int
    ) -> List[Tuple[str, str]]:
        """
        获取前文段落（原文+译文）

        优先从当前章节获取，不足时从之前章节补充
        """
        result = []

        # 从当前章节已翻译的段落获取
        section_trans = self.section_translations.get(section.section_id, [])
        if section_trans:
            # 取最近的 N 段
            start = max(0, len(section_trans) - self.context_window_size)
            result = section_trans[start:]

        # 如果不足，从之前章节补充
        if len(result) < self.context_window_size:
            needed = self.context_window_size - len(result)
            for section_id in reversed(list(self.section_translations.keys())):
                if section_id == section.section_id:
                    continue
                prev_trans = self.section_translations[section_id]
                # 取最后几段
                take = min(needed, len(prev_trans))
                result = prev_trans[-take:] + result
                needed -= take
                if needed <= 0:
                    break

        return result[-self.context_window_size:]

    def _get_next_preview(
        self,
        section: Section,
        current_index: int
    ) -> List[str]:
        """获取后文预览（原文）"""
        preview = []
        paragraphs = section.paragraphs

        # 从当前位置之后获取
        for i in range(current_index + 1, min(current_index + 1 + self.preview_size, len(paragraphs))):
            preview.append(paragraphs[i].source)

        return preview

    def _detect_abbreviations(self, text: str) -> None:
        """
        检测并记录缩写词定义

        识别模式如：
        - "高性能计算（HPC）"
        - "HPC（高性能计算）"
        """
        import re

        # 模式1: 中文（英文缩写）
        pattern1 = r'([^\s（(]+)（([A-Z]{2,})）'
        for match in re.finditer(pattern1, text):
            chinese, abbr = match.groups()
            if abbr not in self.defined_abbreviations:
                self.defined_abbreviations[abbr] = chinese

        # 模式2: 英文缩写（中文）
        pattern2 = r'([A-Z]{2,})（([^）]+)）'
        for match in re.finditer(pattern2, text):
            abbr, chinese = match.groups()
            if abbr not in self.defined_abbreviations:
                self.defined_abbreviations[abbr] = chinese


def create_context_manager(
    article_analysis: Optional[ArticleAnalysis] = None,
    context_window_size: int = 3,
    preview_size: int = 2
) -> LayeredContextManager:
    """
    创建上下文管理器

    Args:
        article_analysis: 全文分析结果
        context_window_size: 前文上下文窗口大小
        preview_size: 后文预览大小

    Returns:
        LayeredContextManager: 上下文管理器实例
    """
    return LayeredContextManager(
        article_analysis=article_analysis,
        context_window_size=context_window_size,
        preview_size=preview_size
    )
