"""
Translation Agent - Four-Step Translator

四步法章节翻译器

Step 1: 理解 (Understand) - 理解章节在全文中的位置和作用
Step 2: 初译 (Translate) - 基于深度理解完成第一版翻译
Step 3: 反思 (Reflect) - 以第一读者视角审视译文（批量）
Step 4: 润色 (Refine) - 针对问题优化译文（仅在需要时）

方案 C 新增：
Step 0: 预扫描 (Prescan) - 使用 Flash 模型快速扫描章节，提取术语并检测冲突
"""

from typing import List, Optional, Callable, Dict, Any
import logging

from ..core.models import (
    Section, Paragraph,
    ArticleAnalysis, SectionUnderstanding,
    ReflectionResult, TranslationIssue,
    QualityAssessment, SectionTranslationResult,
    LayeredContext, EnhancedTerm, PrescanTerm,
    SectionPrescanResult, TermConflict
)
from ..llm.base import LLMProvider
from .context_manager import LayeredContextManager
from .quality_gate import QualityGate


class FourStepTranslator:
    """四步法翻译器"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        context_manager: LayeredContextManager,
        quality_gate: Optional[QualityGate] = None,
        paragraph_threshold: int = 8,
        max_retries: int = 2
    ):
        """
        初始化四步法翻译器

        Args:
            llm_provider: LLM Provider
            context_manager: 分层上下文管理器
            quality_gate: 质量门禁（可选）
            paragraph_threshold: 混合模式阈值，超过此数量的段落分批翻译
            max_retries: 最大重试次数
        """
        self.llm = llm_provider
        self.context_manager = context_manager
        self.quality_gate = quality_gate or QualityGate(mode="strict")
        self.paragraph_threshold = paragraph_threshold
        self.max_retries = max_retries

    # ============ 方案 C 新增：章节预扫描 ============

    def prescan_section(
        self,
        section: Section,
        on_conflict: Optional[Callable[[TermConflict], None]] = None
    ) -> Optional[SectionPrescanResult]:
        """
        章节预扫描（方案 C - Phase 1 Step 0）

        使用 Flash 模型快速扫描章节，提取新术语并检测冲突

        Args:
            section: 要扫描的章节
            on_conflict: 冲突回调函数

        Returns:
            SectionPrescanResult: 预扫描结果
        """
        # 获取章节完整内容
        section_content = "\n\n".join([p.source for p in section.paragraphs])

        # 获取现有术语表
        existing_terms = self.context_manager.get_all_terms()

        # 调用 LLM 预扫描（使用 Flash 模型）
        try:
            if hasattr(self.llm, "prescan_section_with_flash"):
                result = self.llm.prescan_section_with_flash(
                    section_id=section.section_id,
                    section_title=section.title,
                    section_content=section_content,
                    existing_terms=existing_terms
                )
            else:
                result = self.llm.prescan_section(
                    section_id=section.section_id,
                    section_title=section.title,
                    section_content=section_content,
                    existing_terms=existing_terms
                )
        except Exception as e:
            # 预扫描失败不阻塞翻译流程
            logging.warning(f"Section prescan failed: {e}")
            return None

        # 解析新术语
        new_terms = []
        for term_data in result.get("new_terms", []):
            new_terms.append(PrescanTerm(
                term=term_data.get("term", ""),
                suggested_translation=term_data.get("suggested_translation", ""),
                context=term_data.get("context", ""),
                confidence=term_data.get("confidence", 0.8)
            ))

        # 检测术语冲突
        conflicts = self.context_manager.add_terms_from_prescan(
            new_terms,
            section.section_id
        )

        # 如果有冲突且提供了回调，调用回调
        if conflicts and on_conflict:
            for conflict in conflicts:
                on_conflict(conflict)

        return SectionPrescanResult(
            section_id=section.section_id,
            new_terms=new_terms,
            term_usages=result.get("term_usages", {}),
            scan_coverage=1.0
        )

    def translate_section(
        self,
        section: Section,
        all_sections: List[Section],
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        retry_count: int = 0
    ) -> SectionTranslationResult:
        """
        翻译整个章节（四步法）

        混合模式：
        - 短章节（≤ threshold）：整体翻译
        - 长章节（> threshold）：分批翻译，每批 threshold 段

        Args:
            section: 要翻译的章节
            all_sections: 所有章节列表
            on_progress: 进度回调 (step_name, current, total)
            retry_count: 当前重试次数

        Returns:
            SectionTranslationResult: 翻译结果
        """
        if on_progress:
            on_progress("理解章节", 0, 4)

        # Step 1: 理解章节
        understanding = self._step_understand(section, all_sections)
        self.context_manager.set_section_understanding(
            section.section_id, understanding
        )

        if on_progress:
            on_progress("初译", 1, 4)

        # Step 2: 初译（混合模式）
        if len(section.paragraphs) <= self.paragraph_threshold:
            # 短章节：整体翻译
            translations = self._translate_batch(
                section, section.paragraphs, understanding, all_sections
            )
        else:
            # 长章节：分批翻译
            translations = []
            batches = self._split_into_batches(section.paragraphs)
            for batch_idx, batch in enumerate(batches):
                batch_translations = self._translate_batch(
                    section, batch, understanding, all_sections,
                    batch_index=batch_idx
                )
                translations.extend(batch_translations)

        if on_progress:
            on_progress("反思", 2, 4)

        # Step 3: 批量反思
        reflection = self._step_reflect(section, translations)

        if on_progress:
            on_progress("润色", 3, 4)

        # Step 4: 润色（如果需要）
        if not reflection.is_excellent and reflection.issues:
            translations = self._step_refine(section, translations, reflection)

        # 质量门禁检查
        assessment = self.quality_gate.assess(section, translations, reflection)

        # 如果未通过且需要重译
        if not assessment.passed and assessment.action == "retranslate":
            if retry_count < self.max_retries:
                # 重置章节上下文
                self.context_manager.reset_section(section.section_id)
                # 递归重试
                return self.translate_section(
                    section, all_sections, on_progress, retry_count + 1
                )

        if on_progress:
            on_progress("完成", 4, 4)

        # 记录翻译结果到上下文管理器
        for i, (para, trans) in enumerate(zip(section.paragraphs, translations)):
            self.context_manager.record_translation(
                section.section_id,
                para.source,
                trans,
                self._extract_terms_used(para.source, trans)
            )

        return SectionTranslationResult(
            section_id=section.section_id,
            translations=translations,
            understanding=understanding,
            reflection=reflection,
            assessment=assessment
        )

    def translate_paragraph(
        self,
        paragraph: Paragraph,
        section: Section,
        all_sections: List[Section],
        understanding: Optional[SectionUnderstanding] = None
    ) -> str:
        """
        翻译单个段落（用于交互式翻译）

        Args:
            paragraph: 要翻译的段落
            section: 所属章节
            all_sections: 所有章节列表
            understanding: 章节理解（可选，如果没有会自动生成）

        Returns:
            str: 译文
        """
        # 如果没有章节理解，先生成
        if understanding is None:
            if section.section_id in self.context_manager.section_understandings:
                understanding = self.context_manager.section_understandings[section.section_id]
            else:
                understanding = self._step_understand(section, all_sections)
                self.context_manager.set_section_understanding(
                    section.section_id, understanding
                )

        # 获取段落索引
        para_index = next(
            (i for i, p in enumerate(section.paragraphs) if p.id == paragraph.id),
            0
        )

        # 构建上下文
        context = self.context_manager.build_context(
            section, para_index, all_sections
        )
        context.section_understanding = understanding

        # 翻译
        translation = self._translate_single_paragraph(paragraph, context)

        # 记录
        self.context_manager.record_translation(
            section.section_id,
            paragraph.source,
            translation,
            self._extract_terms_used(paragraph.source, translation)
        )

        return translation

    # ============ Step 1: 理解 ============

    def _step_understand(
        self,
        section: Section,
        all_sections: List[Section]
    ) -> SectionUnderstanding:
        """Step 1: 理解章节（优化：优先使用预分析结果）"""
        # 优化：优先使用 Phase 0 中预分析的章节角色
        if (
            self.context_manager.article_analysis and
            self.context_manager.article_analysis.section_roles and
            section.section_id in self.context_manager.article_analysis.section_roles
        ):
            # 直接使用预分析结果，跳过 LLM 调用
            return self.context_manager.article_analysis.section_roles[section.section_id]

        # 回退：如果没有预分析结果，调用 LLM 分析
        section_content = "\n\n".join([p.source for p in section.paragraphs])

        # 获取全文分析信息
        article_theme = ""
        structure_summary = ""
        if self.context_manager.article_analysis:
            article_theme = self.context_manager.article_analysis.theme
            structure_summary = self.context_manager.article_analysis.structure_summary

        # 获取章节标题列表
        section_titles = [s.title for s in all_sections]

        # 获取当前章节索引
        current_index = next(
            (i for i, s in enumerate(all_sections) if s.section_id == section.section_id),
            0
        )

        # 调用 LLM 理解章节
        result = self.llm.understand_section(
            section_content=section_content,
            article_theme=article_theme,
            structure_summary=structure_summary,
            section_titles=section_titles,
            current_index=current_index
        )

        return SectionUnderstanding(
            role_in_article=result.get("role_in_article", ""),
            relation_to_previous=result.get("relation_to_previous", ""),
            relation_to_next=result.get("relation_to_next", ""),
            key_points=result.get("key_points", []),
            translation_notes=result.get("translation_notes", [])
        )

    # ============ Step 2: 初译 ============

    def _translate_batch(
        self,
        section: Section,
        paragraphs: List[Paragraph],
        understanding: SectionUnderstanding,
        all_sections: List[Section],
        batch_index: int = 0
    ) -> List[str]:
        """Step 2: 批量初译"""
        translations = []

        for i, paragraph in enumerate(paragraphs):
            # 计算全局索引
            global_index = batch_index * self.paragraph_threshold + i

            # 构建分层上下文
            context = self.context_manager.build_context(
                section, global_index, all_sections
            )
            context.section_understanding = understanding

            # 翻译单个段落
            translation = self._translate_single_paragraph(paragraph, context)
            translations.append(translation)

            # 临时记录到上下文（用于后续段落的前文参考）
            self.context_manager.record_translation(
                section.section_id,
                paragraph.source,
                translation,
                self._extract_terms_used(paragraph.source, translation)
            )

        return translations

    def _translate_single_paragraph(
        self,
        paragraph: Paragraph,
        context: LayeredContext
    ) -> str:
        """翻译单个段落"""
        # 构建翻译上下文
        llm_context = self._build_translation_context(context)

        # 调用 LLM 翻译
        translation = self.llm.translate(paragraph.source, llm_context)

        return translation.strip()

    def _build_translation_context(self, context: LayeredContext) -> Dict[str, Any]:
        """构建 LLM 翻译上下文"""
        llm_context = {}

        # 术语表
        if context.terminology:
            llm_context["glossary"] = [
                {
                    "original": term.term,
                    "translation": term.translation,
                    "strategy": term.strategy.value if hasattr(term.strategy, 'value') else term.strategy,
                    "note": term.context_meaning
                }
                for term in context.terminology
            ]

        # 风格指南
        if context.guidelines:
            llm_context["style_guide"] = {
                "notes": context.guidelines
            }

        # 章节理解
        if context.section_understanding:
            llm_context["section_context"] = {
                "role": context.section_understanding.role_in_article,
                "relation_to_previous": context.section_understanding.relation_to_previous,
                "key_points": context.section_understanding.key_points,
                "translation_notes": context.section_understanding.translation_notes
            }

        # 全文背景
        if context.article_theme:
            llm_context["article_theme"] = context.article_theme
        if context.article_structure:
            llm_context["article_structure"] = context.article_structure

        # 前文上下文
        if context.previous_paragraphs:
            llm_context["previous_paragraphs"] = context.previous_paragraphs

        # 后文预览
        if context.next_preview:
            llm_context["next_preview"] = context.next_preview

        return llm_context

    # ============ Step 3: 反思 ============

    def _step_reflect(
        self,
        section: Section,
        translations: List[str]
    ) -> ReflectionResult:
        """Step 3: 批量反思"""
        # 获取原文列表
        source_paragraphs = [p.source for p in section.paragraphs]

        # 获取翻译指南和术语表
        guidelines = []
        terminology = []
        if self.context_manager.article_analysis:
            guidelines = self.context_manager.article_analysis.guidelines
            terminology = [
                {
                    "term": t.term,
                    "translation": t.translation,
                    "context_meaning": t.context_meaning
                }
                for t in self.context_manager.article_analysis.terminology
            ]

        # 调用 LLM 反思
        result = self.llm.reflect_on_translation(
            source_paragraphs=source_paragraphs,
            translations=translations,
            guidelines=guidelines,
            terminology=terminology
        )

        # 解析问题列表
        issues = []
        for issue_data in result.get("issues", []):
            issues.append(TranslationIssue(
                paragraph_index=issue_data.get("paragraph_index", 0),
                issue_type=issue_data.get("issue_type", "readability"),
                original_text=issue_data.get("original_text", ""),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion", "")
            ))

        return ReflectionResult(
            overall_score=float(result.get("overall_score", 0)),
            readability_score=float(result.get("readability_score", 0)),
            accuracy_score=float(result.get("accuracy_score", 0)),
            is_excellent=result.get("is_excellent", False),
            issues=issues
        )

    # ============ Step 4: 润色 ============

    def _step_refine(
        self,
        section: Section,
        translations: List[str],
        reflection: ReflectionResult
    ) -> List[str]:
        """Step 4: 针对性润色"""
        refined = translations.copy()

        for issue in reflection.issues:
            idx = issue.paragraph_index
            if 0 <= idx < len(refined):
                # 获取原文
                source = section.paragraphs[idx].source

                # 调用 LLM 润色
                refined_text = self.llm.refine_translation(
                    source=source,
                    current_translation=refined[idx],
                    issue_type=issue.issue_type,
                    description=issue.description,
                    suggestion=issue.suggestion
                )

                refined[idx] = refined_text.strip()

        return refined

    # ============ Helper Methods ============

    def _split_into_batches(self, paragraphs: List[Paragraph]) -> List[List[Paragraph]]:
        """将段落列表分批"""
        batches = []
        for i in range(0, len(paragraphs), self.paragraph_threshold):
            batches.append(paragraphs[i:i + self.paragraph_threshold])
        return batches

    def _extract_terms_used(self, source: str, translation: str) -> Dict[str, str]:
        """
        从翻译结果中提取使用的术语

        简单实现：检查术语表中的术语是否出现在原文中，
        如果出现，记录其在译文中的翻译
        """
        terms_used = {}

        if not self.context_manager.article_analysis:
            return terms_used

        source_lower = source.lower()

        for term in self.context_manager.article_analysis.terminology:
            if term.term.lower() in source_lower:
                # 术语出现在原文中，记录翻译
                if term.translation:
                    terms_used[term.term] = term.translation

        return terms_used


def create_four_step_translator(
    llm_provider: LLMProvider,
    context_manager: LayeredContextManager,
    quality_gate: Optional[QualityGate] = None,
    paragraph_threshold: int = 8,
    max_retries: int = 2
) -> FourStepTranslator:
    """
    创建四步法翻译器

    Args:
        llm_provider: LLM Provider
        context_manager: 分层上下文管理器
        quality_gate: 质量门禁
        paragraph_threshold: 混合模式阈值
        max_retries: 最大重试次数

    Returns:
        FourStepTranslator: 翻译器实例
    """
    return FourStepTranslator(
        llm_provider=llm_provider,
        context_manager=context_manager,
        quality_gate=quality_gate,
        paragraph_threshold=paragraph_threshold,
        max_retries=max_retries
    )
