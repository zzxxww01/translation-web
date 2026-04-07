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

from collections import defaultdict
from typing import List, Optional, Callable, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

from ..core.longform_context import (
    build_article_challenge_payload,
    build_glossary_entries_from_terms,
    build_review_priorities,
    build_review_term_entries,
    build_section_context_payload,
    build_translation_guidelines,
)
from ..core.glossary_prompt import select_prompt_terms_for_text, _count_term_occurrences
from ..core.format_tokens import (
    TranslationPayload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
    format_token_context,
)
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
        max_retries: int = 1,
        memory_service=None,
        style_polish_threshold: float = 8.0
    ):
        """
        初始化四步法翻译器

        Args:
            llm_provider: LLM Provider
            context_manager: 分层上下文管理器
            quality_gate: 质量门禁（可选）
            paragraph_threshold: 混合模式阈值，超过此数量的段落分批翻译
            max_retries: 最大重试次数
            memory_service: 翻译记忆服务（可选，用于反思评分学习）
            style_polish_threshold: 简洁性评分低于此阈值时触发 Style Polish（设为 0 关闭）
        """
        self.llm = llm_provider
        self.context_manager = context_manager
        self.quality_gate = quality_gate or QualityGate(mode="standard")
        self.paragraph_threshold = paragraph_threshold
        self.max_retries = max_retries
        self.memory_service = memory_service
        self.style_polish_threshold = style_polish_threshold

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
            result = self.llm.prescan_section_with_flash(
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
        retry_count: int = 0,
        project_id: Optional[str] = None,
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
            translation_outputs = self._translate_batch(
                section, section.paragraphs, understanding, all_sections
            )
        else:
            # 长章节：分批翻译
            translation_outputs = []
            batches = self._split_into_batches(section.paragraphs)
            for batch_idx, batch in enumerate(batches):
                batch_outputs = self._translate_batch(
                    section, batch, understanding, all_sections,
                    batch_index=batch_idx
                )
                translation_outputs.extend(batch_outputs)

        translations = [item.text for item in translation_outputs]

        draft_translations = list(translations)

        if on_progress:
            on_progress("反思", 2, 4)

        # Step 3: 批量反思
        reflection = self._step_reflect(
            section,
            translations,
            understanding,
        )

        # 自学习：反思评分 < 8.0 且有具体 issues 时，后台提取规则
        if (
            self.memory_service
            and reflection.overall_score < 8.0
            and reflection.issues
        ):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.memory_service.process_reflection_issues(
                            reflection.issues,
                            translations,
                        )
                    )
            except Exception as e:
                logger.debug("Failed to schedule reflection rule extraction: %s", e)

        if on_progress:
            on_progress("润色", 3, 4)

        # Step 4: 润色（如果需要）
        if not reflection.is_excellent and reflection.issues:
            translation_outputs = self._step_refine(
                section,
                translation_outputs,
                reflection,
                understanding,
            )
            translations = [item.text for item in translation_outputs]

        # Step 5: 风格润色（可选，conciseness_score 低于阈值时触发）
        if (
            self.style_polish_threshold > 0
            and reflection.conciseness_score > 0
            and reflection.conciseness_score < self.style_polish_threshold
        ):
            translation_outputs = self._step_style_polish(
                section, translation_outputs
            )
            translations = [item.text for item in translation_outputs]

        revised_translations = list(translations)

        # 质量门禁检查
        assessment = self.quality_gate.assess(section, translations, reflection)

        # 如果未通过且需要重译
        if not assessment.passed and assessment.action == "retranslate":
            if retry_count < self.max_retries:
                # 重置章节上下文
                self.context_manager.reset_section(section.section_id)
                # 递归重试
                return self.translate_section(
                    section,
                    all_sections,
                    on_progress,
                    retry_count + 1,
                    project_id=project_id,
                )

        if on_progress:
            on_progress("完成", 4, 4)

        return SectionTranslationResult(
            section_id=section.section_id,
            translations=translations,
            draft_translations=draft_translations,
            revised_translations=revised_translations,
            translation_outputs=[
                {
                    "text": item.text,
                    "tokenized_text": item.tokenized_text,
                    "format_issues": list(item.format_issues),
                }
                for item in translation_outputs
            ],
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
        payload = self._translate_single_paragraph(paragraph, context)

        # 记录
        self.context_manager.record_translation(
            section.section_id,
            paragraph.source,
            payload.text,
            self._extract_terms_used(paragraph.source, payload.text)
        )

        return payload.text

    # ============ Step 1: 理解 ============

    def _step_understand(
        self,
        section: Section,
        all_sections: List[Section]
    ) -> SectionUnderstanding:
        """Step 1: 从预分析结果中读取章节理解。"""
        if (
            self.context_manager.article_analysis and
            self.context_manager.article_analysis.section_roles and
            section.section_id in self.context_manager.article_analysis.section_roles
        ):
            return self.context_manager.article_analysis.section_roles[section.section_id]

        raise RuntimeError(
            "Missing precomputed section role context. "
            "The unified longform flow now requires deep analysis before four-step translation."
        )

    # ============ Step 2: 初译 ============

    def _translate_batch(
        self,
        section: Section,
        paragraphs: List[Paragraph],
        understanding: SectionUnderstanding,
        all_sections: List[Section],
        batch_index: int = 0
    ) -> List[TranslationPayload]:
        """Step 2: 批量初译 — 使用 translate_section 一次翻译整批段落"""
        section_lines = []
        paragraph_ids = []
        dehydrated_results: Dict[str, TranslationPayload] = {}
        format_tokens = []
        token_count = 0
        batch_source_text_parts: List[str] = []

        for para in paragraphs:
            dehydrated_payload = build_dehydrated_link_payload(para)
            if dehydrated_payload is not None:
                dehydrated_results[para.id] = dehydrated_payload
                continue

            prepared = build_translation_input(para)
            prompt_text = prepared.tokenized_text or prepared.text
            section_lines.append(f"[{para.id}] {prompt_text}")
            paragraph_ids.append(para.id)
            batch_source_text_parts.append(para.source)
            if para.inline_elements:
                format_tokens.extend(
                    [
                        {
                            "id": element.span_id,
                            "type": element.type,
                            "text": element.text,
                            "paragraph_id": para.id,
                        }
                        for element in para.inline_elements
                        if element.span_id
                    ]
                )
                token_count += len(para.inline_elements)

        # 如果所有段落都是 dehydrated，直接返回
        if not section_lines:
            return [dehydrated_results[p.id] for p in paragraphs if p.id in dehydrated_results]

        # 构建批量翻译上下文
        batch_source_text = "\n\n".join(batch_source_text_parts)
        context = self._build_batch_context(
            section,
            batch_source_text,
            understanding,
            all_sections,
            format_tokens,
            token_count,
        )

        # 单次 API 调用翻译整批段落
        section_text = "\n\n".join(section_lines)
        translated = self.llm.translate_section(
            section_text, section.title, context, paragraph_ids
        )

        # 将 JSON 结果映射回 TranslationPayload
        trans_map = {item["id"]: item["translation"] for item in translated}

        translations: List[TranslationPayload] = []
        for para in paragraphs:
            if para.id in dehydrated_results:
                translations.append(dehydrated_results[para.id])
            elif para.id in trans_map:
                payload = build_translation_payload(
                    para,
                    trans_map[para.id].strip(),
                    token_repairer=self._repair_format_tokens,
                )
                translations.append(payload)
                self.context_manager.record_translation(
                    section.section_id,
                    para.source,
                    payload.text,
                    self._extract_terms_used(para.source, payload.text),
                )
            else:
                # 回退：translate_section 遗漏了此段落，使用单段翻译
                logger.warning(
                    "Batch translation missing paragraph %s, falling back to single",
                    para.id,
                )
                global_index = batch_index * self.paragraph_threshold + paragraphs.index(para)
                ctx = self.context_manager.build_context(section, global_index, all_sections)
                ctx.section_understanding = understanding
                payload = self._translate_single_paragraph(para, ctx)
                translations.append(payload)
                self.context_manager.record_translation(
                    section.section_id,
                    para.source,
                    payload.text,
                    self._extract_terms_used(para.source, payload.text),
                )

        return translations

    def _build_batch_context(
        self,
        section: Section,
        batch_source_text: str,
        understanding: SectionUnderstanding,
        all_sections: List[Section],
        format_tokens: List[Dict[str, Any]],
        token_count: int = 0,
    ) -> Dict[str, Any]:
        """构建批量翻译的上下文，复用 _build_section_prompt_context 的逻辑并注入四步法特有信息"""
        article_analysis = self.context_manager.article_analysis

        section_index = next(
            (i for i, s in enumerate(all_sections) if s.section_id == section.section_id),
            0,
        )
        total_sections = len(all_sections)

        context: Dict[str, Any] = {
            "article_theme": article_analysis.theme if article_analysis else "",
            "target_audience": (
                article_analysis.style.target_audience if article_analysis else ""
            ),
            "translation_voice": (
                article_analysis.style.translation_voice if article_analysis else ""
            ),
            "section_position": f"第 {section_index + 1}/{total_sections} 章节",
            "previous_section_title": (
                all_sections[section_index - 1].title if section_index > 0 else "无"
            ),
            "next_section_title": (
                all_sections[section_index + 1].title
                if section_index < total_sections - 1
                else "无"
            ),
            "glossary": (
                build_glossary_entries_from_terms(
                    select_prompt_terms_for_text(
                        self._apply_term_tracker_corrections(
                            article_analysis.terminology
                        ),
                        batch_source_text,
                    )
                )
                if article_analysis
                else []
            ),
            "guidelines": (
                build_translation_guidelines(article_analysis.guidelines)
                if article_analysis
                else []
            ),
            "section_role": (
                build_section_context_payload(understanding).get("role", "")
            ),
            "translation_notes": (
                build_section_context_payload(understanding).get("translation_notes", [])
            ),
            "article_challenges": (
                build_article_challenge_payload(article_analysis.challenges)
                if article_analysis
                else []
            ),
            "format_tokens": format_tokens,
            "format_token_count": token_count,
        }

        # 注入前文译文：优先使用当前章节已完成批次的译文，不足时再回退到上一章节。
        previous_context_pairs: List[tuple[str, str]] = []

        current_section_translations = self.context_manager.get_section_translations(
            section.section_id
        )
        if current_section_translations:
            previous_context_pairs.extend(current_section_translations[-5:])

        if len(previous_context_pairs) < 5 and section_index > 0:
            prev_section_id = all_sections[section_index - 1].section_id
            prev_translations = self.context_manager.get_section_translations(
                prev_section_id
            )
            if prev_translations:
                needed = 5 - len(previous_context_pairs)
                previous_context_pairs = prev_translations[-needed:] + previous_context_pairs

        if previous_context_pairs:
            context["previous_translations"] = [
                {"source": src, "translation": trans}
                for src, trans in previous_context_pairs
            ]

        # 注入术语使用记录
        if self.context_manager.term_tracker.used_translations:
            context["term_usage"] = self.context_manager.term_tracker.used_translations.copy()

        return context

    def _translate_single_paragraph(
        self,
        paragraph: Paragraph,
        context: LayeredContext
    ) -> TranslationPayload:
        dehydrated_payload = build_dehydrated_link_payload(paragraph)
        if dehydrated_payload is not None:
            return dehydrated_payload

        # 构建翻译上下文
        llm_context = self._build_translation_context(context)
        if paragraph.inline_elements:
            llm_context["format_tokens"] = format_token_context(paragraph)

        # 调用 LLM 翻译
        prepared = build_translation_input(paragraph)
        prompt_text = prepared.tokenized_text or prepared.text
        translation = self.llm.translate(prompt_text, llm_context)

        return build_translation_payload(
            paragraph,
            translation.strip(),
            token_repairer=self._repair_format_tokens,
        )

    def _build_translation_context(self, context: LayeredContext) -> Dict[str, Any]:
        """构建 LLM 翻译上下文"""
        llm_context = {}

        article_analysis = self.context_manager.article_analysis

        # 术语表
        if context.terminology:
            llm_context["glossary"] = build_glossary_entries_from_terms(context.terminology)

        # 术语使用记录（用于 FIRST_ANNOTATE 动态调整）
        if context.term_usage:
            llm_context["term_usage"] = context.term_usage

        # 风格指南
        if context.guidelines:
            llm_context["style_guide"] = {
                "notes": build_translation_guidelines(context.guidelines)
            }

        # 章节理解
        if context.section_understanding:
            llm_context["section_context"] = build_section_context_payload(
                context.section_understanding
            )

        # 全文背景
        if context.article_theme:
            llm_context["article_theme"] = context.article_theme
        if context.article_structure:
            llm_context["article_structure"] = context.article_structure
        if article_analysis:
            if article_analysis.style.target_audience:
                llm_context["target_audience"] = article_analysis.style.target_audience
            if article_analysis.style.translation_voice:
                llm_context["translation_voice"] = (
                    article_analysis.style.translation_voice
                )
            if article_analysis.challenges:
                llm_context["article_challenges"] = build_article_challenge_payload(
                    article_analysis.challenges
                )

        # 前文上下文
        if context.previous_paragraphs:
            llm_context["previous_paragraphs"] = context.previous_paragraphs

        # 后文预览
        if context.next_preview:
            llm_context["next_preview"] = context.next_preview

        return llm_context

    # ============ Step 3: 反思 ============

    def _build_review_context(
        self,
        section: Section,
        understanding: SectionUnderstanding,
    ) -> Dict[str, Any]:
        """Build critique-time context so reflection focuses on article-level quality."""
        article_theme = ""
        structure_summary = ""
        guidelines: List[str] = []
        terminology: List[Dict[str, str]] = []
        translation_voice = ""
        target_audience = ""
        article_challenges: List[Dict[str, str]] = []

        if self.context_manager.article_analysis:
            article_theme = self.context_manager.article_analysis.theme
            structure_summary = self.context_manager.article_analysis.structure_summary
            guidelines = build_translation_guidelines(
                self.context_manager.article_analysis.guidelines
            )
            target_audience = (
                self.context_manager.article_analysis.style.target_audience
            )
            translation_voice = (
                self.context_manager.article_analysis.style.translation_voice
            )
            article_challenges = build_article_challenge_payload(
                self.context_manager.article_analysis.challenges
            )
            terminology = build_review_term_entries(
                self.context_manager.article_analysis.terminology
            )

        review_priorities = build_review_priorities([
            "先检查是否误译、漏译或削弱原文判断。",
            "再检查术语是否前后一致，首现是否适合中文加英文括注。",
            "再检查是否对真正有理解门槛的术语漏注，或对常见术语过度加注。",
            "再检查中文是否有翻译腔、英文句法投影或机械名词串。",
            "标题、图注和数据密集段优先保证信息密度与判断力度。",
        ])

        section_payload = build_section_context_payload(understanding)

        return {
            "article_theme": article_theme,
            "structure_summary": structure_summary,
            "target_audience": target_audience,
            "section_title": section.title,
            "section_role": section_payload.get("role", ""),
            "relation_to_previous": section_payload.get("relation_to_previous", ""),
            "relation_to_next": understanding.relation_to_next,
            "translation_notes": section_payload.get("translation_notes", []),
            "article_challenges": article_challenges,
            "review_priorities": review_priorities,
            "guidelines": guidelines,
            "terminology": terminology,
            "translation_voice": translation_voice,
        }

    def _build_refine_context(
        self,
        section: Section,
        understanding: SectionUnderstanding,
    ) -> Dict[str, Any]:
        """Build section-level guardrails for targeted revision."""
        return self._build_review_context(section, understanding)

    def _step_reflect(
        self,
        section: Section,
        translations: List[str],
        understanding: SectionUnderstanding,
    ) -> ReflectionResult:
        """Step 3: 批量反思"""
        # 获取原文列表
        source_paragraphs = [p.source for p in section.paragraphs]

        # 获取翻译指南和术语表
        guidelines = []
        terminology = []
        if self.context_manager.article_analysis:
            guidelines = build_translation_guidelines(
                self.context_manager.article_analysis.guidelines
            )
            terminology = build_review_term_entries(
                self.context_manager.article_analysis.terminology
            )

        # 调用 LLM 反思
        result = self.llm.reflect_on_translation(
            source_paragraphs=source_paragraphs,
            translations=translations,
            guidelines=guidelines,
            terminology=terminology,
            context=self._build_review_context(section, understanding),
        )

        # 解析问题列表
        issues = []
        for issue_data in result.get("issues", []):
            issues.append(TranslationIssue(
                paragraph_index=issue_data.get("paragraph_index", 0),
                issue_type=issue_data.get("issue_type", "readability"),
                severity=issue_data.get("severity", "medium"),
                original_text=issue_data.get("original_text", ""),
                description=issue_data.get("description", ""),
                why_it_matters=issue_data.get("why_it_matters", ""),
                suggestion=issue_data.get("suggestion", "")
            ))

        return ReflectionResult(
            overall_score=float(result.get("overall_score", 0)),
            readability_score=float(result.get("readability_score", 0)),
            accuracy_score=float(result.get("accuracy_score", 0)),
            conciseness_score=float(result.get("conciseness_score", 0)),
            is_excellent=result.get("is_excellent", False),
            issues=issues
        )

    # ============ Step 4: 润色 ============

    def _step_refine(
        self,
        section: Section,
        translations: List[TranslationPayload],
        reflection: ReflectionResult,
        understanding: SectionUnderstanding,
    ) -> List[TranslationPayload]:
        """Step 4: 针对性润色 — 按段落合并问题，每个有问题的段落只调用一次"""
        refined = [
            TranslationPayload(
                text=item.text,
                tokenized_text=item.tokenized_text,
                format_issues=list(item.format_issues),
            )
            for item in translations
        ]

        # 按段落索引分组 issues
        issues_by_paragraph: Dict[int, List[TranslationIssue]] = defaultdict(list)
        for issue in reflection.issues:
            issues_by_paragraph[issue.paragraph_index].append(issue)

        # 每个有问题的段落只调用一次
        for idx, issues in issues_by_paragraph.items():
            if not (0 <= idx < len(refined)):
                continue

            paragraph = section.paragraphs[idx]
            dehydrated_payload = build_dehydrated_link_payload(paragraph)
            if dehydrated_payload is not None:
                refined[idx] = dehydrated_payload
                continue

            current_payload = refined[idx]
            refine_context = self._build_refine_context(section, understanding)
            source = paragraph.source
            current_translation = current_payload.text

            if paragraph.inline_elements:
                prepared = build_translation_input(paragraph)
                source = prepared.tokenized_text or prepared.text
                current_translation = (
                    current_payload.tokenized_text or current_payload.text
                )
                refine_context = {
                    **refine_context,
                    "format_tokens": format_token_context(paragraph),
                }

            # 合并同一段落的多个问题为一个描述
            if len(issues) == 1:
                issue = issues[0]
                issue_type = issue.issue_type
                description = issue.description
                suggestion = issue.suggestion
            else:
                issue_type = "multiple"
                description = "\n".join(
                    f"- [{issue.issue_type}] {issue.description}（建议：{issue.suggestion}）"
                    for issue in issues
                )
                suggestion = "请综合以上问题一并修订"

            # 调用 LLM 润色
            refined_text = self.llm.refine_translation(
                source=source,
                current_translation=current_translation,
                issue_type=issue_type,
                description=description,
                suggestion=suggestion,
                context=refine_context,
            )

            stripped = refined_text.strip()

            if paragraph.inline_elements:
                candidate = build_translation_payload(
                    paragraph,
                    stripped,
                    token_repairer=self._repair_format_tokens,
                )
                if candidate.format_valid:
                    refined[idx] = candidate
                continue

            refined[idx] = TranslationPayload(text=stripped)

        return refined

    # ============ Step 5: 风格润色（可选） ============

    def _step_style_polish(
        self,
        section: Section,
        translations: List[TranslationPayload],
    ) -> List[TranslationPayload]:
        """Step 5: 风格润色 — 逐段调用 style_polish，压缩冗长表达、统一隐喻、提升语气力度"""
        polished = [
            TranslationPayload(
                text=item.text,
                tokenized_text=item.tokenized_text,
                format_issues=list(item.format_issues),
            )
            for item in translations
        ]

        for idx, (para, payload) in enumerate(zip(section.paragraphs, polished)):
            # 跳过脱水链接段落
            dehydrated_payload = build_dehydrated_link_payload(para)
            if dehydrated_payload is not None:
                polished[idx] = dehydrated_payload
                continue

            source = para.source
            current_translation = payload.text

            # 如果有 format tokens，用 tokenized 版本
            if para.inline_elements:
                prepared = build_translation_input(para)
                source = prepared.tokenized_text or prepared.text
                current_translation = payload.tokenized_text or payload.text

            polished_text = self.llm.style_polish(
                source=source,
                current_translation=current_translation,
            )

            stripped = polished_text.strip()

            if para.inline_elements:
                candidate = build_translation_payload(
                    para,
                    stripped,
                    token_repairer=self._repair_format_tokens,
                )
                if candidate.format_valid:
                    polished[idx] = candidate
                continue

            polished[idx] = TranslationPayload(text=stripped)

        return polished

    # ============ Helper Methods ============

    def _split_into_batches(self, paragraphs: List[Paragraph]) -> List[List[Paragraph]]:
        """将段落列表分批"""
        batches = []
        for i in range(0, len(paragraphs), self.paragraph_threshold):
            batches.append(paragraphs[i:i + self.paragraph_threshold])
        return batches

    def _apply_term_tracker_corrections(
        self, terms: List[EnhancedTerm]
    ) -> List[EnhancedTerm]:
        """根据 term_tracker 已有的使用记录修正术语翻译，与单段翻译路径对齐。"""
        tracker = self.context_manager.term_tracker
        corrected: List[EnhancedTerm] = []
        for term in terms:
            if term.term.lower() in tracker.used_translations:
                preferred = tracker.get_preferred_translation(term.term)
                if preferred:
                    term = term.model_copy(update={"translation": preferred})
            corrected.append(term)
        return corrected

    def _extract_terms_used(self, source: str, translation: str) -> Dict[str, str]:
        """
        从翻译结果中提取使用的术语

        简单实现：检查术语表中的术语是否出现在原文中，
        如果出现，记录其在译文中的翻译
        """
        terms_used = {}

        if not self.context_manager.article_analysis:
            return terms_used

        for term in self.context_manager.article_analysis.terminology:
            if _count_term_occurrences(source, term.term) > 0:
                # 术语出现在原文中，记录翻译
                if term.translation:
                    terms_used[term.term] = term.translation

        return terms_used

    def _repair_format_tokens(
        self,
        paragraph: Paragraph,
        translated_tokenized_text: str,
        issues: List[str],
    ) -> Optional[str]:
        if not paragraph.inline_elements:
            return None

        prepared = build_translation_input(paragraph)
        return self.llm.repair_format_tokens(
            source_text=prepared.tokenized_text or prepared.text,
            translated_text=translated_tokenized_text,
            format_tokens=format_token_context(paragraph),
            issues=issues,
            model="flash",
        )


def create_four_step_translator(
    llm_provider: LLMProvider,
    context_manager: LayeredContextManager,
    quality_gate: Optional[QualityGate] = None,
    paragraph_threshold: int = 8,
    max_retries: int = 1,
    memory_service=None
) -> FourStepTranslator:
    """
    创建四步法翻译器

    Args:
        llm_provider: LLM Provider
        context_manager: 分层上下文管理器
        quality_gate: 质量门禁
        paragraph_threshold: 混合模式阈值
        max_retries: 最大重试次数
        memory_service: 翻译记忆服务（可选）

    Returns:
        FourStepTranslator: 翻译器实例
    """
    return FourStepTranslator(
        llm_provider=llm_provider,
        context_manager=context_manager,
        quality_gate=quality_gate,
        paragraph_threshold=paragraph_threshold,
        max_retries=max_retries,
        memory_service=memory_service
    )
