from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from slugify import slugify

from .format_tokens import assign_span_ids, expected_token_ids
from .image_assets import parse_markdown_image_reference
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
    # 列表项的缩进层级（0=一级）。解析时不记录的话，多级列表导出后会被
    # 统一渲染成一级 `- `，信息结构被改变。
    list_indent: int = 0


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
            # 仅把 "By <Title-Case 人名列表>" 形态的短行当作 byline 跳过;
            # 避免误删以 "By leveraging/By contrast/By the way" 开头的正文句子(审计 N4)。
            if (
                len(stripped) <= 80
                and re.fullmatch(
                    r"By\s+[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+)*"
                    r"(?:\s*(?:,|and|&)\s*[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+)*)*",
                    stripped,
                )
            ):
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
                # 缩进层级从未 strip 的原行算，raw 也保留缩进——否则多级列表
                # 在导出时全部塌成一级。
                list_indent = self._list_indent_level(lines[index])
                raw = " " * (list_indent * 2) + stripped
                text = re.sub(r"^[-*+]\s+", "", stripped)
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="li",
                        element_type=ElementType.LI,
                        raw_markdown=raw,
                        markdown_text=text,
                        list_indent=list_indent,
                    )
                )
                block_index += 1
                index += 1
                continue

            # 有序列表项:各自成独立块,保留序号("1. text")。不并入散文累积,
            # 否则连续条目会被合并成一行散文、序号变正文(审计 N3)。
            if re.match(r"^\d+[.)]\s+", stripped):
                blocks.append(
                    self._make_text_block(
                        block_id=f"b{block_index:04d}",
                        block_index=block_index,
                        kind="p",
                        element_type=ElementType.P,
                        raw_markdown=stripped,
                        markdown_text=stripped,
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

    @staticmethod
    def _list_indent_level(line: str) -> int:
        """列表项的缩进层级：每 2 个空格算一级，tab 按 4 空格归一。"""
        leading = len(line) - len(line.lstrip(" \t"))
        expanded = len(line[:leading].expandtabs(4))
        return expanded // 2

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
        list_indent: int = 0,
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
            list_indent=list_indent,
        )

    def _make_image_block(
        self,
        block_id: str,
        block_index: int,
        raw_markdown: str,
    ) -> MarkdownBlock:
        reference = parse_markdown_image_reference(raw_markdown)
        src = raw_markdown.strip()
        source_html = f'<img src="{self._escape_html_attr(src)}" />'
        if reference:
            src = reference.source
            alt = reference.alt.strip()
            title = reference.title.strip()
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
            or re.match(r"^\d+[.)]\s+", stripped) is not None
            or self._starts_table(lines, index)
        )

    def _build_sections(self, blocks: list[MarkdownBlock]) -> list[Section]:
        sections: list[Section] = []
        current_section = Section(
            section_id="00-intro", title="Introduction", synthetic=True, paragraphs=[]
        )
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

                # 文章副标题：位于 H1 主标题与第一个 H2 章节之间，因此一定落在
                # **合成的** intro 章里（synthetic=True 表示这段内容出现在任何 H2
                # 之前）。少了 synthetic 这个前提，「第 0 章第 0 段是 H3/H4」会把
                # 正文小标题误判成副标题——而被打上 metadata 标记的段落会被排除出
                # 正文翻译，永远保持英文；有副标题时更会被整段替换成文章副标题。
                # 三种语料外形态实测都会中招：无副标题且首章以 H3 小标题开头、
                # 首章以 H4 开头、以及没有 H1 直接从 H2 起头的短快评。
                if (
                    section_index == 0
                    and paragraph_index == 0
                    and section.synthetic
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
            list_indent=block.list_indent,
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

    # 数学区域。必须在强调解析之前整段排除掉，否则 LaTeX 的下标 `_` 会被当成
    # 斜体定界符成对吞掉。实测：
    #   `\alpha_{i\to t}\,\mathbf{v}_i, \qquad \alpha_{i\to t}`
    #   → `\alpha_{i\to t}\,\mathbf{v}i, \qquad \alpha{i\to t}`（两个 `_` 消失，
    #     还凭空产生一个横跨半条公式的假 em token）
    # 关键在于 `}` 和 `,` 不是单词字符，flanking 守卫挡不住它们后面的 `_`。
    # 行内 `$...$` 沿用 markdown_postprocess 的 Pandoc 规则：开定界符后非空白、
    # 闭定界符前非空白、闭定界符后不跟数字（否则 `$100 到 $200` 会被当公式）。
    _MATH_SPAN = re.compile(
        r"\$\$[\s\S]*?\$\$"
        r"|\\\[[\s\S]*?\\\]"
        r"|\\\([\s\S]*?\\\)"
        r"|\$(?![\s$])[^$\n]*[^\s$]\$(?![\d$])"
    )
    # 掩码用：行内代码里的 `$` 不得参与配对（`` `a $ b` `` 后面若有真公式会错配）。
    _INLINE_CODE_SPAN = re.compile(r"`[^`\n]+`")

    @classmethod
    def _math_spans(cls, text: str) -> list[tuple[int, int]]:
        if "$" not in text and "\\[" not in text and "\\(" not in text:
            return []
        # 等长空格掩码，保持所有偏移不变
        masked = cls._INLINE_CODE_SPAN.sub(lambda m: " " * len(m.group(0)), text)
        return [(m.start(), m.end()) for m in cls._MATH_SPAN.finditer(masked)]

    def _extract_inline_elements(self, text: str) -> tuple[str, list[InlineElement]]:
        result: list[str] = []
        elements: list[InlineElement] = []
        index = 0
        output_pos = 0
        math_spans = self._math_spans(text)
        # italic 分支遵循 CommonMark flanking:* 定界符内侧不可为空白(避免 "2 * 3 * 4"
        # 被当强调);_ 定界符外侧不可为单词字符(避免 snake_case 标识符如 get_data_from_api
        # 的下划线被吞并、单词被粘连)。见审计 N2。
        #
        # 每个定界符还必须带 `(?<!\\)`：html2md 会把原文里的字面 `*` `_` 转义成
        # `\*` `\_`，不认转义就会把它们当成强调标记吃掉，并凭空造出一个假的
        # em/strong token 送进 prompt。实测受损案例：
        #   `\*not italic\*`      → `\not italic\`（字面星号丢失）
        #   `数学 P\_{max} 与 V\_{dd}` → `数学 P\{max} 与 V\{dd}`（LaTeX 下标被破坏，
        #                            假 em 还跨越了两个变量）
        # 下标场景尤其危险：`_` 的后置守卫只挡字母数字，`_{max}` 后面是 `{` 会放行。
        combined = re.compile(
            r'(?<!\\)\[([^\]]+)\]\((<[^>]+>|[^()\s]*(?:\([^)]*\)[^()\s]*)*)(?:\s+"([^"]+)")?\)'
            r'|(?<!\\)\*\*([^*]+)(?<!\\)\*\*|(?<!\\)__([^_]+)(?<!\\)__'
            r'|(?<![\\*])\*([^\s*](?:[^*]*[^\s*])?)(?<!\\)\*(?!\*)'
            r"|(?<![\\A-Za-z0-9_])_([^\s_](?:[^_]*[^\s_])?)(?<!\\)_(?![A-Za-z0-9_])"
            r'|(?<!\\)`([^`]+)`'
        )

        for match in combined.finditer(text):
            # 落在数学区域里的"强调"一律不认。跳过时不推进 index，这段文本会由
            # 下一次的 gap 拼接（或末尾 tail）原样输出，偏移因此保持正确。
            if any(start <= match.start() < end for start, end in math_spans):
                continue
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

        plain_text = "".join(result)
        self._collect_math_elements(plain_text, elements)
        return plain_text, elements

    @staticmethod
    def _collect_math_elements(
        plain_text: str, elements: list[InlineElement]
    ) -> None:
        """把公式登记为 ``math`` 内联元素，原地追加进 ``elements``。

        公式在 ``plain_text`` 里是**原样保留**的（强调解析已整段跳过数学区），
        所以可以直接在成品文本上定位，偏移无需换算。

        登记的意义在翻译阶段：math 元素会被 ``[[[MATH_n|...]]]`` 包住送给模型，
        还原时无条件用原文覆盖，模型再也碰不到公式内容。此前公式是当普通文本
        送进 prompt 的，被改写过——`\\mathbf{q}_l` 变成
        `\\backslash mathbf{q}\\backslash _l`，渲染出来是字面的 `\\mathbfq\\_l`。
        """
        if "$" not in plain_text and "\\[" not in plain_text and "\\(" not in plain_text:
            return

        # inline code 的内容在 plain 里是裸文本（反引号已脱掉），里面的 `$`
        # 不该参与公式配对，先等长掩掉。
        masked = list(plain_text)
        for element in elements:
            if element.type != "code":
                continue
            for offset in range(element.start, min(element.end, len(masked))):
                masked[offset] = " "

        for match in MarkdownProjectParser._MATH_SPAN.finditer("".join(masked)):
            elements.append(
                InlineElement(
                    type="math",
                    text=plain_text[match.start() : match.end()],
                    start=match.start(),
                    end=match.end(),
                )
            )
        # 按文本顺序排好，让 MATH_n 的编号与出现次序一致；同类型元素的相对
        # 顺序不变，因此其他 token 的编号不受影响。
        elements.sort(key=lambda element: element.start)

    def _escape_html_attr(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
