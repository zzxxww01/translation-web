from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agents.context_manager import LayeredContextManager
from src.core.models import (
    ArticleAnalysis,
    ArticleStyle,
    EnhancedTerm,
    Paragraph,
    ProjectStatus,
    Section,
    TranslationStrategy,
)
from src.services.batch_translation_service import BatchTranslationService
from src.services.batch_translation_types import TranslationProgress


class _ProjectManager:
    def __init__(self, sections):
        self.sections = [section.model_copy(deep=True) for section in sections]

    def get_sections(self, _project_id):
        return [section.model_copy(deep=True) for section in self.sections]


class _PrescanRecorder:
    def __init__(self, events):
        self.events = events

    async def prescan(self, **kwargs):
        self.events.append(("prescan", kwargs["section"].section_id))


@pytest.mark.asyncio
async def test_sections_prescan_before_ordered_translation_and_rebuild_conflict_context(
    tmp_path,
) -> None:
    first = Section(
        section_id="s1",
        title="First",
        paragraphs=[Paragraph(id="p1", index=0, source="First token")],
    )
    second = Section(
        section_id="s2",
        title="Second",
        paragraphs=[Paragraph(id="p2", index=0, source="Second")],
    )
    future = Section(
        section_id="s3",
        title="Future",
        paragraphs=[Paragraph(id="p3", index=0, source="Future token")],
    )
    future.paragraphs[0].add_translation("未来 token 译文", "manual")

    analysis = ArticleAnalysis(
        theme="theme",
        structure_summary="structure",
        style=ArticleStyle(
            tone="professional",
            target_audience="engineers",
            translation_voice="technical",
        ),
        terminology=[
            EnhancedTerm(
                term="token",
                translation="token",
                strategy=TranslationStrategy.FIRST_ANNOTATE,
            )
        ],
    )
    context_manager = LayeredContextManager()
    context_manager.set_article_analysis(analysis)
    project_manager = _ProjectManager([first, second, future])
    events = []

    service = BatchTranslationService.__new__(BatchTranslationService)
    service.context_manager = context_manager
    service.project_manager = project_manager
    service._section_executor = _PrescanRecorder(events)
    service._is_cancelled = lambda _project_id: False

    async def translate_single_section(**kwargs):
        section_id = kwargs["section"].section_id
        events.append(("translate", section_id))
        assert kwargs["prescan_completed"] is True

        if section_id == "s1":
            # Simulate four-step draft state written before an optimistic merge
            # loses to a manual edit.
            context_manager.record_translation(
                "s1",
                "First token",
                "过期 AI 草稿",
                {"token": "token"},
            )
            manual = project_manager.sections[0].model_copy(deep=True)
            manual.paragraphs[0].add_translation("人工 token 译文", "manual")
            project_manager.sections[0] = manual
            return {
                "section_id": "s1",
                "conflict_paragraph_ids": ["p1"],
            }

        if section_id == "s2":
            assert context_manager.get_section_translations("s1") == [
                ("First token", "人工 token 译文")
            ]
            assert "过期 AI 草稿" not in str(
                context_manager.get_all_translations()
            )
            return {
                "section_id": "s2",
                "conflict_paragraph_ids": [],
            }

        return {
            "section_id": "s3",
            "conflict_paragraph_ids": [],
        }

    service._translate_single_section = translate_single_section
    project = SimpleNamespace(
        sections=project_manager.get_sections("demo"),
    )
    progress = TranslationProgress(
        total_sections=3,
        total_paragraphs=3,
        original_status=ProjectStatus.CREATED,
    )

    results = await service._translate_sections_in_document_order(
        project_id="demo",
        project=project,
        analysis=analysis,
        run_dir=Path(tmp_path),
        progress=progress,
        on_progress=None,
        on_term_conflict=None,
        total_paragraphs=3,
    )

    assert events == [
        ("prescan", "s1"),
        ("prescan", "s2"),
        ("prescan", "s3"),
        ("translate", "s1"),
        ("translate", "s2"),
        ("translate", "s3"),
    ]
    assert [result["section_id"] for result in results] == ["s1", "s2", "s3"]


def test_rebuild_context_uses_only_persisted_prefix() -> None:
    past = Section(
        section_id="past",
        title="Past",
        paragraphs=[Paragraph(id="p1", index=0, source="Past token")],
    )
    future = Section(
        section_id="future",
        title="Future",
        paragraphs=[Paragraph(id="p2", index=0, source="Future token")],
    )
    future.paragraphs[0].add_translation("未来 token 译文", "manual")
    analysis = ArticleAnalysis(
        theme="theme",
        structure_summary="structure",
        style=ArticleStyle(),
        terminology=[
            EnhancedTerm(
                term="token",
                translation="token",
                strategy=TranslationStrategy.FIRST_ANNOTATE,
            )
        ],
    )
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.context_manager = LayeredContextManager()
    service.context_manager.set_article_analysis(analysis)
    service.context_manager.record_translation(
        "future",
        "Future token",
        "未持久化污染",
        {"token": "token"},
    )

    service._rebuild_persisted_translation_context([past])

    assert service.context_manager.get_all_translations() == {}
    assert service.context_manager.has_term_usage("token") is False
