import asyncio
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
        merge_translation_updates: Callable[..., tuple[Section, list[str], list[str]]],
        commit_four_step_result: Optional[Callable[[Any], None]] = None,
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
        self._merge_translation_updates = merge_translation_updates
        self._commit_four_step_result = commit_four_step_result

    async def prescan(
        self,
        *,
        project_id: str,
        section: Section,
        run_dir: Path,
        progress: TranslationProgress,
        on_term_conflict: Optional[
            Callable[[TermConflict], Awaitable[dict[str, Any]]]
        ],
    ) -> Optional[Any]:
        """Prescan one translatable section without starting its translation."""
        if self._is_cancelled(project_id):
            return None

        translatable_section = self._build_translatable_section(section)
        if not translatable_section.paragraphs:
            return None

        prescan_result = await self._run_section_prescan(
            project_id,
            translatable_section,
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
        return prescan_result

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
        prescan_completed: bool = False,
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
                    "translations": [
                        paragraph.best_translation_text(fallback_to_source=False)
                        for paragraph in section.paragraphs
                    ],
                    "paragraph_count": section_paragraph_count,
                    "translated_before": translated_in_section,
                    "translated_after": translated_in_section,
                    "conflict_paragraph_ids": [],
                }
            expected_paragraphs = {
                paragraph.id: paragraph.model_copy(deep=True)
                for paragraph in translatable_section.paragraphs
            }

            if not prescan_completed:
                prescan_result = await self._run_section_prescan(
                    project_id,
                    translatable_section,
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

            four_step_result = None
            if translation_mode == translation_mode_section:
                translations = await self._translate_section_batch(
                    section=translatable_section,
                    section_index=section_index,
                    total_sections=total_sections,
                    all_sections=all_sections,
                    analysis=analysis,
                )
                self._apply_section_batch_translations(
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
                # 四步法内部仍是同步批调用；卸载到线程池以保持事件循环可响应取消和查询。
                four_step_result = await asyncio.to_thread(
                    self._four_step_translate_section,
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
                self._apply_four_step_translations(
                    translatable_section,
                    four_step_result,
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-draft",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "mode": translation_mode,
                        "prompt_context": section_prompt_context,
                        "understanding": four_step_result.understanding,
                        "translations": four_step_result.draft_translations,
                    },
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-critique",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "reflection": four_step_result.reflection,
                    },
                )
                if four_step_result.revision_attempted:
                    self._persist_section_artifact(
                        run_dir,
                        "section-revision",
                        section.section_id,
                        {
                            "section_id": section.section_id,
                            "assessment": four_step_result.assessment,
                            "translations": four_step_result.revised_translations,
                            "revision_attempted": True,
                        },
                    )

            persisted_section, applied_ids, conflict_ids = (
                self._merge_translation_updates(
                    project_id,
                    section.section_id,
                    translatable_section.paragraphs,
                    expected_paragraphs,
                    recompute_progress=False,
                )
            )
            applied_id_set = set(applied_ids)
            applied_translations = [
                paragraph.best_translation_text(fallback_to_source=False)
                for paragraph in persisted_section.paragraphs
                if paragraph.id in applied_id_set
            ]
            if (
                four_step_result is not None
                and applied_ids
                and not conflict_ids
                and self._commit_four_step_result is not None
            ):
                self._commit_four_step_result(four_step_result)
            self._touch_progress(
                progress,
                step=f"完成: {section.title}",
                current_section=section.section_id,
            )
            return {
                "section_id": section.section_id,
                "translations": [
                    paragraph.best_translation_text(fallback_to_source=False)
                    for paragraph in persisted_section.paragraphs
                ],
                "updated_translations": applied_translations,
                "paragraph_count": section_paragraph_count,
                "translated_before": translated_in_section,
                "translated_after": self._count_translated_paragraphs(
                    persisted_section
                ),
                "applied_paragraph_ids": applied_ids,
                "conflict_paragraph_ids": conflict_ids,
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
        """Filter out structured metadata paragraphs and already translated paragraphs from automatic body translation."""
        return section.model_copy(
            update={
                "paragraphs": [
                    paragraph
                    for paragraph in section.paragraphs
                    if not is_structured_metadata_paragraph(paragraph)
                    and not paragraph.has_usable_translation()
                ]
            }
        )
