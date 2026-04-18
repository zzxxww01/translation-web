"""
Translation Agent - Deep Analyzer

全文深度分析器（Phase 0）

分析内容：
1. 主题与论点
2. 关键术语表（含上下文含义）
3. 风格分析
4. 翻译难点预警
5. 翻译风格指南

方案 C 优化：
- 使用智能采样覆盖所有章节
- 增强章节角色分析采样（首段+中段+末段）
"""

from typing import List, Optional, Dict
import logging

from ..core.models import (
    Section,
    ArticleAnalysis, EnhancedTerm, ArticleStyle,
    TranslationChallenge, TranslationStrategy,
    SectionUnderstanding
)
from ..llm.base import LLMProvider
from .smart_sampler import SmartSampler, create_smart_sampler


logger = logging.getLogger(__name__)


class DeepAnalyzer:
    """全文深度分析器"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_sample_chars: int = 18000
    ):
        """
        初始化深度分析器

        Args:
            llm_provider: LLM Provider
            max_sample_chars: 最大采样字符数
        """
        self.llm = llm_provider
        self.max_sample_chars = max_sample_chars
        self.smart_sampler = create_smart_sampler(max_total_chars=max_sample_chars)

    ANALYSIS_SAMPLE_STEPS = (18000, 12000, 8000, 5000)
    ANALYSIS_TIMEOUT_STEPS = (None, 240, 360, 480)

    def analyze(self, sections: List[Section]) -> ArticleAnalysis:
        """
        执行全文深度分析

        Args:
            sections: 章节列表

        Returns:
            ArticleAnalysis: 深度分析结果
        """
        # 构建章节大纲
        sections_outline = self._build_sections_outline(sections)

        result = None
        last_error: Exception | None = None
        sample_steps = [self.max_sample_chars, *self.ANALYSIS_SAMPLE_STEPS]
        deduped_steps = []
        for sample_chars in sample_steps:
            if sample_chars not in deduped_steps:
                deduped_steps.append(sample_chars)

        for attempt_index, sample_chars in enumerate(deduped_steps):
            timeout = self.ANALYSIS_TIMEOUT_STEPS[min(attempt_index, len(self.ANALYSIS_TIMEOUT_STEPS) - 1)]
            try:
                full_text = self._extract_full_text(sections, max_length=sample_chars)
                logger.info(
                    "Deep analysis attempt %s with sample_chars=%s timeout=%s",
                    attempt_index + 1,
                    sample_chars,
                    timeout or "default",
                )
                result = self.llm.deep_analyze(full_text, sections_outline, timeout=timeout)
                break
            except Exception as exc:
                last_error = exc
                if attempt_index == len(deduped_steps) - 1 or not self._should_retry_with_smaller_sample(exc):
                    raise
                logger.warning(
                    "Deep analysis attempt %s failed with sample_chars=%s: %s; retrying with a smaller sample",
                    attempt_index + 1,
                    sample_chars,
                    exc,
                )

        if result is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("Deep analysis returned no result")

        # 解析基础分析结果
        analysis = self._parse_analysis_result(result, sections)

        # 优化：一次性分析所有章节角色（减少 LLM 调用）
        section_roles = self._analyze_all_section_roles(sections, analysis)
        analysis.section_roles = section_roles

        return analysis

    def _extract_full_text(
        self,
        sections: List[Section],
        max_length: int = 18000
    ) -> str:
        """
        提取全文文本（方案 C 优化：使用智能采样）

        采样策略：
        - 每章首段 + 中段 + 末段
        - 术语密集段落
        - 总计不超过 max_length 字符，但覆盖所有章节

        Args:
            sections: 章节列表
            max_length: 最大长度

        Returns:
            str: 采样后的全文文本
        """
        # 使用智能采样器
        sampler = self.smart_sampler
        if max_length != self.max_sample_chars:
            sampler = create_smart_sampler(max_total_chars=max_length)
        sampling_result = sampler.sample_for_deep_analysis(
            sections,
            include_term_dense=True
        )

        # 构建采样文本
        return sampler.build_sampled_text(
            sampling_result,
            include_section_headers=True
        )

    def _should_retry_with_smaller_sample(self, exc: Exception) -> bool:
        text = str(exc).lower()
        retry_signals = [
            "timed out",
            "timeout",
            "deadline exceeded",
            "connection",
            "temporarily unavailable",
            "service unavailable",
            "bad gateway",
            "502",
            "503",
            "504",
            "incomplete",
        ]
        return any(signal in text for signal in retry_signals)

    def _build_sections_outline(self, sections: List[Section]) -> str:
        """
        构建章节大纲

        Args:
            sections: 章节列表

        Returns:
            str: 章节大纲
        """
        lines = []
        for i, section in enumerate(sections):
            para_count = len(section.paragraphs)
            lines.append(f"{i+1}. {section.title} ({para_count} 段)")
        return "\n".join(lines)

    def _parse_analysis_result(
        self,
        result: dict,
        sections: List[Section]
    ) -> ArticleAnalysis:
        """
        解析分析结果

        Args:
            result: LLM 返回的分析结果
            sections: 章节列表

        Returns:
            ArticleAnalysis: 解析后的分析结果
        """
        # 解析术语表
        terminology = []
        for term_data in result.get("terminology", []):
            strategy_str = term_data.get("strategy", "translate")
            try:
                strategy = TranslationStrategy(strategy_str)
            except ValueError:
                strategy = TranslationStrategy.TRANSLATE

            term = EnhancedTerm(
                term=term_data.get("term", ""),
                context_meaning=term_data.get("context_meaning", ""),
                translation=term_data.get("translation"),
                strategy=strategy,
                first_occurrence_note=term_data.get("first_occurrence_note", False),
                rationale=term_data.get("rationale")
            )
            terminology.append(term)

        # 解析风格
        style_data = result.get("style", {})
        style = ArticleStyle(
            tone=style_data.get("tone", "professional"),
            target_audience=style_data.get("target_audience", ""),
            translation_voice=style_data.get("translation_voice", "")
        )

        # 解析翻译难点
        challenges = []
        for challenge_data in result.get("challenges", []):
            challenge = TranslationChallenge(
                location=challenge_data.get("location", ""),
                issue=challenge_data.get("issue", ""),
                suggestion=challenge_data.get("suggestion")
            )
            challenges.append(challenge)

        # 统计信息
        total_paragraphs = sum(len(s.paragraphs) for s in sections)
        total_words = sum(
            len(p.source.split())
            for s in sections
            for p in s.paragraphs
        )

        return ArticleAnalysis(
            theme=result.get("theme", ""),
            key_arguments=result.get("key_arguments", []),
            structure_summary=result.get("structure_summary", ""),
            terminology=terminology,
            style=style,
            challenges=challenges,
            guidelines=result.get("guidelines", []),
            section_count=len(sections),
            paragraph_count=total_paragraphs,
            word_count=total_words
        )

    def _analyze_all_section_roles(
        self,
        sections: List[Section],
        analysis: ArticleAnalysis
    ) -> Dict[str, SectionUnderstanding]:
        """
        一次性分析所有章节的角色（优化：减少 LLM 调用次数）

        Args:
            sections: 章节列表
            analysis: 已有的文章分析结果

        Returns:
            Dict[str, SectionUnderstanding]: section_id -> 角色理解
        """
        # 构建章节摘要（用于一次性分析）
        sections_summary = self._build_sections_summary(sections)

        # 构建章节角色分析的 prompt
        prompt = self._build_section_roles_prompt(
            article_theme=analysis.theme,
            structure_summary=analysis.structure_summary,
            sections_summary=sections_summary
        )

        # 调用 LLM 一次性分析所有章节
        response = self.llm.generate(prompt, response_format="json")
        result = self.llm._parse_json_response(response)

        # 解析结果
        section_roles = {}
        section_roles_data = result.get("section_roles", {})

        for section in sections:
            section_id = section.section_id
            if section_id in section_roles_data:
                role_data = section_roles_data[section_id]
                section_roles[section_id] = SectionUnderstanding(
                    role_in_article=role_data.get("role_in_article", ""),
                    relation_to_previous=role_data.get("relation_to_previous", ""),
                    relation_to_next=role_data.get("relation_to_next", ""),
                    key_points=role_data.get("key_points", []),
                    translation_notes=role_data.get("translation_notes", [])
                )
            else:
                # 如果 LLM 没有返回该章节的分析，创建一个默认的
                section_roles[section_id] = SectionUnderstanding(
                    role_in_article="待分析",
                    relation_to_previous="",
                    relation_to_next="",
                    key_points=[],
                    translation_notes=[]
                )

        return section_roles

    def _build_sections_summary(self, sections: List[Section]) -> str:
        """
        构建章节摘要（方案 C 优化：增强采样）

        每章节采样: 首段 + 中段 + 末段

        Args:
            sections: 章节列表

        Returns:
            str: 章节摘要
        """
        # 使用智能采样器获取增强摘要
        section_summaries = self.smart_sampler.sample_for_section_roles(sections)

        lines = []
        for section in sections:
            lines.append(f"## {section.section_id} - {section.title}")
            summary = section_summaries.get(section.section_id, "")
            lines.append(summary)
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def _build_section_roles_prompt(
        self,
        article_theme: str,
        structure_summary: str,
        sections_summary: str
    ) -> str:
        """
        构建章节角色分析 prompt

        Args:
            article_theme: 文章主题
            structure_summary: 结构摘要
            sections_summary: 章节摘要

        Returns:
            str: 完整的 prompt
        """
        return self.llm.prompt_manager.get(
            "longform/analysis/section_role_map",
            article_theme=article_theme,
            structure_summary=structure_summary,
            sections_summary=sections_summary[:6000]  # 限制长度，降低长响应失败风险
        )

    def get_analysis_summary(self, analysis: ArticleAnalysis) -> str:
        """
        生成分析摘要报告

        Args:
            analysis: 分析结果

        Returns:
            str: 格式化的摘要报告
        """
        lines = [
            "=" * 60,
            "全文深度分析报告",
            "=" * 60,
            "",
            f"## 主题",
            f"{analysis.theme}",
            "",
            f"## 主要论点",
        ]

        for i, arg in enumerate(analysis.key_arguments, 1):
            lines.append(f"  {i}. {arg}")

        lines.extend([
            "",
            f"## 结构概述",
            f"{analysis.structure_summary}",
            "",
            f"## 风格分析",
            f"  - 语气: {analysis.style.tone}",
            f"  - 目标读者: {analysis.style.target_audience}",
            f"  - 翻译语气: {analysis.style.translation_voice}",
            "",
            f"## 关键术语 ({len(analysis.terminology)} 个)",
        ])

        for term in analysis.terminology[:10]:  # 只显示前10个
            strategy_text = {
                TranslationStrategy.PRESERVE: "保持原文",
                TranslationStrategy.FIRST_ANNOTATE: "首次标注",
                TranslationStrategy.TRANSLATE: "直接翻译"
            }.get(term.strategy, "翻译")

            trans = term.translation or "(保持原文)"
            lines.append(f"  - {term.term} → {trans} [{strategy_text}]")

        if len(analysis.terminology) > 10:
            lines.append(f"  ... 还有 {len(analysis.terminology) - 10} 个术语")

        if analysis.challenges:
            lines.extend([
                "",
                f"## 翻译难点 ({len(analysis.challenges)} 处)",
            ])
            for challenge in analysis.challenges[:5]:
                lines.append(f"  - [{challenge.location}] {challenge.issue}")

        lines.extend([
            "",
            f"## 翻译指南",
        ])
        for i, guideline in enumerate(analysis.guidelines, 1):
            lines.append(f"  {i}. {guideline}")

        lines.extend([
            "",
            "-" * 60,
            f"统计: {analysis.section_count} 章节, {analysis.paragraph_count} 段落, ~{analysis.word_count} 词",
            "=" * 60,
        ])

        return "\n".join(lines)


def create_deep_analyzer(llm_provider: LLMProvider) -> DeepAnalyzer:
    """
    创建深度分析器

    Args:
        llm_provider: LLM Provider

    Returns:
        DeepAnalyzer: 深度分析器实例
    """
    return DeepAnalyzer(llm_provider=llm_provider)
