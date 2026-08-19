# -*- coding: utf-8 -*-
"""文章副标题的识别不能只靠版式巧合。

副标题位于 H1 主标题与第一个 H2 章节之间，因此一定落在**合成的** intro 章里。
旧规则只判「第 0 章第 0 段是 H3/H4」，在 16 篇语料上 16/16 不误伤——典型的
按版式调优。被误判成 subtitle 的段落会被排除出正文翻译（永远保持英文），
有副标题时更会被整段替换成文章副标题，内容张冠李戴。
"""

import pytest

from src.core.markdown_project_parser import MarkdownProjectParser


@pytest.fixture
def parser():
    return MarkdownProjectParser(merge_short_paragraphs=False)


def _first_paragraph(parser, markdown):
    return parser.parse(markdown).sections[0].paragraphs[0]


def test_real_subtitle_after_title_is_metadata(parser):
    para = _first_paragraph(parser, "# Title\n\n### The Real Subtitle\n\n## Ch1\n\nBody.\n")
    assert para.is_metadata
    assert para.metadata_type == "subtitle"


def test_h3_subheading_in_first_chapter_is_body(parser):
    # 无副标题、首个 H2 章节以 H3 小标题开头
    para = _first_paragraph(
        parser, "# High-NA EUV Is Slipping\n\n## Equipment\n\n### Intel's Position\n\nBody.\n"
    )
    assert not para.is_metadata, "正文小标题被误判为副标题，将永不翻译"


def test_h4_subheading_in_first_chapter_is_body(parser):
    para = _first_paragraph(parser, "# Memory Pricing\n\n## Supply\n\n#### Q3 Prices\n\nBody.\n")
    assert not para.is_metadata


def test_article_without_h1_title_keeps_subheading_as_body(parser):
    # 短快评常见形态：没有 H1，直接从 H2 起头
    para = _first_paragraph(parser, "## Why CPO Matters\n\n### The Physics\n\nBody.\n")
    assert not para.is_metadata


def test_first_chapter_body_paragraph_untouched(parser):
    para = _first_paragraph(parser, "# Title\n\n## Chapter\n\nPlain body paragraph.\n")
    assert not para.is_metadata


def test_subtitle_detection_needs_synthetic_section(parser):
    # 判别信号本身：真副标题所在的章节是合成的（出现在任何 H2 之前）
    with_subtitle = parser.parse("# T\n\n### Sub\n\n## Ch\n\nBody.\n")
    without_subtitle = parser.parse("# T\n\n## Ch\n\n### Sub\n\nBody.\n")
    assert with_subtitle.sections[0].synthetic is True
    assert without_subtitle.sections[0].synthetic is False
