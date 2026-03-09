"""
Translation Agent - Translation Agent

Handles paragraph translation with context management.
"""

from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from ..core.models import (
    Paragraph,
    Section,
    ParagraphStatus,
    Glossary,
    GlossaryTerm,
    StyleGuide,
    TranslationRule,
)
from ..llm.base import LLMProvider
from ..core.inline_handler import InlineElementExtractor, PlaceholderHandler


@dataclass
class TranslationContext:
    """翻译上下文"""

    glossary: Optional[Glossary] = None
    style_guide: Optional[StyleGuide] = None
    previous_paragraphs: List[Tuple[str, str]] = None  # [(source, translation), ...]
    next_preview: List[str] = None  # [source, ...]
    source_text: Optional[str] = None  # 当前段落原文（用于术语筛选）

    # 【新增】分层上下文字段
    article_title: Optional[str] = None  # 全文级：文章标题
    current_section_title: Optional[str] = None  # 章节级：当前章节标题
    heading_chain: Optional[List[str]] = (
        None  # 父级：标题链 ["# 主标题", "## 二级标题"]
    )

    # 【新增】自学习翻译规则
    learned_rules: Optional[List[TranslationRule]] = None

    def __post_init__(self):
        if self.previous_paragraphs is None:
            self.previous_paragraphs = []
        if self.next_preview is None:
            self.next_preview = []
        if self.heading_chain is None:
            self.heading_chain = []
        if self.learned_rules is None:
            self.learned_rules = []


class ContextWindow:
    """滑动窗口上下文管理"""

    def __init__(self, window_size: int = 5):
        """
        初始化上下文窗口

        Args:
            window_size: 窗口大小（保留最近 N 段）
        """
        self.window_size = window_size
        self.confirmed: List[Tuple[str, str]] = []  # [(source, translation), ...]

    def add_confirmed(self, source: str, translation: str) -> None:
        """
        添加已确认的段落

        Args:
            source: 原文
            translation: 译文
        """
        self.confirmed.append((source, translation))

    def get_context(self) -> List[Tuple[str, str]]:
        """
        获取最近 N 段作为上下文

        Returns:
            List[Tuple[str, str]]: 最近的段落列表
        """
        return self.confirmed[-self.window_size :]

    def clear(self) -> None:
        """清空上下文"""
        self.confirmed.clear()


