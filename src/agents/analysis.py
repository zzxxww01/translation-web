"""
Translation Agent - Analysis Agent

Analyzes articles to extract terms and style guide.
"""

from typing import List, Optional

from ..core.models import (
    Glossary, GlossaryTerm, TranslationStrategy,
    StyleGuide, AnalysisResult, Section
)
from ..llm.base import LLMProvider


class AnalysisAgent:
    """分析 Agent - 全文分析，提取术语和风格"""

    def __init__(self, llm_provider: LLMProvider):
        """
        初始化分析 Agent

        Args:
            llm_provider: LLM Provider
        """
        self.llm = llm_provider

    def analyze(
        self,
        sections: List[Section],
        existing_glossary: Optional[Glossary] = None
    ) -> AnalysisResult:
        """
        分析文章

        Args:
            sections: 章节列表
            existing_glossary: 现有术语表（用于合并）

        Returns:
            AnalysisResult: 分析结果
        """
        # 提取全文文本（用于分析）
        full_text = self._extract_text(sections)

        # 统计信息
        word_count = len(full_text.split())
        paragraph_count = sum(len(s.paragraphs) for s in sections)

        # 调用 LLM 分析
        try:
            analysis_data = self.llm.analyze(full_text)
        except Exception as e:
            # 如果分析失败，返回基本结果
            return AnalysisResult(
                title=sections[0].title if sections else "Untitled",
                section_count=len(sections),
                paragraph_count=paragraph_count,
                word_count=word_count
            )

        # 解析术语
        detected_terms = []
        for term_data in analysis_data.get("terms", []):
            try:
                strategy = TranslationStrategy(term_data.get("strategy", "translate"))
            except ValueError:
                strategy = TranslationStrategy.TRANSLATE

            term = GlossaryTerm(
                original=term_data.get("original", ""),
                translation=term_data.get("translation"),
                strategy=strategy,
                note=term_data.get("note")
            )
            detected_terms.append(term)

        # 解析风格
        style_data = analysis_data.get("style", {})
        style_guide = StyleGuide(
            tone=style_data.get("tone", "professional"),
            formality=style_data.get("formality", "formal"),
            notes=style_data.get("notes", [])
        )

        # 构建结果
        result = AnalysisResult(
            title=sections[0].title if sections else "Untitled",
            summary=analysis_data.get("summary"),
            detected_terms=detected_terms,
            style_guide=style_guide,
            section_count=len(sections),
            paragraph_count=paragraph_count,
            word_count=word_count
        )

        return result

    def merge_glossary(
        self,
        existing: Glossary,
        detected_terms: List[GlossaryTerm]
    ) -> Glossary:
        """
        合并现有术语表和检测到的术语

        Args:
            existing: 现有术语表
            detected_terms: 检测到的术语

        Returns:
            Glossary: 合并后的术语表
        """
        merged = Glossary(version=existing.version + 1)

        # 先添加现有术语
        for term in existing.terms:
            merged.add_term(term)

        # 添加新检测到的术语（不覆盖现有的）
        for term in detected_terms:
            if not merged.get_term(term.original):
                merged.add_term(term)

        return merged

    def _extract_text(self, sections: List[Section], max_length: int = 10000) -> str:
        """
        提取全文文本（用于分析）

        Args:
            sections: 章节列表
            max_length: 最大长度

        Returns:
            str: 文本内容
        """
        lines = []
        current_length = 0

        for section in sections:
            # 添加章节标题
            lines.append(f"## {section.title}")
            current_length += len(section.title)

            for p in section.paragraphs:
                if current_length + len(p.source) > max_length:
                    break
                lines.append(p.source)
                current_length += len(p.source)

            if current_length >= max_length:
                break

        return "\n\n".join(lines)


def create_analysis_agent(llm_provider: LLMProvider) -> AnalysisAgent:
    """
    创建分析 Agent

    Args:
        llm_provider: LLM Provider

    Returns:
        AnalysisAgent: 分析 Agent
    """
    return AnalysisAgent(llm_provider=llm_provider)
