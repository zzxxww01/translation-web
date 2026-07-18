from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.models import Paragraph, ProjectStatus, Section
from src.services.batch_translation_types import TranslationProgress
from src.services.section_translation_executor import SectionTranslationExecutor


@pytest.mark.asyncio
async def test_section_executor_skips_fully_translated_section() -> None:
    section = Section(
        section_id="s1",
        title="Done",
        paragraphs=[Paragraph(id="p1", index=0, source="hello", confirmed="你好")],
    )
    progress = TranslationProgress(total_sections=1, total_paragraphs=1, original_status=ProjectStatus.CREATED)
    executor = SectionTranslationExecutor(
        is_cancelled=lambda _project_id: False,
        touch_progress=lambda *args, **kwargs: None,
        build_section_prompt_context=lambda *args, **kwargs: {"ok": True},
        persist_section_artifact=lambda *args, **kwargs: None,
        run_section_prescan=_noop_prescan,
        count_translated_paragraphs=lambda _section: 1,
        translate_section_batch=lambda **kwargs: ["不会执行"],
        apply_section_batch_translations=lambda _section, translations: translations,
        record_section_batch_term_usage=lambda *_args, **_kwargs: None,
        four_step_translate_section=lambda **kwargs: None,
        create_section_callback=lambda *args, **kwargs: None,
        apply_four_step_translations=lambda *_args, **_kwargs: None,
        merge_translation_updates=lambda *_args, **_kwargs: (
            section,
            [],
            [],
        ),
    )

    result = await executor.translate(
        project_id="demo",
        section=section,
        section_index=0,
        total_sections=1,
        all_sections=[section],
        analysis=SimpleNamespace(),
        run_dir=Path("."),
        progress=progress,
        on_progress=None,
        on_term_conflict=None,
        project=SimpleNamespace(),
        total_paragraphs=1,
        translation_mode="section",
        translation_mode_section="section",
    )

    assert result["skipped"] is True
    assert result["translations"] == ["你好"]


async def _noop_prescan(*args, **kwargs):
    return None


@pytest.mark.asyncio
async def test_section_executor_filters_structured_metadata_from_automatic_translation() -> None:
    metadata = Paragraph(
        id="p0",
        index=0,
        source="By Jane Doe, and 2 others",
        is_metadata=True,
        metadata_type="byline",
        confirmed="作者：Jane Doe 等 3 人",
    )
    body = Paragraph(id="p1", index=1, source="Claude Code changes workflows")
    section = Section(
        section_id="s1",
        title="Intro",
        paragraphs=[metadata, body],
    )
    progress = TranslationProgress(total_sections=1, total_paragraphs=2, original_status=ProjectStatus.CREATED)
    captured = {}

    async def fake_translate_section_batch(**kwargs):
        filtered_section = kwargs["section"]
        captured["translated_ids"] = [paragraph.id for paragraph in filtered_section.paragraphs]
        return [{"id": "p1", "translation": "Claude Code 改变了工作流"}]

    executor = SectionTranslationExecutor(
        is_cancelled=lambda _project_id: False,
        touch_progress=lambda *args, **kwargs: None,
        build_section_prompt_context=lambda *args, **kwargs: {"ok": True},
        persist_section_artifact=lambda *args, **kwargs: None,
        run_section_prescan=_noop_prescan,
        count_translated_paragraphs=lambda section_: sum(
            1 for paragraph in section_.paragraphs if paragraph.has_usable_translation()
        ),
        translate_section_batch=fake_translate_section_batch,
        apply_section_batch_translations=lambda filtered_section, translations: [
            translations[0]["translation"]
        ],
        record_section_batch_term_usage=lambda *_args, **_kwargs: None,
        four_step_translate_section=lambda **kwargs: None,
        create_section_callback=lambda *args, **kwargs: None,
        apply_four_step_translations=lambda *_args, **_kwargs: None,
        merge_translation_updates=lambda *_args, **_kwargs: (
            section,
            ["p1"],
            [],
        ),
    )

    result = await executor.translate(
        project_id="demo",
        section=section,
        section_index=0,
        total_sections=1,
        all_sections=[section],
        analysis=SimpleNamespace(),
        run_dir=Path("."),
        progress=progress,
        on_progress=None,
        on_term_conflict=None,
        project=SimpleNamespace(),
        total_paragraphs=2,
        translation_mode="section",
        translation_mode_section="section",
    )

    assert captured["translated_ids"] == ["p1"]
    assert result["paragraph_count"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("conflict_ids", "should_commit"),
    [(["p1"], False), ([], True)],
)
async def test_four_step_feedback_is_committed_only_after_full_merge_success(
    conflict_ids,
    should_commit,
) -> None:
    section = Section(
        section_id="s1",
        title="Intro",
        paragraphs=[Paragraph(id="p1", index=0, source="Source")],
    )
    persisted = section.model_copy(deep=True)
    persisted.paragraphs[0].add_translation(
        "人工译文" if conflict_ids else "AI 译文",
        "manual" if conflict_ids else "pro",
    )
    progress = TranslationProgress(
        total_sections=1,
        total_paragraphs=1,
        original_status=ProjectStatus.CREATED,
    )
    committed = []
    result_model = SimpleNamespace(
        translations=["AI 译文"],
        draft_translations=["AI 译文"],
        revised_translations=[],
        understanding=None,
        reflection=SimpleNamespace(),
        assessment=None,
        revision_attempted=False,
    )

    def apply_result(translatable_section, _result):
        translatable_section.paragraphs[0].add_translation("AI 译文", "pro")

    executor = SectionTranslationExecutor(
        is_cancelled=lambda _project_id: False,
        touch_progress=lambda *args, **kwargs: None,
        build_section_prompt_context=lambda *args, **kwargs: {"ok": True},
        persist_section_artifact=lambda *args, **kwargs: None,
        run_section_prescan=lambda *args, **kwargs: pytest.fail(
            "prescan barrier must prevent a second prescan"
        ),
        count_translated_paragraphs=lambda section_: sum(
            1
            for paragraph in section_.paragraphs
            if paragraph.has_usable_translation()
        ),
        translate_section_batch=lambda **kwargs: [],
        apply_section_batch_translations=lambda *_args, **_kwargs: None,
        record_section_batch_term_usage=lambda *_args, **_kwargs: None,
        four_step_translate_section=lambda **kwargs: result_model,
        create_section_callback=lambda *args, **kwargs: None,
        apply_four_step_translations=apply_result,
        merge_translation_updates=lambda *_args, **_kwargs: (
            persisted,
            [] if conflict_ids else ["p1"],
            conflict_ids,
        ),
        commit_four_step_result=committed.append,
    )

    result = await executor.translate(
        project_id="demo",
        section=section,
        section_index=0,
        total_sections=1,
        all_sections=[section],
        analysis=SimpleNamespace(),
        run_dir=Path("."),
        progress=progress,
        on_progress=None,
        on_term_conflict=None,
        project=SimpleNamespace(),
        total_paragraphs=1,
        translation_mode="four_step",
        translation_mode_section="section",
        prescan_completed=True,
    )

    assert result["conflict_paragraph_ids"] == conflict_ids
    assert committed == ([result_model] if should_commit else [])