class TranslationAgent:
    """翻译 Agent"""

    def __init__(self, llm_provider: LLMProvider, context_window_size: int = 5):
        """
        初始化翻译 Agent

        Args:
            llm_provider: LLM Provider
            context_window_size: 上下文窗口大小
        """
        self.llm = llm_provider
        self.context_window = ContextWindow(window_size=context_window_size)

        # 内联元素处理
        self.inline_extractor = InlineElementExtractor()
        self.placeholder_handler = PlaceholderHandler()

    def translate_paragraph(
        self,
        paragraph: Paragraph,
        context: TranslationContext,
        model_name: str = "pro",
    ) -> str:
        """
        翻译单个段落（增强版：支持内联元素保留）

        Args:
            paragraph: 段落
            context: 翻译上下文
            model_name: 模型名称（用于记录）

        Returns:
            str: 翻译结果
        """
        # Step 1: 提取内联元素
        plain_text, elements = self.inline_extractor.extract_from_markdown(
            paragraph.source
        )

        # Step 2: 插入占位符
        if elements:
            text_with_placeholders, updated_elements = (
                self.placeholder_handler.insert_placeholders(plain_text, elements)
            )
        else:
            text_with_placeholders = plain_text
            updated_elements = []

        # Step 3: 设置源文本用于术语筛选
        context.source_text = text_with_placeholders

        # Step 4: 构建 LLM 上下文
        llm_context = self._build_llm_context(context)

        # 如果有内联元素，添加占位符说明
        if elements:
            # 在Prompt中添加占位符处理指令
            llm_context["inline_instruction"] = (
                "注意：文本中的{{TYPE_N|...}}是占位符，用于保留格式元素。"
                "请保留占位符格式，但要翻译占位符中的文本内容。"
                "例如：{{LINK_1|open-source}} 应翻译为 {{LINK_1|开源}}"
            )

        # Step 5: 调用 LLM 翻译
        llm_context["model"] = model_name
        translation = self.llm.translate(text_with_placeholders, llm_context)

        # Step 6: 还原内联元素
        if elements:
            final_translation = self.placeholder_handler.restore_elements(
                translation, updated_elements
            )
        else:
            final_translation = translation

        # Step 7: 记录翻译结果
        paragraph.add_translation(final_translation, model_name)

        return final_translation

    def translate_section(
        self,
        section: Section,
        context: TranslationContext,
        model_name: str = "pro",
        on_progress: Optional[Callable[[int, int, Paragraph], None]] = None,
    ) -> Section:
        """
        翻译整个章节

        Args:
            section: 章节
            context: 翻译上下文
            model_name: 模型名称
            on_progress: 进度回调 (current, total, paragraph)

        Returns:
            Section: 翻译后的章节
        """
        total = len(section.paragraphs)

        for i, paragraph in enumerate(section.paragraphs):
            # 跳过已确认的段落
            if paragraph.status == ParagraphStatus.APPROVED:
                # 添加到上下文窗口
                if paragraph.confirmed:
                    self.context_window.add_confirmed(
                        paragraph.source, paragraph.confirmed
                    )
                continue

            # 更新上下文中的前文
            context.previous_paragraphs = self.context_window.get_context()

            # 更新后文预览
            context.next_preview = [p.source for p in section.paragraphs[i + 1 : i + 3]]

            # 翻译
            translation = self.translate_paragraph(paragraph, context, model_name)

            # 添加到上下文窗口
            self.context_window.add_confirmed(paragraph.source, translation)

            # 回调
            if on_progress:
                on_progress(i + 1, total, paragraph)

        return section

    def retranslate_paragraph(
        self,
        paragraph: Paragraph,
        context: TranslationContext,
        instruction: Optional[str] = None,
        model_name: str = "pro",
    ) -> str:
        """
        重新翻译段落（可附加指令）

        Args:
            paragraph: 段落
            context: 翻译上下文
            instruction: 额外指令（如"更简洁"、"更口语化"）
            model_name: 模型名称

        Returns:
            str: 翻译结果
        """
        # 设置源文本用于术语筛选
        context.source_text = paragraph.source

        # 构建 LLM 上下文
        llm_context = self._build_llm_context(context)

        # 添加额外指令
        if instruction:
            llm_context["instruction"] = instruction

        # 如果有之前的翻译，也传入作为参考
        prev_trans = paragraph.latest_translation(non_empty=True)
        if prev_trans is not None:
            llm_context["previous_translation"] = prev_trans.text

        # 调用 LLM 翻译
        llm_context["model"] = model_name
        translation = self.llm.translate(paragraph.source, llm_context)

        # 记录翻译结果
        paragraph.add_translation(translation, model_name)

        return translation

    def _build_llm_context(self, context: TranslationContext) -> Dict[str, Any]:
        """
        构建 LLM 上下文（增强版：支持分层上下文）

        Args:
            context: 翻译上下文

        Returns:
            Dict: LLM 上下文
        """
        llm_context = {}

        # 术语表 - 智能筛选相关术语
        if context.glossary and context.glossary.terms:
            active_terms = [
                term
                for term in context.glossary.terms
                if getattr(term, "status", "active") == "active"
            ]
            # 如果有源文本，筛选相关术语
            if context.source_text:
                from ..core.term_matcher import TermMatcher

                matcher = TermMatcher(
                    Glossary(version=context.glossary.version, terms=active_terms)
                )
                relevant_terms = matcher.get_term_context(
                    context.source_text, max_terms=20
                )
                llm_context["glossary"] = relevant_terms
                llm_context["glossary_size"] = len(relevant_terms)
                llm_context["total_glossary_terms"] = len(active_terms)
            else:
                # 没有源文本时，使用所有术语（限制数量）
                llm_context["glossary"] = [
                    {
                        "original": term.original,
                        "translation": term.translation,
                        "strategy": term.strategy.value,
                        "note": term.note,
                    }
                    for term in active_terms[:30]
                ]

        # 风格指南
        if context.style_guide:
            llm_context["style_guide"] = {
                "tone": context.style_guide.tone,
                "formality": context.style_guide.formality,
                "notes": context.style_guide.notes,
            }

        # 前文上下文
        if context.previous_paragraphs:
            llm_context["previous_paragraphs"] = context.previous_paragraphs

        # 后文预览
        if context.next_preview:
            llm_context["next_preview"] = context.next_preview

        # 【新增】分层上下文支持
        # 1. 全文级上下文：文章标题
        if hasattr(context, "article_title") and context.article_title:
            llm_context["article_title"] = context.article_title

        # 2. 章节级上下文：当前章节标题
        if hasattr(context, "current_section_title") and context.current_section_title:
            llm_context["current_section_title"] = context.current_section_title

        # 3. 父级上下文：标题链
        if hasattr(context, "heading_chain") and context.heading_chain:
            llm_context["heading_chain"] = context.heading_chain

        # 4. 自学习翻译规则
        if hasattr(context, "learned_rules") and context.learned_rules:
            llm_context["learned_rules"] = context.learned_rules

        return llm_context

    def reset_context(self) -> None:
        """重置上下文窗口"""
        self.context_window.clear()

    def load_confirmed_context(self, paragraphs: List[Paragraph]) -> None:
        """
        从已确认的段落加载上下文

        Args:
            paragraphs: 段落列表
        """
        self.context_window.clear()
        for p in paragraphs:
            if p.status == ParagraphStatus.APPROVED and p.confirmed:
                self.context_window.add_confirmed(p.source, p.confirmed)


def create_translation_agent(
    llm_provider: LLMProvider, context_window_size: int = 5
) -> TranslationAgent:
    """
    创建翻译 Agent

    Args:
        llm_provider: LLM Provider
        context_window_size: 上下文窗口大小

    Returns:
        TranslationAgent: 翻译 Agent
    """
    return TranslationAgent(
        llm_provider=llm_provider, context_window_size=context_window_size
    )
