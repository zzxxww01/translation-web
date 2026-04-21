from src.core.inline_recovery_service import InlineRecoveryService
from src.core.models import ElementType, InlineElement, Paragraph, Section


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
