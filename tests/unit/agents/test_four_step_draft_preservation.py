"""回归测试：四步法后续步骤（反思/润色）失败时保留初译 draft，而非整章丢弃。"""

from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.core.format_tokens import TranslationPayload
from src.core.models import Paragraph, ParagraphStatus, Section, SectionUnderstanding


class _LLM:
    """占位 LLM；本测试通过 stub 控制各步骤，不真正调用。"""


def _section() -> Section:
    return Section(
        section_id="s1",
        title="Sec 1",
        paragraphs=[
            Paragraph(id="p1", index=0, source="First", status=ParagraphStatus.PENDING),
            Paragraph(id="p2", index=1, source="Second", status=ParagraphStatus.PENDING),
        ],
    )


def test_reflection_failure_returns_draft_instead_of_raising():
    translator = FourStepTranslator(_LLM(), LayeredContextManager())
    section = _section()

    understanding = SectionUnderstanding(
        role_in_article="body", relation_to_previous="", relation_to_next="",
        key_points=[], translation_notes=[],
    )
    # Step 1 理解 / Step 2 初译 成功，Step 3 反思抛错
    translator._step_understand = lambda *a, **k: understanding
    translator._translate_batch = lambda *a, **k: [
        TranslationPayload(text="初译一"),
        TranslationPayload(text="初译二"),
    ]

    def _boom(*a, **k):
        raise RuntimeError("reflect failed")

    translator._step_reflect = _boom

    result = translator.translate_section(section, [section])

    # 不抛异常，返回降级 draft
    assert result.translations == ["初译一", "初译二"]
    assert result.draft_translations == ["初译一", "初译二"]
    assert result.reflection is None


def test_early_failure_still_raises():
    translator = FourStepTranslator(_LLM(), LayeredContextManager())
    section = _section()

    def _boom(*a, **k):
        raise RuntimeError("understand failed")

    translator._step_understand = _boom

    # 初译尚未完成（Step 1 失败），无可用降级，应上抛
    try:
        translator.translate_section(section, [section])
        assert False, "should have raised"
    except RuntimeError as e:
        assert "understand failed" in str(e)
