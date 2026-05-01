"""Markdown exporter built on parent-block reconstruction."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .format_tokens import (
    FormatRecoveryError,
    reconstruct_block_tokenized_text,
    require_valid_reconstruction,
    restore_markdown_from_tokenized,
    sorted_block_groups,
    tokenize_text,
)
from .markdown_postprocess import postprocess_markdown
from .models import ArticleMetadata, ElementType, Glossary, Paragraph, Section


class MarkdownExporter:
    """Export sections using the canonical block skeleton."""

    def __init__(self, restore_inline_elements: bool = True):
        self.restore_inline_elements = restore_inline_elements

    def export_sections(
        self,
        sections: List[Section],
        title: str,
        title_translation: Optional[str] = None,
        metadata: Optional[ArticleMetadata] = None,
        include_source: bool = False,
        include_status: bool = False,
        use_translation: bool = True,
    ) -> str:
        lines = []
        article_title = title_translation if use_translation and title_translation else title
        lines.append(f"# {article_title}")
        lines.append("")

        if metadata:
            meta_lines = self._format_metadata(metadata, use_translation)
            if meta_lines:
                lines.extend(meta_lines)
                lines.append("")

        for section in sections:
            lines.append(
                self.export_section(
                    section,
                    include_source=include_source,
                    include_status=include_status,
                    use_translation=use_translation,
                )
            )

        return postprocess_markdown("\n".join(lines))

    def _format_metadata(
        self,
        metadata: ArticleMetadata,
        use_translation: bool = True,
    ) -> List[str]:
        lines: List[str] = []

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
        use_translation: bool = True,
    ) -> str:
        lines = []
        title = section.title_translation if use_translation and section.title_translation else section.title
        lines.append(f"## {title}")
        lines.append("")

        for block in self._group_section_blocks(section):
            if include_source and any(p.confirmed for p in block):
                source_comment = block[0].parent_block_plain_text or " ".join(
                    p.source for p in block
                )
                lines.append(f"<!-- {source_comment} -->")
            if include_status:
                status_mark = self._status_mark(block[0])
                if status_mark:
                    lines.append(f"<!-- status:{status_mark} -->")
            lines.append(self._render_block_markdown(block, use_translation=use_translation))
            lines.append("")

        return "\n".join(lines)

    def _group_section_blocks(self, section: Section) -> list[list[Paragraph]]:
        return sorted_block_groups(section.paragraphs)

    def _render_block_markdown(
        self,
        paragraphs: list[Paragraph],
        use_translation: bool = True,
    ) -> str:
        first = paragraphs[0]
        block_type = first.parent_block_type or first.element_type

        if not use_translation:
            return self._render_source_block_markdown(first)

        if block_type == ElementType.IMAGE:
            return first.parent_block_markdown or first.source_html or f"![image]({first.source})"
        if block_type == ElementType.TABLE:
            return first.parent_block_markdown or first.parent_source_html or first.source
        if block_type == ElementType.CODE:
            try:
                payload = require_valid_reconstruction(paragraphs, fallback_to_source=True)
            except FormatRecoveryError:
                payload = reconstruct_block_tokenized_text(paragraphs, fallback_to_source=True)
            return f"```\n{payload.text}\n```"

        try:
            payload = require_valid_reconstruction(paragraphs, fallback_to_source=True)
            if first.parent_inline_elements:
                text = restore_markdown_from_tokenized(
                    payload.tokenized_text or payload.text,
                    first.parent_inline_elements,
                )
            else:
                text = payload.text
        except FormatRecoveryError:
            text = reconstruct_block_tokenized_text(paragraphs, fallback_to_source=True).text
        return self._format_by_element_type(block_type, text)

    def _render_source_block_markdown(self, paragraph: Paragraph) -> str:
        if paragraph.parent_block_markdown:
            return paragraph.parent_block_markdown
        if self.restore_inline_elements and paragraph.inline_elements:
            tokenized = tokenize_text(paragraph.source, paragraph.inline_elements)
            text = restore_markdown_from_tokenized(tokenized, paragraph.inline_elements)
        else:
            text = paragraph.source
        return self._format_by_element_type(paragraph.element_type, text)

    def _status_mark(self, paragraph: Paragraph) -> str:
        status_map = {
            "approved": "approved",
            "translated": "translated",
            "reviewing": "reviewing",
            "pending": "pending",
            "translating": "translating",
            "modified": "modified",
        }
        return status_map.get(paragraph.status.value, "")

    def _format_by_element_type(self, element_type: ElementType, text: str) -> str:
        if element_type == ElementType.H1:
            return f"# {text}"
        if element_type == ElementType.H2:
            return f"## {text}"
        if element_type == ElementType.H3:
            return f"### {text}"
        if element_type == ElementType.H4:
            return f"#### {text}"
        if element_type == ElementType.LI:
            return f"- {text}"
        if element_type == ElementType.BLOCKQUOTE:
            return f"> {text}"
        if element_type == ElementType.CODE:
            return f"```\n{text}\n```"
        if element_type == ElementType.IMAGE:
            return f"![image]({text})"
        return text

    def export_glossary(self, glossary: Glossary) -> str:
        lines = ["## 术语表", ""]
        lines.append("| 原文 | 翻译 | 策略 | 词义说明 |")
        lines.append("|------|------|------|------|")

        for term in glossary.terms:
            strategy_map = {
                "preserve": "保留原文",
                "first_annotate": "首次标注",
                "translate": "翻译",
            }
            strategy = strategy_map.get(term.strategy.value, term.strategy.value)
            translation = term.translation or "-"
            note = term.note or "-"
            lines.append(f"| {term.original} | {translation} | {strategy} | {note} |")

        return "\n".join(lines)

    def export_bilingual(
        self,
        sections: List[Section],
        title: str,
    ) -> str:
        lines = [f"# {title}", ""]

        for section in sections:
            title_trans = section.title_translation or section.title
            lines.append(f"## {title_trans}")
            if section.title_translation:
                lines.append(f"*{section.title}*")
            lines.append("")

            for block in self._group_section_blocks(section):
                translated = self._render_block_markdown(block, use_translation=True)
                source = self._render_block_markdown(block, use_translation=False)
                lines.append(translated)
                lines.append("")
                lines.append(f"*{source}*")
                lines.append("")
                lines.append("---")
                lines.append("")

        return postprocess_markdown("\n".join(lines))


def export_to_markdown(
    sections: List[Section],
    title: str,
    output_path: Optional[str] = None,
    include_source: bool = False,
) -> str:
    exporter = MarkdownExporter()
    content = exporter.export_sections(
        sections,
        title,
        include_source=include_source,
    )

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")

    return content

