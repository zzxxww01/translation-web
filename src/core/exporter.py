"""
Translation Agent - Markdown Exporter

Export translation projects to Markdown format.
Enhanced with:
- Inline element restoration (links, emphasis)
- Title and metadata export
- Image reference preservation
"""

from pathlib import Path
from typing import List, Optional

from .models import Section, Paragraph, ElementType, Glossary, InlineElement, ArticleMetadata


class MarkdownExporter:
    """Markdown 导出器"""

    def __init__(self, restore_inline_elements: bool = True):
        """
        初始化导出器

        Args:
            restore_inline_elements: 是否恢复内联元素（链接、强调等）
        """
        self.restore_inline_elements = restore_inline_elements

    def export_sections(
        self,
        sections: List[Section],
        title: str,
        title_translation: Optional[str] = None,
        metadata: Optional[ArticleMetadata] = None,
        include_source: bool = False,
        include_status: bool = False,
        use_translation: bool = True
    ) -> str:
        """
        导出章节列表为 Markdown

        Args:
            sections: 章节列表
            title: 文章标题
            title_translation: 文章标题翻译
            metadata: 文章元信息
            include_source: 是否包含原文（作为注释）
            include_status: 是否包含状态标记
            use_translation: 是否使用译文（否则使用原文）

        Returns:
            str: Markdown 内容
        """
        lines = []

        # 文章标题
        article_title = title_translation if use_translation and title_translation else title
        lines.append(f"# {article_title}")
        lines.append("")

        # 元信息
        if metadata:
            meta_lines = self._format_metadata(metadata, use_translation)
            if meta_lines:
                lines.extend(meta_lines)
                lines.append("")

        for section in sections:
            section_md = self.export_section(
                section,
                include_source=include_source,
                include_status=include_status,
                use_translation=use_translation
            )
            lines.append(section_md)

        return "\n".join(lines)

    def _format_metadata(
        self,
        metadata: ArticleMetadata,
        use_translation: bool = True
    ) -> List[str]:
        """格式化元信息"""
        lines = []

        if metadata.authors:
            authors_str = ", ".join(metadata.authors)
            label = "作者" if use_translation else "Author"
            lines.append(f"**{label}**: {authors_str}")

        if metadata.published_date:
            label = "日期" if use_translation else "Date"
            lines.append(f"**{label}**: {metadata.published_date}")

        if metadata.publication:
            label = "来源" if use_translation else "Source"
            if metadata.original_url:
                lines.append(f"**{label}**: [{metadata.publication}]({metadata.original_url})")
            else:
                lines.append(f"**{label}**: {metadata.publication}")

        if metadata.subtitle:
            lines.append("")
            lines.append(f"*{metadata.subtitle}*")

        return lines

    def export_section(
        self,
        section: Section,
        include_source: bool = False,
        include_status: bool = False,
        use_translation: bool = True
    ) -> str:
        """
        导出单个章节为 Markdown

        Args:
            section: 章节
            include_source: 是否包含原文
            include_status: 是否包含状态标记
            use_translation: 是否使用译文

        Returns:
            str: Markdown 内容
        """
        lines = []

        # 章节标题
        title = section.title_translation if use_translation and section.title_translation else section.title
        lines.append(f"## {title}")
        lines.append("")

        for p in section.paragraphs:
            para_md = self.export_paragraph(
                p,
                include_source=include_source,
                include_status=include_status,
                use_translation=use_translation
            )
            lines.append(para_md)
            lines.append("")

        return "\n".join(lines)

    def export_paragraph(
        self,
        paragraph: Paragraph,
        include_source: bool = False,
        include_status: bool = False,
        use_translation: bool = True
    ) -> str:
        """
        导出单个段落为 Markdown

        Args:
            paragraph: 段落
            include_source: 是否包含原文
            include_status: 是否包含状态标记
            use_translation: 是否使用译文

        Returns:
            str: Markdown 内容
        """
        # 获取文本
        if use_translation:
            text = paragraph.confirmed
            if not text and paragraph.translations:
                text = list(paragraph.translations.values())[0].text
            if not text:
                text = paragraph.source
        else:
            text = paragraph.source
            # 恢复内联元素（仅对原文）
            if self.restore_inline_elements and paragraph.inline_elements:
                text = self._restore_inline_elements(text, paragraph.inline_elements)

        # 图片特殊处理
        if paragraph.element_type == ElementType.IMAGE:
            return f"![image]({paragraph.source})"

        # 状态标记
        status_mark = ""
        if include_status:
            status_map = {
                "approved": "✅",
                "translated": "🔄",
                "reviewing": "🔄",
                "pending": "⏳",
                "translating": "⏳"
            }
            status_mark = status_map.get(paragraph.status.value, "") + " "

        # 原文注释
        source_comment = ""
        if include_source and paragraph.confirmed:
            src_preview = paragraph.source[:100] + '...' if len(paragraph.source) > 100 else paragraph.source
            source_comment = f"<!-- {src_preview} -->\n"

        # 根据元素类型格式化
        return self._format_by_element_type(
            paragraph.element_type, text, status_mark, source_comment
        )

    def _format_by_element_type(
        self,
        element_type: ElementType,
        text: str,
        status_mark: str = "",
        source_comment: str = ""
    ) -> str:
        """根据元素类型格式化输出"""
        if element_type == ElementType.H1:
            return f"{source_comment}# {status_mark}{text}"
        elif element_type == ElementType.H2:
            return f"{source_comment}## {status_mark}{text}"
        elif element_type == ElementType.H3:
            return f"{source_comment}### {status_mark}{text}"
        elif element_type == ElementType.H4:
            return f"{source_comment}#### {status_mark}{text}"
        elif element_type == ElementType.LI:
            return f"{source_comment}- {status_mark}{text}"
        elif element_type == ElementType.BLOCKQUOTE:
            return f"{source_comment}> {status_mark}{text}"
        elif element_type == ElementType.CODE:
            return f"{source_comment}```\n{text}\n```"
        elif element_type == ElementType.IMAGE:
            return f"![image]({text})"
        else:
            return f"{source_comment}{status_mark}{text}"

    def _restore_inline_elements(
        self,
        text: str,
        inline_elements: List[InlineElement]
    ) -> str:
        """
        将内联元素恢复到文本中（Markdown 格式）

        Args:
            text: 原始文本
            inline_elements: 内联元素列表

        Returns:
            带有 Markdown 格式的文本
        """
        if not inline_elements:
            return text

        # 按位置倒序排列（从后往前替换，避免位置偏移）
        sorted_elements = sorted(inline_elements, key=lambda x: x.start, reverse=True)

        result = text
        for el in sorted_elements:
            # 确保位置有效
            if el.start < 0 or el.end > len(result):
                # 尝试查找文本
                actual_start = result.find(el.text)
                if actual_start < 0:
                    continue
                el_start = actual_start
                el_end = actual_start + len(el.text)
            else:
                el_start = el.start
                el_end = el.end

            # 验证文本匹配
            if result[el_start:el_end] != el.text:
                actual_start = result.find(el.text)
                if actual_start < 0:
                    continue
                el_start = actual_start
                el_end = actual_start + len(el.text)

            # 生成替换文本
            if el.type == "link" and el.href:
                replacement = f"[{el.text}]({el.href})"
            elif el.type == "strong":
                replacement = f"**{el.text}**"
            elif el.type == "em":
                replacement = f"*{el.text}*"
            elif el.type == "code":
                replacement = f"`{el.text}`"
            else:
                continue

            result = result[:el_start] + replacement + result[el_end:]

        return result

    def export_glossary(self, glossary: Glossary) -> str:
        """
        导出术语表为 Markdown

        Args:
            glossary: 术语表

        Returns:
            str: Markdown 内容
        """
        lines = ["## 术语表", ""]
        lines.append("| 原文 | 翻译 | 策略 | 备注 |")
        lines.append("|------|------|------|------|")

        for term in glossary.terms:
            strategy_map = {
                "preserve": "保持原文",
                "first_annotate": "首次标注",
                "translate": "翻译"
            }
            strategy = strategy_map.get(term.strategy.value, term.strategy.value)
            translation = term.translation or "-"
            note = term.note or "-"
            lines.append(f"| {term.original} | {translation} | {strategy} | {note} |")

        return "\n".join(lines)

    def export_bilingual(
        self,
        sections: List[Section],
        title: str
    ) -> str:
        """
        导出双语对照版本

        Args:
            sections: 章节列表
            title: 文章标题

        Returns:
            str: Markdown 内容
        """
        lines = [f"# {title}", ""]

        for section in sections:
            # 章节标题
            title_trans = section.title_translation or section.title
            lines.append(f"## {title_trans}")
            if section.title_translation:
                lines.append(f"*{section.title}*")
            lines.append("")

            for p in section.paragraphs:
                # 译文
                text = p.confirmed
                if not text and p.translations:
                    text = list(p.translations.values())[0].text

                if text:
                    lines.append(text)
                    lines.append("")
                    lines.append(f"*{p.source}*")
                else:
                    lines.append(p.source)

                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)


def export_to_markdown(
    sections: List[Section],
    title: str,
    output_path: Optional[str] = None,
    include_source: bool = False
) -> str:
    """
    便捷函数：导出为 Markdown

    Args:
        sections: 章节列表
        title: 文章标题
        output_path: 输出文件路径（可选）
        include_source: 是否包含原文

    Returns:
        str: Markdown 内容
    """
    exporter = MarkdownExporter()
    content = exporter.export_sections(
        sections, title,
        include_source=include_source
    )

    if output_path:
        Path(output_path).write_text(content, encoding='utf-8')

    return content
