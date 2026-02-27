"""
Heading and Metadata Translation Service - 标题和元信息翻译服务
"""

from typing import Optional, Dict, Any, List
from ..core.models import Paragraph
from ..core.metadata_parser import MetadataParser, HeadingParser
from ..llm.base import LLMProvider


class HeadingTranslationService:
    """标题翻译服务"""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.heading_parser = HeadingParser()

        # 加载标题翻译Prompt模板
        import os

        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )
        template_file = os.path.join(prompts_dir, "heading_translation.txt")

        with open(template_file, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def translate_heading(
        self,
        heading_text: str,
        heading_level: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        翻译标题

        Args:
            heading_text: 标题原文
            heading_level: 标题层级 (1-6)
            context: 上下文信息（可选）

        Returns:
            翻译后的标题
        """
        # 构建上下文部分
        context_section = ""
        if context:
            if context.get("article_title"):
                context_section += f"文章标题：{context['article_title']}\n"
            if context.get("parent_headings"):
                context_section += "父级标题：\n"
                for h in context["parent_headings"]:
                    context_section += f"  {h}\n"

        # 构建完整Prompt
        prompt = self.prompt_template.format(
            context_section=context_section if context_section else "（无上下文）",
            title=heading_text,
        )

        # 调用LLM
        translation = self.llm.generate(prompt, temperature=0.3)

        # 清理结果
        translation = translation.strip().strip('"').strip("'")

        return translation

    def process_heading_paragraph(
        self, paragraph: Paragraph, previous_headings: List[tuple] = None
    ) -> Paragraph:
        """
        处理标题段落

        Args:
            paragraph: 段落对象
            previous_headings: 之前的标题列表 [(level, text), ...]

        Returns:
            更新后的段落
        """
        if not paragraph.is_heading or not paragraph.heading_level:
            return paragraph

        # 构建标题链
        if previous_headings:
            paragraph.heading_chain = self.heading_parser.build_heading_chain(
                paragraph.source, paragraph.heading_level, previous_headings
            )

        # 翻译标题
        context = {
            "parent_headings": (
                paragraph.heading_chain[:-1] if paragraph.heading_chain else []
            )
        }

        translation = self.translate_heading(
            paragraph.source, paragraph.heading_level, context
        )

        # 记录翻译
        paragraph.add_translation(translation, "gemini_heading")
        paragraph.confirm(translation, "auto_heading")

        return paragraph


class MetadataTranslationService:
    """元信息翻译服务"""

    def __init__(self):
        self.metadata_parser = MetadataParser()

    def detect_and_translate_metadata(self, paragraph: Paragraph) -> Paragraph:
        """
        检测并翻译元信息

        Args:
            paragraph: 段落对象

        Returns:
            更新后的段落
        """
        # 检测元信息类型
        metadata_type = self.metadata_parser.detect_metadata_type(paragraph.source)

        if metadata_type:
            # 标记为元信息
            paragraph.is_metadata = True
            paragraph.metadata_type = metadata_type

            # 翻译元信息
            translation = self.metadata_parser.translate_metadata(
                paragraph.source, metadata_type
            )

            # 记录翻译
            paragraph.add_translation(translation, "auto_metadata")
            paragraph.confirm(translation, "auto_metadata")

        return paragraph


class EnhancedTranslationOrchestrator:
    """
    增强的翻译编排器

    支持标题和元信息的特殊处理
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        heading_service: Optional[HeadingTranslationService] = None,
        metadata_service: Optional[MetadataTranslationService] = None,
    ):
        self.llm = llm_provider
        self.heading_service = heading_service or HeadingTranslationService(
            llm_provider
        )
        self.metadata_service = metadata_service or MetadataTranslationService()

    def process_paragraphs(self, paragraphs: List[Paragraph]) -> List[Paragraph]:
        """
        处理段落列表，识别并处理标题和元信息

        Args:
            paragraphs: 段落列表

        Returns:
            处理后的段落列表
        """
        previous_headings = []

        for paragraph in paragraphs:
            # 1. 检测标题
            if paragraph.is_heading and paragraph.heading_level:
                paragraph = self.heading_service.process_heading_paragraph(
                    paragraph, previous_headings
                )

                # 更新标题历史
                previous_headings.append(
                    (paragraph.heading_level, paragraph.confirmed or paragraph.source)
                )

                # 清理旧的标题（只保留父级）
                previous_headings = [
                    (level, text)
                    for level, text in previous_headings
                    if level < paragraph.heading_level
                ] + [(paragraph.heading_level, paragraph.confirmed or paragraph.source)]

            # 2. 检测元信息
            elif not paragraph.is_heading:
                paragraph = self.metadata_service.detect_and_translate_metadata(
                    paragraph
                )

        return paragraphs
