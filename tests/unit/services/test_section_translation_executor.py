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
        save_section=lambda *_args, **_kwargs: None,
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
