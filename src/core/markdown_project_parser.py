from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from slugify import slugify

from .format_tokens import assign_span_ids, expected_token_ids
from .models import ArticleMetadata, ElementType, InlineElement, Paragraph, Section


@dataclass
class ParsedMarkdownProject:
    title: str
    sections: List[Section]
    metadata: Optional[ArticleMetadata] = None


@dataclass
class MarkdownBlock:
    block_id: str
    block_index: int
    kind: str
    element_type: ElementType
    raw_markdown: str
    plain_text: str
    inline_elements: List[InlineElement]
    source_html: Optional[str] = None
    is_heading: bool = False
    heading_level: Optional[int] = None


class MarkdownProjectParser:
    SHORT_PARAGRAPH_THRESHOLD = 150
    _SOURCE_PATTERN = re.compile(
        r"^(?:Sources?|Data)\s*:\s",
        re.IGNORECASE,
    )
    _BYLINE_PATTERN = re.compile(r"^By\s+", re.IGNORECASE)
    _DATE_ACCESS_PATTERN = re.compile(
        r"^[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4}(?:\s+·\s+(?:Paid|Free))?$"
    )

    def __init__(
        self,
        max_paragraph_length: int = 800,
        merge_short_paragraphs: bool = True,
    ):
        self.max_paragraph_length = max_paragraph_length
        self.merge_short_paragraphs = merge_short_paragraphs

    def parse(
        self,
        markdown: str,
        metadata: Optional[ArticleMetadata] = None,
    ) -> ParsedMarkdownProject:
        normalized = markdown.replace("\r\n", "\n").strip()
        lines = normalized.split("\n")
        cursor = 0

        title = "Untitled"
        if cursor < len(lines) and lines[cursor].startswith("# "):
            title = lines[cursor][2:].strip() or title
            cursor += 1
            while cursor < len(lines) and not lines[cursor].strip():
                cursor += 1

        cursor = self._consume_front_matter(lines, cursor)
        blocks = self._parse_blocks(lines[cursor:])
        sections = self._build_sections(blocks)
        if self.merge_short_paragraphs:
            sections = self._merge_short_segments(sections)
        return ParsedMarkdownProject(title=title, sections=sections, metadata=metadata)

    def _consume_front_matter(self, lines: list[str], start: int) -> int:
        index = start

        # Skip YAML frontmatter (--- ... ---)
        if index < len(lines) and lines[index].strip() == "---":
            index += 1
            while index < len(lines):
                if lines[index].strip() == "---":
                    index += 1
                    break
                index += 1

        # Skip other metadata patterns
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith("## "):
                break
            if stripped.startswith("By "):
                index += 1
                continue
            if re.match(r"^[A-Z][a-z]{2}\s+\d{2},\s+\d{4}(?:\s+\S+\s+\w+)?$", stripped):
                index += 1
                continue
            break
        return index

    def _parse_blocks(self, lines: list[str]) -> list[MarkdownBlock]:
        blocks: list[MarkdownBlock] = []
        index = 0
        block_index = 0

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if not stripped:
                index += 1
                continue

            # 跳过水平线
            if re.match(r'^[-*_]{3,}\s*$', stripped):
                index += 1
                continue

            if stripped.startswith("```"):
                raw_lines = [line.rstrip()]
                code_lines: list[str] = []
                index += 1
                while index < len(lines) and not lines[index].strip().startswith("```"):
                    raw_lines.append(lines[index].rstrip("\n"))
                    code_lines.append(lines[index])
                    index += 1
                if index < len(lines):
                    raw_lines.append(lines[index].rstrip())
                    index += 1
                blocks.append(
                    MarkdownBlock(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="code",
                        element_type=ElementType.CODE,
                        raw_markdown="\n".join(raw_lines),
                        plain_text="\n".join(code_lines).rstrip("\n"),
                        inline_elements=[],
                    )
                )
                block_index += 1
                continue

            if self._starts_table(lines, index):
                table_lines = [lines[index].rstrip()]
                index += 1
                while index < len(lines) and "|" in lines[index]:
                    table_lines.append(lines[index].rstrip())
                    index += 1
                raw = "\n".join(table_lines)
                blocks.append(
                    MarkdownBlock(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="table",
                        element_type=ElementType.TABLE,
                        raw_markdown=raw,
                        plain_text=raw,
                        inline_elements=[],
                    )
                )
                block_index += 1
                continue

            if stripped.startswith("## "):
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="h2",
                        element_type=ElementType.H2,
                        raw_markdown=stripped,
                        markdown_text=stripped[3:].strip(),
                        is_heading=True,
                        heading_level=2,
                    )
                )
                block_index += 1
                index += 1
                continue
            if stripped.startswith("### "):
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="h3",
                        element_type=ElementType.H3,
                        raw_markdown=stripped,
                        markdown_text=stripped[4:].strip(),
                        is_heading=True,
                        heading_level=3,
                    )
                )
                block_index += 1
                index += 1
                continue
            if stripped.startswith("#### "):
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="h4",
                        element_type=ElementType.H4,
                        raw_markdown=stripped,
                        markdown_text=stripped[5:].strip(),
                        is_heading=True,
                        heading_level=4,
                    )
                )
                block_index += 1
                index += 1
                continue

            if stripped.startswith(">"):
                raw_lines: list[str] = []
                quote_lines: list[str] = []
                while index < len(lines) and lines[index].strip().startswith(">"):
                    raw_lines.append(lines[index].rstrip())
                    quote_lines.append(re.sub(r"^>\s?", "", lines[index].strip()))
                    index += 1
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="blockquote",
                        element_type=ElementType.BLOCKQUOTE,
                        raw_markdown="\n".join(raw_lines),
                        markdown_text="\n".join(quote_lines).strip(),
                    )
                )
                block_index += 1
                continue

            if re.match(r"^[-*+]\s+", stripped):
                raw = stripped
                text = re.sub(r"^[-*+]\s+", "", stripped)
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="li",
                        element_type=ElementType.LI,
                        raw_markdown=raw,
                        markdown_text=text,
                    )
                )
                block_index += 1
                index += 1
                continue

            if stripped.startswith("!["):
                blocks.append(
                    self._make_image_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        raw_markdown=stripped,
                    )
                )
                block_index += 1
                index += 1
                continue

            paragraph_lines = [stripped]
            index += 1
            while index < len(lines):
                candidate = lines[index].strip()
                if not candidate or self._starts_new_block(lines, index):
                    break
                paragraph_lines.append(candidate)
                index += 1
            raw = " ".join(paragraph_lines).strip()
            blocks.append(
                self._make_text_block(
                    block_id=f"b{block_index:04d}",
                    block_index=block_index,
                    kind="p",
                    element_type=ElementType.P,
                    raw_markdown=raw,
                    markdown_text=raw,
                )
            )
            block_index += 1

        return blocks

    def _make_text_block(
        self,
        block_id: str,
        block_index: int,
        kind: str,
        element_type: ElementType,
        raw_markdown: str,
        markdown_text: str,
        is_heading: bool = False,
        heading_level: Optional[int] = None,
    ) -> MarkdownBlock:
        plain_text, inline_elements = self._extract_inline_elements(markdown_text)
        return MarkdownBlock(
            block_id=block_id,
            block_index=block_index,
            kind=kind,
            element_type=element_type,
            raw_markdown=raw_markdown,
            plain_text=plain_text,
            inline_elements=assign_span_ids(inline_elements),
            is_heading=is_heading,
            heading_level=heading_level,
        )

    def _make_image_block(
        self,
        block_id: str,
        block_index: int,
        raw_markdown: str,
    ) -> MarkdownBlock:
        match = re.match(
            r'!\[(?P<alt>[^\]]*)\]\((?P<src><[^>]+>|[^)"]+?)(?:\s+"(?P<title>[^"]*)")?\)$',
            raw_markdown.strip(),
        )
        src = raw_markdown.strip()
        source_html = f'<img src="{self._escape_html_attr(src)}" />'
        if match:
            src = match.group("src").strip()
            if src.startswith("<") and src.endswith(">"):
                src = src[1:-1].strip()
            alt = match.group("alt").strip()
            title = (match.group("title") or "").strip()
            attrs = [f'src="{self._escape_html_attr(src)}"']
            if alt:
                attrs.append(f'alt="{self._escape_html_attr(alt)}"')
            if title:
                attrs.append(f'title="{self._escape_html_attr(title)}"')
            source_html = f"<img {' '.join(attrs)} />"

        return MarkdownBlock(
            block_id=block_id,
            block_index=block_index,
            kind="image",
            element_type=ElementType.IMAGE,
            raw_markdown=raw_markdown.strip(),
            plain_text=src,
            inline_elements=[],
            source_html=source_html,
        )

    def _starts_table(self, lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        if "|" not in header:
            return False
        return bool(
            re.match(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$", separator)
        )

    def _starts_new_block(self, lines: list[str], index: int) -> bool:
        stripped = lines[index].strip()
        return (
            stripped.startswith(("## ", "### ", "#### ", "```", "![", ">"))
            or re.match(r"^[-*+]\s+", stripped) is not None
            or self._starts_table(lines, index)
        )

    def _build_sections(self, blocks: list[MarkdownBlock]) -> list[Section]:
        sections: list[Section] = []
        current_section = Section(section_id="00-intro", title="Introduction", paragraphs=[])
        paragraph_index = 0
        seen_h2 = False

        for block in blocks:
            if block.element_type == ElementType.H2:
                if current_section.paragraphs or seen_h2:
                    sections.append(current_section)
                seen_h2 = True
                current_section = Section(
                    section_id=f"{len(sections):02d}-{slugify(block.plain_text[:30]) or 'section'}",
                    title=block.plain_text,
                    paragraphs=[],
                )
                paragraph_index = 0
                continue

            new_segments = self._segments_from_block(block, paragraph_index)
            for paragraph in new_segments:
                current_section.paragraphs.append(paragraph)
                paragraph_index += 1

        if current_section.paragraphs or not sections:
            sections.append(current_section)

        self._mark_source_metadata(sections)
        return sections

    def _mark_source_metadata(self, sections: list[Section]) -> None:
        """Mark structured front-matter / source paragraphs as metadata."""
        for section_index, section in enumerate(sections):
            for paragraph_index, paragraph in enumerate(section.paragraphs):
                if paragraph.is_metadata:
                    continue

                if (
                    section_index == 0
                    and paragraph_index == 0
                    and paragraph.element_type in {ElementType.H3, ElementType.H4}
                ):
                    paragraph.is_metadata = True
                    paragraph.metadata_type = "subtitle"
                    continue

                if paragraph.element_type not in {ElementType.P, ElementType.LI}:
                    continue

                source_text = paragraph.source.strip()
                if self._SOURCE_PATTERN.match(source_text):
                    paragraph.is_metadata = True
                    paragraph.metadata_type = "source"
                elif section_index == 0 and self._BYLINE_PATTERN.match(source_text):
                    paragraph.is_metadata = True
                    paragraph.metadata_type = "byline"
                elif section_index == 0 and self._DATE_ACCESS_PATTERN.match(source_text):
                    paragraph.is_metadata = True
                    paragraph.metadata_type = "date_access"

    def _segments_from_block(
        self,
        block: MarkdownBlock,
        start_index: int,
    ) -> list[Paragraph]:
        if block.element_type in {ElementType.IMAGE, ElementType.TABLE, ElementType.CODE}:
            return [self._build_segment(block, start_index, 0, len(block.plain_text), block.inline_elements)]

        if block.element_type not in {ElementType.P, ElementType.BLOCKQUOTE}:
            return [self._build_segment(block, start_index, 0, len(block.plain_text), block.inline_elements)]

        if len(block.plain_text) <= self.max_paragraph_length:
            return [self._build_segment(block, start_index, 0, len(block.plain_text), block.inline_elements)]

        chunk_ranges = self._split_block_ranges(block)
        if len(chunk_ranges) <= 1:
            return [self._build_segment(block, start_index, 0, len(block.plain_text), block.inline_elements)]

        segments: list[Paragraph] = []
        for offset, (chunk_start, chunk_end) in enumerate(chunk_ranges):
            local_elements = self._slice_inline_elements(block.inline_elements, chunk_start, chunk_end)
            if local_elements is None:
                return [self._build_segment(block, start_index, 0, len(block.plain_text), block.inline_elements)]
            segments.append(
                self._build_segment(
                    block,
                    start_index + offset,
                    chunk_start,
                    chunk_end,
                    local_elements,
                )
            )
        return segments

    def _build_segment(
        self,
        block: MarkdownBlock,
        paragraph_index: int,
        segment_start: int,
        segment_end: int,
        local_inline_elements: list[InlineElement],
    ) -> Paragraph:
        text = block.plain_text[segment_start:segment_end]
        is_metadata = block.element_type == ElementType.IMAGE
        metadata_type = "image" if is_metadata else None
        return Paragraph(
            id=f"p{paragraph_index:03d}",
            index=paragraph_index,
            source=text,
            source_html=block.source_html,
            element_type=block.element_type,
            inline_elements=assign_span_ids(local_inline_elements),
            parent_block_id=block.block_id,
            parent_block_index=block.block_index,
            parent_block_type=block.element_type,
            parent_block_markdown=block.raw_markdown,
            parent_block_plain_text=block.plain_text,
            parent_source_html=block.source_html,
            parent_inline_elements=assign_span_ids(block.inline_elements),
            segment_start=segment_start,
            segment_end=segment_end,
            expected_tokens=expected_token_ids(local_inline_elements),
            is_heading=block.is_heading,
            heading_level=block.heading_level,
            is_metadata=is_metadata,
            metadata_type=metadata_type,
        )

    def _split_block_ranges(self, block: MarkdownBlock) -> list[tuple[int, int]]:
        sentence_ranges = self._split_sentences_with_offsets(block.plain_text)
        if len(sentence_ranges) <= 1:
            return [(0, len(block.plain_text))]

        chunks: list[tuple[int, int]] = []
        current_start, current_end = sentence_ranges[0]

        for sentence_start, sentence_end in sentence_ranges[1:]:
            if sentence_end - current_start > self.max_paragraph_length:
                if self._boundary_breaks_inline(block.inline_elements, current_end):
                    return [(0, len(block.plain_text))]
                chunks.append((current_start, current_end))
                current_start, current_end = sentence_start, sentence_end
            else:
                current_end = sentence_end

        chunks.append((current_start, current_end))
        return chunks

    def _merge_short_segments(self, sections: list[Section]) -> list[Section]:
        for section in sections:
            if len(section.paragraphs) <= 1:
                continue

            merged: list[Paragraph] = []
            current: Optional[Paragraph] = None
            current_inline: list[InlineElement] = []

            for paragraph in section.paragraphs:
                if paragraph.element_type in {
                    ElementType.IMAGE,
                    ElementType.TABLE,
                    ElementType.CODE,
                    ElementType.H3,
                    ElementType.H4,
                    ElementType.LI,
                }:
                    if current is not None:
                        current.inline_elements = assign_span_ids(current_inline)
                        current.expected_tokens = expected_token_ids(current.inline_elements)
                        current.segment_end = current.segment_start + len(current.source)
                        merged.append(current)
                        current = None
                        current_inline = []
                    merged.append(paragraph)
                    continue

                same_parent = (
                    current is not None
                    and current.parent_block_id == paragraph.parent_block_id
                    and current.element_type == paragraph.element_type
                )

                if len(paragraph.source) < self.SHORT_PARAGRAPH_THRESHOLD and same_parent:
                    offset = len(current.source) + 1
                    current.source = f"{current.source} {paragraph.source}"
                    current.segment_end = paragraph.segment_end
                    for element in paragraph.inline_elements or []:
                        current_inline.append(
                            InlineElement(
                                type=element.type,
                                text=element.text,
                                start=element.start + offset,
                                end=element.end + offset,
                                href=element.href,
                                title=element.title,
                                span_id=element.span_id,
                            )
                        )
                elif len(paragraph.source) < self.SHORT_PARAGRAPH_THRESHOLD and current is None:
                    current = paragraph.model_copy(deep=True)
                    current_inline = list(current.inline_elements or [])
                else:
                    if current is not None:
                        current.inline_elements = assign_span_ids(current_inline)
                        current.expected_tokens = expected_token_ids(current.inline_elements)
                        current.segment_end = current.segment_start + len(current.source)
                        merged.append(current)
                        current = None
                        current_inline = []
                    merged.append(paragraph)

            if current is not None:
                current.inline_elements = assign_span_ids(current_inline)
                current.expected_tokens = expected_token_ids(current.inline_elements)
                current.segment_end = current.segment_start + len(current.source)
                merged.append(current)

            for idx, paragraph in enumerate(merged):
                paragraph.id = f"p{idx:03d}"
                paragraph.index = idx
            section.paragraphs = merged

        return sections

    def _split_sentences_with_offsets(self, text: str) -> list[tuple[int, int]]:
        pattern = re.compile(r".+?(?:[.!?。！？]+(?=\s|$)|$)", re.DOTALL)
        ranges: list[tuple[int, int]] = []
        for match in pattern.finditer(text):
            start, end = self._trim_range(text, match.start(), match.end())
            if start < end:
                ranges.append((start, end))
        return ranges or [(0, len(text))]

    def _trim_range(self, text: str, start: int, end: int) -> tuple[int, int]:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        return start, end

    def _boundary_breaks_inline(
        self,
        elements: list[InlineElement],
        boundary: int,
    ) -> bool:
        return any(element.start < boundary < element.end for element in elements)

    def _slice_inline_elements(
        self,
        elements: list[InlineElement],
        start: int,
        end: int,
    ) -> Optional[list[InlineElement]]:
        local: list[InlineElement] = []
        for element in elements:
            if element.end <= start or element.start >= end:
                continue
            if not (start <= element.start and element.end <= end):
                return None
            local.append(
                InlineElement(
                    type=element.type,
                    text=element.text,
                    start=element.start - start,
                    end=element.end - start,
                    href=element.href,
                    title=element.title,
                    span_id=element.span_id,
                )
            )
        return local

    def _extract_inline_elements(self, text: str) -> tuple[str, list[InlineElement]]:
        result: list[str] = []
        elements: list[InlineElement] = []
        index = 0
        output_pos = 0
        combined = re.compile(
            r'\[([^\]]+)\]\((<[^>]+>|[^()\s]*(?:\([^)]*\)[^()\s]*)*)(?:\s+"([^"]+)")?\)|\*\*([^*]+)\*\*|__([^_]+)__|(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)|`([^`]+)`'
        )

        for match in combined.finditer(text):
            if match.start() > index:
                segment = text[index:match.start()]
                result.append(segment)
                output_pos += len(segment)

            if match.group(1) is not None:
                plain = match.group(1)
                href = (match.group(2) or "").strip()
                if href.startswith("<") and href.endswith(">"):
                    href = href[1:-1].strip()
                elements.append(
                    InlineElement(
                        type="link",
                        text=plain,
                        start=output_pos,
                        end=output_pos + len(plain),
                        href=href,
                        title=match.group(3),
                    )
                )
            elif match.group(4) is not None or match.group(5) is not None:
                plain = match.group(4) or match.group(5) or ""
                elements.append(
                    InlineElement(
                        type="strong",
                        text=plain,
                        start=output_pos,
                        end=output_pos + len(plain),
                    )
                )
            elif match.group(6) is not None or match.group(7) is not None:
                plain = match.group(6) or match.group(7) or ""
                elements.append(
                    InlineElement(
                        type="em",
                        text=plain,
                        start=output_pos,
                        end=output_pos + len(plain),
                    )
                )
            else:
                plain = match.group(8) or ""
                elements.append(
                    InlineElement(
                        type="code",
                        text=plain,
                        start=output_pos,
                        end=output_pos + len(plain),
                    )
                )

            result.append(plain)
            output_pos += len(plain)
            index = match.end()

        if index < len(text):
            result.append(text[index:])

        return "".join(result), elements

    def _escape_html_attr(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
