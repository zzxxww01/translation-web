import re

from src.core.inline_recovery_service import InlineRecoveryService
from src.core.models import ElementType, InlineElement, Paragraph, Section

# 与 translation_qa._LINK_COLLAPSE 同源：`[` 内再嵌 `[...](` 即嵌套坏链
_NESTED_LINK = re.compile(r"\[[^\]\[]*\[[^\]]*\]\(")


def test_restore_single_link_prefers_exact_match() -> None:
    service = InlineRecoveryService()
    link = InlineElement(type="link", text="OpenAI", start=0, end=6, href="https://openai.com")

    restored = service.restore_single_link(
        source_text="OpenAI released GPT-5.",
        translated_text="OpenAI 发布了 GPT-5。",
        link_element=link,
    )

    assert restored == "[OpenAI](https://openai.com) 发布了 GPT-5。"


def test_render_source_block_markdown_restores_inline_elements() -> None:
    service = InlineRecoveryService()
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="Read OpenAI docs",
        inline_elements=[
            InlineElement(
                type="link",
                text="OpenAI docs",
                start=5,
                end=16,
                href="https://platform.openai.com/docs",
            )
        ],
        element_type=ElementType.P,
    )
    section = Section(section_id="s1", title="Intro", paragraphs=[paragraph])

    blocks = service.group_section_blocks(section)
    assert len(blocks) == 1
    assert service.render_source_block_markdown(blocks[0]) == "Read [OpenAI docs](https://platform.openai.com/docs)"


def test_meta_compute_source_line_double_links_stay_independent() -> None:
    # A-3 回归（Meta Compute source 行实测）：双链接段兜底恢复必须产出
    # 两条独立闭合链接，禁止 `[[A](url), B](url)` 嵌套。
    service = InlineRecoveryService()
    source_text = "Source: Meta, SemiAnalysis Estimates"
    elements = [
        InlineElement(type="link", text="Meta", start=8, end=12, href="https://meta.com"),
        InlineElement(
            type="link",
            text="SemiAnalysis Estimates",
            start=14,
            end=36,
            href="https://semianalysis.com",
        ),
    ]

    restored = service.smart_fallback_restore_inline_elements(
        source_text=source_text,
        translated_text="来源：Meta，SemiAnalysis 估算",
        elements=elements,
        block_id="b1",
    )

    assert _NESTED_LINK.search(restored) is None
    assert restored.count("](") == 2
    assert restored.count("https://meta.com") == 1
    assert restored.count("https://semianalysis.com") == 1


def test_restore_single_link_never_wraps_existing_link() -> None:
    # 已生成的链接区段不可再被包裹：只能降级为段末追加来源链接。
    service = InlineRecoveryService()
    link = InlineElement(type="link", text="Meta", start=0, end=4, href="https://meta.com")

    restored = service.restore_single_link(
        source_text="Meta and SemiAnalysis estimates",
        translated_text="[Meta 与 SemiAnalysis 估算](https://semianalysis.com)",
        link_element=link,
    )

    assert _NESTED_LINK.search(restored) is None
    assert restored.endswith("（[来源](https://meta.com)）")
    assert restored.startswith("[Meta 与 SemiAnalysis 估算](https://semianalysis.com)")


def test_restore_single_link_skips_segment_overlapping_generated_link() -> None:
    # 句读切段命中的区段若与既有链接重叠，同样降级为段末追加。
    service = InlineRecoveryService()
    link = InlineElement(
        type="link", text="quarterly report", start=20, end=36, href="https://a.com/q"
    )

    translated = "前文说明，[季度报告分析](https://b.com)，其余内容。"
    restored = service.restore_single_link(
        source_text="As explained, see quarterly report analysis, and more.",
        translated_text=translated,
        link_element=link,
    )

    assert _NESTED_LINK.search(restored) is None
    assert restored.count("https://b.com") == 1
