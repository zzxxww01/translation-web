from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.core.format_tokens import TranslationPayload
from src.core.models import (
    Paragraph,
    ParagraphStatus,
    ReflectionResult,
    Section,
    SectionUnderstanding,
)
from src.llm.usage_metrics import LLMUsageMetrics


def test_draft_and_refine_calls_use_their_actual_phase() -> None:
    metrics = LLMUsageMetrics()
    metrics.start_run("phase-run", project_id="demo")
    provider = object()

    def get_provider(phase: str):
        metrics.set_phase(phase)
        return provider

    translator = FourStepTranslator(
        provider,
        LayeredContextManager(),
        get_provider_for_phase=get_provider,
    )
    section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[
            Paragraph(
                id="p1",
                index=0,
                source="Source",
                status=ParagraphStatus.PENDING,
            )
        ],
    )
    understanding = SectionUnderstanding(
        role_in_article="body",
        relation_to_previous="",
        relation_to_next="",
        key_points=[],
        translation_notes=[],
    )
    translator._step_understand = lambda *_args, **_kwargs: understanding

    def draft(*_args, **_kwargs):
        metrics.record_call(
            provider="fake",
            model="draft",
            duration_seconds=0,
            success=True,
        )
        return [TranslationPayload(text="初译")]

    def reflect(*_args, **_kwargs):
        metrics.record_call(
            provider="fake",
            model="refine",
            duration_seconds=0,
            success=True,
        )
        return ReflectionResult(
            overall_score=9.5,
            terminology_score=9.5,
            accuracy_score=9.5,
            fluency_score=9.5,
            conciseness_score=9.5,
            consistency_score=9.5,
            logic_score=9.5,
            issues=[],
        )

    translator._translate_batch = draft
    translator._step_reflect = reflect

    result = translator.translate_section(section, [section])

    calls = metrics.summary("phase-run")["calls"]
    assert result.translations == ["初译"]
    assert [(call["model"], call["phase"]) for call in calls] == [
        ("draft", "phase1_draft"),
        ("refine", "phase2_refine"),
    ]
