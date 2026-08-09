from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.core.models import Paragraph, Section


class _PrescanLLM:
    def prescan_section_with_flash(self, **_kwargs):
        return {
            "new_terms": [
                {
                    "term": "inference cluster",
                    "suggested_translation": "推理集群",
                    "context": "AI infrastructure",
                    "confidence": 0.9,
                }
            ],
            "term_usages": {"inference cluster": "first"},
        }


def test_prescan_network_phase_has_no_context_side_effect_until_committed() -> None:
    context = LayeredContextManager()
    translator = FourStepTranslator(_PrescanLLM(), context)
    section = Section(
        section_id="s1",
        title="Intro",
        paragraphs=[Paragraph(id="p1", index=0, source="Inference cluster")],
    )

    result = translator.scan_section_terms(section)

    assert result is not None
    assert context.get_all_terms() == {}

    translator.apply_section_prescan(result)

    assert context.get_all_terms() == {"inference cluster": "推理集群"}
