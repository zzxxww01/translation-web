from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from src.core.models import ArticleAnalysis, ProjectMeta, Section, TermConflict
from src.core.structured_metadata import is_structured_metadata_paragraph
from src.services.batch_translation_types import TranslationProgress


class SectionTranslationExecutor:
    """Own section-level orchestration so batch service can focus on run lifecycle."""

    def __init__(
        self,
        *,
        is_cancelled: Callable[[str], bool],
        touch_progress: Callable[..., None],
        build_section_prompt_context: Callable[..., dict[str, Any]],
        persist_section_artifact: Callable[[Path, str, str, Any], None],
        run_section_prescan: Callable[..., Awaitable[Optional[Any]]],
        count_translated_paragraphs: Callable[[Section], int],
        translate_section_batch: Callable[..., Awaitable[list[str]]],
        apply_section_batch_translations: Callable[[Section, list[str]], list[str]],
        record_section_batch_term_usage: Callable[[Section, ArticleAnalysis], None],
        four_step_translate_section: Callable[..., Any],
        create_section_callback: Callable[..., Callable[[str, int, int], None]],
        apply_four_step_translations: Callable[[Section, Any], None],
        save_section: Callable[[str, Section], None],
    ) -> None:
        self._is_cancelled = is_cancelled
        self._touch_progress = touch_progress
        self._build_section_prompt_context = build_section_prompt_context
        self._persist_section_artifact = persist_section_artifact
        self._run_section_prescan = run_section_prescan
        self._count_translated_paragraphs = count_translated_paragraphs
        self._translate_section_batch = translate_section_batch
        self._apply_section_batch_translations = apply_section_batch_translations
        self._record_section_batch_term_usage = record_section_batch_term_usage
        self._four_step_translate_section = four_step_translate_section
        self._create_section_callback = create_section_callback
        self._apply_four_step_translations = apply_four_step_translations
        self._save_section = save_section

    async def translate(
        self,
        *,
        project_id: str,
        section: Section,
        section_index: int,
        total_sections: int,
        all_sections: list[Section],
        analysis: ArticleAnalysis,
        run_dir: Path,
        progress: TranslationProgress,
        on_progress: Optional[Callable[[str, int, int], None]],
        on_term_conflict: Optional[Callable[[TermConflict], Awaitable[dict[str, Any]]]],
        project: ProjectMeta,
        total_paragraphs: int,
        translation_mode: str,
        translation_mode_section: str,
    ) -> dict[str, Any]:
        try:
            if self._is_cancelled(project_id):
                return {"section_id": section.section_id, "cancelled": True}

            self._touch_progress(
                progress,
                step=f"处理中: {section.title}",
                current_section=section.section_id,
            )

            section_prompt_context = self._build_section_prompt_context(
                project,
                section,
                section_index,
                analysis,
            )
            self._persist_section_artifact(
                run_dir,
                "section-context",
                section.section_id,
                section_prompt_context,
            )

            prescan_result = await self._run_section_prescan(
                project_id,
                self._build_translatable_section(section),
                progress,
                on_term_conflict=on_term_conflict,
            )
            if prescan_result:
                self._persist_section_artifact(
                    run_dir,
                    "section-prescan",
                    section.section_id,
                    prescan_result,
                )

            section_paragraph_count = len(section.paragraphs)
            translated_in_section = self._count_translated_paragraphs(section)
            if translated_in_section == section_paragraph_count and section_paragraph_count > 0:
                return {
                    "section_id": section.section_id,
                    "skipped": True,
                    "translations": [
                        paragraph.best_translation_text(fallback_to_source=False)
                        for paragraph in section.paragraphs
                    ],
                    "paragraph_count": section_paragraph_count,
                }

            translatable_section = self._build_translatable_section(section)
            if not translatable_section.paragraphs:
                return {
                    "section_id": section.section_id,
                    "translations": [],
                    "paragraph_count": section_paragraph_count,
                    "translated_before": translated_in_section,
                }

            if translation_mode == translation_mode_section:
                translations = await self._translate_section_batch(
                    section=translatable_section,
                    section_index=section_index,
                    total_sections=total_sections,
                    all_sections=all_sections,
                    analysis=analysis,
                )
                collected_translations = self._apply_section_batch_translations(
                    translatable_section,
                    translations,
                )
                self._record_section_batch_term_usage(translatable_section, analysis)
                self._persist_section_artifact(
                    run_dir,
                    "section-draft",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "mode": translation_mode,
                        "prompt_context": section_prompt_context,
                        "translations": translations,
                    },
                )
            else:
                result = self._four_step_translate_section(
                    section=translatable_section,
                    all_sections=all_sections,
                    project_id=project_id,
                    on_progress=self._create_section_callback(
                        section.title,
                        on_progress,
                        translated_in_section,
                        total_paragraphs,
                        max(section_paragraph_count - translated_in_section, 0),
                    ),
                )
                self._apply_four_step_translations(translatable_section, result)
                collected_translations = result.translations
                self._persist_section_artifact(
                    run_dir,
                    "section-draft",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "mode": translation_mode,
                        "prompt_context": section_prompt_context,
                        "understanding": result.understanding,
                        "translations": result.draft_translations,
                    },
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-critique",
                    section.section_id,
                    {"section_id": section.section_id, "reflection": result.reflection},
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-revision",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "assessment": result.assessment,
                        "translations": result.revised_translations,
                    },
                )

            self._save_section(project_id, section)
            self._touch_progress(
                progress,
                step=f"完成: {section.title}",
                current_section=section.section_id,
            )
            return {
                "section_id": section.section_id,
                "translations": collected_translations,
                "paragraph_count": section_paragraph_count,
                "translated_before": translated_in_section,
            }
        except Exception as error:
            error_msg = f"Failed to translate section {section.section_id}: {str(error)}"
            self._touch_progress(
                progress,
                step=error_msg,
                current_section=section.section_id,
            )
            return {
                "section_id": section.section_id,
                "error": error_msg,
                "exception": error,
            }

    @staticmethod
    def _build_translatable_section(section: Section) -> Section:
        """Filter out structured metadata paragraphs from automatic body translation."""
        return section.model_copy(
            update={
                "paragraphs": [
                    paragraph
                    for paragraph in section.paragraphs
                    if not is_structured_metadata_paragraph(paragraph)
                ]
            }
        )
