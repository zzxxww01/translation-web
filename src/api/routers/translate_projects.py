"""
Translate project-level endpoints.
"""

import asyncio
from datetime import datetime
import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from src.api.streaming.translation_stream_session import (
    TranslationStreamSession,
    resolve_live_conflict,
)
from src.agents.translation import TranslationAgent, TranslationContext
from src.core.format_tokens import apply_translation_payload
from src.core.models import ParagraphStatus
from src.core.project import ConcurrentParagraphUpdateError
from src.core.structured_metadata import is_structured_metadata_paragraph
from src.llm.usage_metrics import llm_usage_metrics
from src.services.source_metadata_service import SourceMetadataTranslationService
from src.services.translation_artifact_service import TranslationArtifactService
from src.services.translation_run_registry import translation_run_registry

from ..dependencies import AnalysisLLMProviderDep, GlossaryManagerDep, LongformLLMProviderDep, ProjectManagerDep
from ..middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
_normal_translation_tasks: set[asyncio.Task[Any]] = set()

from ..middleware import (
    BadRequestException,
    NotFoundException,
    ServiceUnavailableException,
)
from ..utils.json_utils import parse_llm_json_response
from .translate_models import (
    FullTranslateRequest,
    ProjectAnalysisResponse,
    ResolveConflictRequest,
    SectionAnalysisResponse,
)
from .translate_utils import validate_path_component


from src.config.timeout_config import TimeoutConfig

router = APIRouter()


def _get_best_translation_text(paragraph) -> str:
    return paragraph.best_translation_text()


def _build_translation_context(section, index: int, glossary):
    context = TranslationContext(glossary=glossary)
    prev_context = []

    for prev_para in section.paragraphs[max(0, index - 5) : index]:
        text = _get_best_translation_text(prev_para)
        if text:
            prev_context.append((prev_para.source, text))

    context.previous_paragraphs = prev_context
    context.next_preview = [
        next_para.source for next_para in section.paragraphs[index + 1 : index + 3]
    ]
    return context


@router.post("/projects/{project_id}/analyze", response_model=ProjectAnalysisResponse)
@limiter.limit("10/minute")
async def analyze_project(request: Request, project_id: str):
    """分析项目原文，生成摘要和翻译指南。"""
    from src.services.analysis_service import AnalysisService

    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    try:
        data = await asyncio.to_thread(AnalysisService().analyze_project, project_id)
        return ProjectAnalysisResponse(
            summary=data.get("summary", ""),
            notes=data.get("notes", []),
            key_terms=data.get("key_terms", []),
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Source file not found")
    except Exception as e:
        logger.error(f"Project analysis failed: {str(e)}")
        if os.getenv("DEBUG") == "true":
            raise ServiceUnavailableException(detail=f"分析失败: {str(e)}")
        raise ServiceUnavailableException(detail="分析失败，请稍后重试或联系支持")


@router.post(
    "/projects/{project_id}/sections/{section_id}/analyze",
    response_model=SectionAnalysisResponse,
)
@limiter.limit("10/minute")
async def analyze_section(request: Request, project_id: str, section_id: str):
    """分析章节内容，生成摘要和注意事项。"""
    from src.services.analysis_service import AnalysisService

    if not validate_path_component(project_id) or not validate_path_component(
        section_id
    ):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        data = await asyncio.to_thread(AnalysisService().analyze_section, project_id, section_id)
        return SectionAnalysisResponse(
            summary=data.get("summary", ""),
            tips=data.get("tips", []),
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Section source file not found")
    except Exception as e:
        logger.error(f"Section analysis failed: {str(e)}")
        if os.getenv("DEBUG") == "true":
            raise ServiceUnavailableException(detail=f"章节分析失败: {str(e)}")
        raise ServiceUnavailableException(detail="章节分析失败，请稍后重试或联系支持")


@router.post("/projects/{project_id}/sections/{section_id}/translate_all")
@limiter.limit("5/minute")
async def batch_translate_section(
    request: Request,
    project_id: str,
    section_id: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
):
    """批量翻译章节中所有非 APPROVED 状态段落。"""
    if not validate_path_component(project_id) or not validate_path_component(
        section_id
    ):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        section = await asyncio.to_thread(pm.get_section, project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        source_metadata_result = await asyncio.to_thread(
            SourceMetadataTranslationService(pm, llm).translate_project_sources,
            project_id,
            sections=[section],
        )
        section = await asyncio.to_thread(pm.get_section, project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        glossary = await asyncio.to_thread(gm.load_merged, project_id)
        timeout_s = TimeoutConfig.get_timeout("longform")
        agent = TranslationAgent(llm, timeout=timeout_s)
        translated_count = (
            source_metadata_result.get("translated", 0)
            + source_metadata_result.get("reused", 0)
        )
        metadata_conflict_ids = list(
            source_metadata_result.get("conflict_paragraph_ids", [])
        )
        conflict_ids = []
        paragraph_ids = [paragraph.id for paragraph in section.paragraphs]

        for paragraph_id in paragraph_ids:
            index = next(
                (
                    paragraph_index
                    for paragraph_index, candidate in enumerate(section.paragraphs)
                    if candidate.id == paragraph_id
                ),
                None,
            )
            if index is None:
                conflict_ids.append(paragraph_id)
                continue
            paragraph = section.paragraphs[index]
            if is_structured_metadata_paragraph(paragraph):
                continue
            if paragraph.status == ParagraphStatus.APPROVED:
                continue

            context = _build_translation_context(section, index, glossary)

            try:
                expected_paragraph = paragraph.model_copy(deep=True)
                payload = await asyncio.to_thread(agent.translate_paragraph, paragraph, context)
                generated_paragraph = paragraph.model_copy(deep=True)
                apply_translation_payload(generated_paragraph, payload, "pro")
                generated_paragraph.status = ParagraphStatus.TRANSLATED
                section, applied_ids, paragraph_conflict_ids = await asyncio.to_thread(
                    pm.merge_translation_updates_locked,
                    project_id,
                    section_id,
                    [generated_paragraph],
                    {paragraph.id: expected_paragraph},
                    recompute_progress=False,
                )
                translated_count += len(applied_ids)
                conflict_ids.extend(paragraph_conflict_ids)
                for conflict_id in paragraph_conflict_ids:
                    logger.info(
                        "Skipped stale translation for manually changed paragraph %s",
                        conflict_id,
                    )
            except Exception as e:
                logger.error(f"Error translating paragraph {paragraph.id}: {e}")
                try:
                    latest_section = await asyncio.to_thread(
                        pm.get_section,
                        project_id,
                        section_id,
                    )
                    if latest_section:
                        section = latest_section
                except Exception as reload_error:
                    logger.warning(
                        "Failed to reload section %s after paragraph error: %s",
                        section_id,
                        reload_error,
                    )
                continue

        await asyncio.to_thread(pm.update_progress, project_id)

        all_conflict_ids = [*metadata_conflict_ids, *conflict_ids]
        return {
            "message": "Batch translation complete",
            "translated_count": translated_count,
            "conflict_count": len(all_conflict_ids),
            "conflict_paragraph_ids": all_conflict_ids,
        }
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Batch translation failed: {str(e)}")
        if os.getenv("DEBUG") == "true":
            raise ServiceUnavailableException(detail=f"批量翻译失败: {str(e)}")
        raise ServiceUnavailableException(detail="批量翻译失败，请稍后重试或联系支持")


@router.post("/projects/{project_id}/translate-stream")
@limiter.limit("3/minute")
async def translate_full_document(
    request: Request,
    project_id: str,
    body: FullTranslateRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
):
    """
    全文一键翻译（SSE）。
    翻译项目中所有章节的所有段落。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    # 如果指定了模型，创建新的 provider
    if body.model:
        from src.api.utils.llm_factory import create_llm_provider
        llm = await asyncio.to_thread(
            create_llm_provider,
            provider=body.model,
        )

    from src.services.batch_translation_service import BatchTranslationService

    slot_claim = await BatchTranslationService.claim_translation_slot(project_id)
    if slot_claim["status"] == "busy":
        raise BadRequestException(
            detail=(
                "This project already has an active translation. "
                f"project_id={slot_claim.get('active_project_id')}, "
                f"active_run_id={slot_claim.get('active_run_id')}"
            )
        )
    lease_id = str(slot_claim["lease_id"])

    async def run_blocking_call(func, *args):
        task = asyncio.create_task(asyncio.to_thread(func, *args))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # The worker thread cannot be cancelled. Keep the project slot until
            # it finishes so a new run cannot overlap its writes.
            await asyncio.shield(task)
            raise

    class NormalTranslationCancelled(Exception):
        pass

    progress_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    client_attached = True

    async def emit(payload: Dict[str, Any]) -> None:
        if client_attached:
            await progress_queue.put(payload)

    async def run_translation_worker():
        artifact_service = TranslationArtifactService(pm.projects_path)
        progress_tracker = BatchTranslationService._shared_progress_tracker
        progress = None
        run_id = None
        run_dir = None
        total_paragraphs = 0
        processed_count = 0
        error_count = 0
        terminal_status = "failed"
        terminal_error = None
        terminal_event: Dict[str, Any] | None = None
        final_sections_snapshot = None
        last_progress_write = 0.0

        def check_cancelled() -> None:
            if translation_run_registry.is_cancelled(project_id):
                raise NormalTranslationCancelled("Translation cancelled by user")

        async def touch_progress(
            step: str,
            section_id: str | None = None,
            *,
            force: bool = False,
        ) -> None:
            nonlocal last_progress_write
            if progress is None or run_id is None:
                return
            progress.current_step = step
            if section_id is not None:
                progress.current_section = section_id
            progress_tracker.touch(progress)
            now = asyncio.get_running_loop().time()
            if not force and now - last_progress_write < 0.5:
                return
            last_progress_write = now
            try:
                await run_blocking_call(
                    artifact_service.write_run_state,
                    project_id,
                    run_id,
                    {
                        "status": progress.final_status or "processing",
                        **progress.to_dict(),
                    },
                )
            except Exception as exc:
                # Run-state snapshots are auxiliary. A transient artifact write
                # failure must not abort an otherwise valid translation.
                logger.warning(
                    "[%s] Failed to persist normal translation run state: %s",
                    project_id,
                    exc,
                )

        try:
            project, sections = await asyncio.gather(
                run_blocking_call(pm.get, project_id),
                run_blocking_call(pm.get_sections, project_id),
            )
            total_paragraphs = sum(len(section.paragraphs) for section in sections)
            progress = progress_tracker.create(
                project_id=project_id,
                total_sections=len(sections),
                total_paragraphs=total_paragraphs,
                original_status=project.status,
            )
            run_id, run_dir = await run_blocking_call(
                artifact_service.create_run_artifact_dir,
                project_id,
            )
            progress.run_id = run_id
            llm_usage_metrics.start_run(run_id, project_id=project_id)
            llm_usage_metrics.set_phase("normal_translate")
            BatchTranslationService._set_active_run(
                project_id,
                run_id=run_id,
                status="processing",
            )
            await touch_progress("准备全文翻译", force=True)

            await emit({"type": "start", "total": total_paragraphs})

            if not sections:
                raise RuntimeError("No sections found")

            check_cancelled()
            llm_usage_metrics.set_phase("source_metadata")
            await touch_progress("翻译来源说明", force=True)
            await run_blocking_call(
                SourceMetadataTranslationService(pm, llm).translate_project_sources,
                project_id,
                sections,
                run_dir,
            )
            check_cancelled()

            sections = await run_blocking_call(pm.get_sections, project_id)
            progress.translated_paragraphs = sum(
                1
                for section in sections
                for paragraph in section.paragraphs
                if paragraph.has_usable_translation()
            )
            glossary = await run_blocking_call(gm.load_merged, project_id)
            timeout_s = TimeoutConfig.get_timeout("longform")
            agent = TranslationAgent(llm, timeout=timeout_s)
            llm_usage_metrics.set_phase("normal_translate")

            for section in sections:
                check_cancelled()
                section_full = await run_blocking_call(
                    pm.get_section,
                    project_id,
                    section.section_id,
                )
                if not section_full:
                    continue
                await touch_progress("翻译段落", section.section_id)

                paragraph_ids = [
                    paragraph.id for paragraph in section_full.paragraphs
                ]
                for paragraph_id in paragraph_ids:
                    check_cancelled()
                    index = next(
                        (
                            paragraph_index
                            for paragraph_index, candidate in enumerate(
                                section_full.paragraphs
                            )
                            if candidate.id == paragraph_id
                        ),
                        None,
                    )
                    if index is None:
                        continue
                    paragraph = section_full.paragraphs[index]
                    if (
                        is_structured_metadata_paragraph(paragraph)
                        or paragraph.has_usable_translation()
                    ):
                        processed_count += 1
                        await touch_progress("跳过已有译文", section.section_id)
                        await emit(
                            {
                                "type": "skip",
                                "paragraph_id": paragraph.id,
                                "section_id": section.section_id,
                                "current": processed_count,
                                "total": total_paragraphs,
                            }
                        )
                        continue

                    context = _build_translation_context(section_full, index, glossary)
                    try:
                        expected_paragraph = paragraph.model_copy(deep=True)
                        payload = await run_blocking_call(
                            agent.translate_paragraph,
                            paragraph,
                            context,
                        )
                        check_cancelled()
                        generated_paragraph = paragraph.model_copy(deep=True)
                        apply_translation_payload(
                            generated_paragraph,
                            payload,
                            "default",
                        )
                        generated_paragraph.status = ParagraphStatus.TRANSLATED
                        section_full, applied_ids, conflict_ids = await run_blocking_call(
                            lambda: pm.merge_translation_updates_locked(
                                project_id,
                                section.section_id,
                                [generated_paragraph],
                                {paragraph.id: expected_paragraph},
                                recompute_progress=False,
                            )
                        )
                        if conflict_ids or not applied_ids:
                            raise ConcurrentParagraphUpdateError(paragraph.id)
                        processed_count += 1
                        progress.translated_paragraphs += 1
                        await touch_progress("翻译段落", section.section_id)
                        await emit(
                            {
                                "type": "translated",
                                "paragraph_id": paragraph.id,
                                "section_id": section.section_id,
                                "translation": payload.text,
                                "current": processed_count,
                                "total": total_paragraphs,
                            }
                        )
                    except NormalTranslationCancelled:
                        raise
                    except Exception as exc:
                        try:
                            latest_section = await run_blocking_call(
                                pm.get_section,
                                project_id,
                                section.section_id,
                            )
                            if latest_section:
                                section_full = latest_section
                        except Exception as reload_error:
                            logger.warning(
                                "Failed to reload section %s after paragraph error: %s",
                                section.section_id,
                                reload_error,
                            )
                        processed_count += 1
                        error_count += 1
                        progress_tracker.record_error(
                            progress,
                            str(exc),
                            section.section_id,
                        )
                        await touch_progress(
                            "段落翻译失败",
                            section.section_id,
                            force=True,
                        )
                        await emit(
                            {
                                "type": "error",
                                "paragraph_id": paragraph.id,
                                "section_id": section.section_id,
                                "error": str(exc),
                                "current": processed_count,
                                "total": total_paragraphs,
                            }
                        )
                        continue

            await run_blocking_call(pm.update_progress, project_id)
            final_sections = await run_blocking_call(pm.get_sections, project_id)
            final_sections_snapshot = final_sections
            actual_translated = sum(
                1
                for section in final_sections
                for paragraph in section.paragraphs
                if paragraph.has_usable_translation()
            )
            progress.translated_paragraphs = actual_translated
            terminal_status = (
                "completed"
                if error_count == 0 and actual_translated >= total_paragraphs
                else "incomplete"
            )

            if terminal_status == "incomplete":
                terminal_event = {
                    "type": "incomplete",
                    "current": processed_count,
                    "total": total_paragraphs,
                    "translated_count": actual_translated,
                    "error_count": error_count,
                    "message": (
                        f"Translation incomplete: "
                        f"{actual_translated}/{total_paragraphs} paragraphs usable"
                    ),
                }
            else:
                terminal_event = {
                    "type": "complete",
                    "translated_count": actual_translated,
                    "total": total_paragraphs,
                }
        except NormalTranslationCancelled as exc:
            terminal_status = "cancelled"
            terminal_error = str(exc)
            terminal_event = {
                "type": "cancelled",
                "translated_count": (
                    progress.translated_paragraphs if progress else 0
                ),
                "total": total_paragraphs,
                "message": terminal_error,
            }
        except asyncio.CancelledError:
            terminal_status = "cancelled"
            terminal_error = "Translation worker stopped"
            raise
        except Exception as exc:
            terminal_status = "failed"
            terminal_error = str(exc)
            if progress is not None:
                progress_tracker.record_error(progress, terminal_error)
            terminal_event = {"type": "error", "error": terminal_error}
        finally:
            try:
                if progress is not None and run_id is not None and run_dir is not None:
                    try:
                        if final_sections_snapshot is None:
                            await run_blocking_call(pm.update_progress, project_id)
                            final_sections_snapshot = await run_blocking_call(
                                pm.get_sections,
                                project_id,
                            )
                        final_sections = final_sections_snapshot
                        progress.translated_paragraphs = sum(
                            1
                            for section in final_sections
                            for paragraph in section.paragraphs
                            if paragraph.has_usable_translation()
                        )
                        progress.translated_sections = sum(
                            1
                            for section in final_sections
                            if section.paragraphs
                            and all(
                                paragraph.has_usable_translation()
                                for paragraph in section.paragraphs
                            )
                        )
                    except Exception as exc:
                        progress_tracker.record_error(progress, str(exc))

                    progress.finished_at = datetime.now()
                    progress.final_status = terminal_status
                    await touch_progress(terminal_status, force=True)
                    usage_summary = llm_usage_metrics.finish_run(run_id)
                    summary = {
                        "project_id": project_id,
                        "status": terminal_status,
                        "total_sections": progress.total_sections,
                        "translated_sections": progress.translated_sections,
                        "total_paragraphs": progress.total_paragraphs,
                        "translated_paragraphs": progress.translated_paragraphs,
                        "error_count": len(progress.errors),
                        "errors": progress.errors,
                        "error": terminal_error,
                        "started_at": progress.started_at.isoformat(),
                        "finished_at": progress.finished_at.isoformat(),
                        "run_id": run_id,
                        "artifacts_path": str(run_dir),
                        "api_calls": usage_summary["api_calls"],
                        "llm_usage": usage_summary,
                    }
                    try:
                        await run_blocking_call(
                            artifact_service.write_json,
                            run_dir / "run-summary.json",
                            summary,
                        )
                    except Exception as exc:
                        logger.warning(
                            "[%s] Failed to persist normal translation summary: %s",
                            project_id,
                            exc,
                        )
            finally:
                translation_run_registry.clear_cancelled(project_id)
                BatchTranslationService._release_active_run(
                    project_id,
                    lease_id=lease_id,
                )

        if terminal_event is not None:
            await emit(terminal_event)

    async def generate_progress():
        nonlocal client_attached
        worker_task = asyncio.create_task(run_translation_worker())
        _normal_translation_tasks.add(worker_task)
        worker_task.add_done_callback(_normal_translation_tasks.discard)
        terminal_types = {"complete", "incomplete", "cancelled"}

        try:
            while True:
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if worker_task.done():
                        if not worker_task.cancelled():
                            worker_error = worker_task.exception()
                            if worker_error is not None:
                                yield (
                                    "data: "
                                    + json.dumps(
                                        {"type": "error", "error": str(worker_error)}
                                    )
                                    + "\n\n"
                                )
                        break
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                yield f"data: {json.dumps(event)}\n\n"
                if (
                    event.get("type") in terminal_types
                    or (
                        event.get("type") == "error"
                        and not event.get("paragraph_id")
                    )
                ):
                    break
        except asyncio.CancelledError:
            logger.info(
                "[%s] Normal SSE client detached; translation continues in background",
                project_id,
            )
            raise
        finally:
            client_attached = False
            if not worker_task.done():
                logger.info(
                    "[%s] Normal SSE stream closed before background translation finished",
                    project_id,
                )

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/projects/{project_id}/translate-four-step")
@limiter.limit("3/minute")
async def translate_with_four_steps(
    request: Request,
    project_id: str,
    pm: ProjectManagerDep,
    llm: LongformLLMProviderDep,
    analysis_llm: AnalysisLLMProviderDep,
    _body: FullTranslateRequest = Body(default_factory=FullTranslateRequest),
):
    """
    使用四步法翻译整个项目（优化版）。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    # 如果指定了模型，创建新的 provider
    if _body.model:
        from src.api.utils.llm_factory import create_llm_provider
        llm = await asyncio.to_thread(
            create_llm_provider,
            provider=_body.model,
        )
        analysis_llm = llm

    from src.services.batch_translation_service import BatchTranslationService

    slot_claim = await BatchTranslationService.claim_translation_slot(project_id)
    if slot_claim["status"] == "busy":
        raise BadRequestException(
            detail=(
                "This project already has an active translation. "
                f"project_id={slot_claim.get('active_project_id')}, "
                f"active_run_id={slot_claim.get('active_run_id')}"
            )
        )
    lease_id = str(slot_claim["lease_id"])

    try:
        sections = await asyncio.to_thread(pm.get_sections, project_id)
        total_paragraphs = (
            sum(len(section.paragraphs) for section in sections) if sections else 0
        )
        total_sections = len(sections) if sections else 0

        # 创建BatchTranslationService实例，传递用户模型覆盖
        batch_service = BatchTranslationService(
            llm_provider=llm,
            project_manager=pm,
            translation_mode=BatchTranslationService.TRANSLATION_MODE_FOUR_STEP,
            max_concurrent_sections=10,  # 并发翻译10个章节（VectorEngine支持100并发）
            analysis_llm_provider=analysis_llm,
            user_model_override=_body.model,  # 传递用户指定的模型
        )
    except Exception:
        BatchTranslationService._release_active_run(
            project_id,
            lease_id=lease_id,
        )
        raise
    async def run_translation(
        on_progress,
        on_term_conflict,
    ) -> Dict[str, Any]:
        def _run_translation_in_thread() -> Dict[str, Any]:
            async def _runner() -> Dict[str, Any]:
                return await batch_service.translate_project(
                    project_id,
                    on_progress=on_progress,
                    on_term_conflict=on_term_conflict,
                )

            return asyncio.run(_runner())

        return await asyncio.to_thread(_run_translation_in_thread)

    session = TranslationStreamSession(
        project_id=project_id,
        request=request,
        total_paragraphs=total_paragraphs,
        total_sections=total_sections,
        run_translation=run_translation,
        cancel_translation=batch_service.cancel_translation,
        release_slot=lambda pid: BatchTranslationService._release_active_run(
            pid,
            lease_id=lease_id,
        ),
    )

    return StreamingResponse(
        session.generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/projects/{project_id}/resolve-conflict-live")
async def resolve_term_conflict_live(
    project_id: str,
    request: ResolveConflictRequest,
):
    """
    实时解决翻译过程中的术语冲突（配合四步法 SSE 使用）。
    前端收到 term_conflict SSE 事件后，通过此端点返回用户选择。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    resolved = resolve_live_conflict(
        project_id,
        request.term,
        request.chosen_translation,
        request.apply_to_all,
    )

    return {
        "status": "resolved" if resolved else "accepted",
        "term": request.term,
        "chosen": request.chosen_translation,
    }


@router.post("/projects/{project_id}/translate-four-step/stop")
async def stop_translate_with_four_steps(project_id: str):
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    from src.services.batch_translation_service import BatchTranslationService

    service = BatchTranslationService.__new__(BatchTranslationService)
    result = await service.cancel_translation(project_id)
    if result.get("status") == "not_found":
        raise BadRequestException(detail="No active longform translation for this project")
    return result
