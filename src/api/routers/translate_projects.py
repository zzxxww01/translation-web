"""
Translate project-level endpoints.
"""

import asyncio
import json
import logging
import threading
from typing import Any, Dict

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.format_tokens import apply_translation_payload
from src.core.models import ParagraphStatus
from src.services.source_metadata_service import SourceMetadataTranslationService

from ..dependencies import AnalysisLLMProviderDep, GlossaryManagerDep, LongformLLMProviderDep, ProjectManagerDep

logger = logging.getLogger(__name__)

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

# 活跃的四步法翻译会话冲突状态 {project_id: {term: Event}}
# 使用线程锁保护全局状态
_conflict_lock = threading.Lock()
_pending_conflict_events: Dict[str, Dict[str, asyncio.Event]] = {}
_conflict_resolutions: Dict[str, Dict[str, Dict[str, Any]]] = {}


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
async def analyze_project(project_id: str):
    """分析项目原文，生成摘要和翻译指南。"""
    from src.services.analysis_service import AnalysisService

    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    try:
        data = AnalysisService().analyze_project(project_id)
        return ProjectAnalysisResponse(
            summary=data.get("summary", ""),
            notes=data.get("notes", []),
            key_terms=data.get("key_terms", []),
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Source file not found")
    except Exception as e:
        raise ServiceUnavailableException(detail=f"分析失败: {str(e)}")


@router.post(
    "/projects/{project_id}/sections/{section_id}/analyze",
    response_model=SectionAnalysisResponse,
)
async def analyze_section(project_id: str, section_id: str):
    """分析章节内容，生成摘要和注意事项。"""
    from src.services.analysis_service import AnalysisService

    if not validate_path_component(project_id) or not validate_path_component(
        section_id
    ):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        data = AnalysisService().analyze_section(project_id, section_id)
        return SectionAnalysisResponse(
            summary=data.get("summary", ""),
            tips=data.get("tips", []),
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Section source file not found")
    except Exception as e:
        raise ServiceUnavailableException(detail=f"章节分析失败: {str(e)}")


@router.post("/projects/{project_id}/sections/{section_id}/translate_all")
async def batch_translate_section(
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
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        source_metadata_result = SourceMetadataTranslationService(pm, llm).translate_project_sources(
            project_id,
            sections=[section],
        )

        glossary = gm.load_merged(project_id)
        timeout_s = TimeoutConfig.get_timeout("longform")
        agent = TranslationAgent(llm, timeout=timeout_s)
        translated_count = source_metadata_result.get("translated", 0)

        for index, paragraph in enumerate(section.paragraphs):
            if paragraph.status == ParagraphStatus.APPROVED:
                continue

            context = _build_translation_context(section, index, glossary)

            try:
                payload = agent.translate_paragraph(paragraph, context)
                apply_translation_payload(paragraph, payload, "pro")
                translated_count += 1
            except Exception as e:
                logger.error(f"Error translating paragraph {paragraph.id}: {e}")
                continue

        # 循环结束后统一保存，减少磁盘 IO
        pm.save_section(project_id, section)

        return {
            "message": "Batch translation complete",
            "translated_count": translated_count,
        }
    except NotFoundException:
        raise
    except Exception as e:
        raise ServiceUnavailableException(detail=f"批量翻译失败: {str(e)}")


@router.post("/projects/{project_id}/translate-stream")
async def translate_full_document(
    project_id: str,
    request: FullTranslateRequest,
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
    if request.model:
        from src.api.utils.llm_factory import create_llm_provider
        llm = create_llm_provider(provider=request.model)

    async def generate_progress():
        try:
            sections = pm.get_sections(project_id)
            if not sections:
                yield f"data: {json.dumps({'error': 'No sections found'})}\n\n"
                return

            SourceMetadataTranslationService(pm, llm).translate_project_sources(
                project_id,
                sections=sections,
            )

            glossary = gm.load_merged(project_id)
            timeout_s = TimeoutConfig.get_timeout("longform")
            agent = TranslationAgent(llm, timeout=timeout_s)
            total_paragraphs = sum(len(section.paragraphs) for section in sections)
            processed_count = 0
            error_count = 0

            yield f"data: {json.dumps({'type': 'start', 'total': total_paragraphs})}\n\n"

            for section in sections:
                section_full = pm.get_section(project_id, section.section_id)
                if not section_full:
                    continue

                for index, paragraph in enumerate(section_full.paragraphs):
                    has_translation = paragraph.has_usable_translation()
                    if has_translation:
                        processed_count += 1
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "skip",
                                    "paragraph_id": paragraph.id,
                                    "current": processed_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                        continue

                    context = _build_translation_context(section_full, index, glossary)

                    try:
                        payload = agent.translate_paragraph(
                            paragraph, context
                        )
                        apply_translation_payload(paragraph, payload, "default")
                        pm.save_section(project_id, section_full)
                        processed_count += 1

                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "translated",
                                    "paragraph_id": paragraph.id,
                                    "section_id": section.section_id,
                                    "translation": payload.text,
                                    "current": processed_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                    except Exception as e:
                        processed_count += 1
                        error_count += 1
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "error",
                                    "paragraph_id": paragraph.id,
                                    "error": str(e),
                                    "current": processed_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                        continue

                    await asyncio.sleep(0.1)

            actual_translated = sum(
                1
                for section in pm.get_sections(project_id)
                for paragraph in section.paragraphs
                if paragraph.has_usable_translation()
            )

            if error_count > 0 or actual_translated < total_paragraphs:
                yield (
                    "data: "
                    + json.dumps(
                        {
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
                    )
                    + "\n\n"
                )
            else:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "complete",
                            "translated_count": actual_translated,
                            "total": total_paragraphs,
                        }
                    )
                    + "\n\n"
                )
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/projects/{project_id}/translate-four-step")
async def translate_with_four_steps(
    project_id: str,
    http_request: Request,
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
        llm = create_llm_provider(provider=_body.model)
        analysis_llm = llm

    from src.services.batch_translation_service import BatchTranslationService

    slot_claim = await BatchTranslationService.claim_translation_slot(project_id)
    if slot_claim["status"] == "busy":
        raise BadRequestException(
            detail=(
                "Another project is still stopping. "
                f"active_project_id={slot_claim.get('active_project_id')}, "
                f"active_run_id={slot_claim.get('active_run_id')}"
            )
        )

    try:
        sections = pm.get_sections(project_id)
        total_paragraphs = (
            sum(len(section.paragraphs) for section in sections) if sections else 0
        )
        total_sections = len(sections) if sections else 0

        batch_service = BatchTranslationService(
            llm_provider=llm,
            project_manager=pm,
            translation_mode=BatchTranslationService.TRANSLATION_MODE_FOUR_STEP,
            max_concurrent_sections=10,  # 并发翻译10个章节（VectorEngine支持100并发）
            analysis_llm_provider=analysis_llm,
        )
    except Exception:
        BatchTranslationService._release_active_run(project_id)
        raise
    progress_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    event_loop = asyncio.get_running_loop()

    # 初始化冲突状态（使用锁保护）
    with _conflict_lock:
        _pending_conflict_events[project_id] = {}
        _conflict_resolutions[project_id] = {}

    async def _handle_term_conflict_on_main(conflict) -> Dict[str, Any]:
        term_key = conflict.term.lower()
        event = asyncio.Event()
        with _conflict_lock:
            _pending_conflict_events[project_id][term_key] = event
        await progress_queue.put(
            {
                "type": "term_conflict",
                "conflict": conflict.model_dump(mode="json"),
            }
        )
        try:
            await event.wait()
            with _conflict_lock:
                resolution = _conflict_resolutions.get(project_id, {}).get(term_key, {})
            return {
                "chosen_translation": resolution.get("chosen_translation")
                or conflict.existing_translation
                or conflict.new_translation,
                "apply_to_all": resolution.get("apply_to_all", True),
            }
        finally:
            with _conflict_lock:
                _pending_conflict_events.get(project_id, {}).pop(term_key, None)
                _conflict_resolutions.get(project_id, {}).pop(term_key, None)

    async def run_translation():
        """在后台运行翻译任务。"""
        try:

            def on_progress(step: str, current: int, total: int):
                event_loop.call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {
                        "type": "progress",
                        "step": step,
                        "current": current,
                        "total": total,
                        "message": step,
                    },
                )

            async def on_term_conflict(conflict) -> Dict[str, Any]:
                future = asyncio.run_coroutine_threadsafe(
                    _handle_term_conflict_on_main(conflict), event_loop
                )
                return await asyncio.wrap_future(future)

            def _run_translation_in_thread() -> Dict[str, Any]:
                async def _runner() -> Dict[str, Any]:
                    return await batch_service.translate_project(
                        project_id,
                        on_progress=on_progress,
                        on_term_conflict=on_term_conflict,
                    )

                return asyncio.run(_runner())

            result = await asyncio.to_thread(_run_translation_in_thread)
            status = result.get("status")
            if status == "completed":
                event_type = "complete"
            elif status == "cancelled":
                event_type = "cancelled"
            else:
                event_type = "incomplete"
            if event_type == "complete":
                message = (
                    f"Translation complete: "
                    f"{result.get('translated_paragraphs', 0)}/{total_paragraphs} paragraphs usable"
                )
            elif event_type == "cancelled":
                message = result.get("message") or "Translation cancelled"
            else:
                message = result.get("error") or (
                    f"Translation incomplete: "
                    f"{result.get('translated_paragraphs', 0)}/{total_paragraphs} paragraphs usable"
                )
            await progress_queue.put(
                {
                    "type": event_type,
                    "translated_count": result.get(
                        "translated_paragraphs", 0
                    ),
                    "total": total_paragraphs,
                    "result": result,
                    "message": message,
                }
            )
        except Exception as e:
            await progress_queue.put(
                {
                    "type": "error",
                    "error": str(e),
                }
            )
        finally:
            # 清理冲突状态（使用锁保护）
            with _conflict_lock:
                _pending_conflict_events.pop(project_id, None)
                _conflict_resolutions.pop(project_id, None)
            # 释放翻译槽位
            from src.services.batch_translation_service import BatchTranslationService
            BatchTranslationService._release_active_run(project_id)

    async def generate_progress():
        translation_task: asyncio.Task | None = None
        translation_finished = False
        cancel_requested = False

        async def request_cancel(reason: str) -> None:
            nonlocal cancel_requested
            if cancel_requested:
                return
            cancel_requested = True
            logger.info("[%s] Requesting translation cancellation: %s", project_id, reason)
            try:
                await batch_service.cancel_translation(project_id)
            except Exception as cancel_exc:
                logger.warning("[%s] Failed to cancel translation: %s", project_id, cancel_exc)

        try:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "start",
                        "total": total_paragraphs,
                        "total_sections": total_sections,
                        "message": "开始四步法翻译",
                    }
                )
                + "\n\n"
            )

            translation_task = asyncio.create_task(run_translation())

            while True:
                if await http_request.is_disconnected():
                    await request_cancel("client disconnected")
                    break
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("complete", "error", "incomplete", "cancelled"):
                        translation_finished = True
                        break
                except asyncio.TimeoutError:
                    if await http_request.is_disconnected():
                        await request_cancel("client disconnected during heartbeat")
                        break
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                    if translation_task.done():
                        if translation_task.exception():
                            yield (
                                "data: "
                                + json.dumps(
                                    {
                                        "type": "error",
                                        "error": str(translation_task.exception()),
                                    }
                                )
                                + "\n\n"
                            )
                        translation_finished = True
                        break
        except asyncio.CancelledError:
            await request_cancel("stream task cancelled")
            raise
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            if (
                not translation_finished
                and translation_task is not None
                and not translation_task.done()
            ):
                await request_cancel("stream closed before translation finished")

    return StreamingResponse(
        generate_progress(),
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

    with _conflict_lock:
        events = _pending_conflict_events.get(project_id, {})
        resolutions = _conflict_resolutions.setdefault(project_id, {})

        term_key = request.term.lower()
        resolutions[term_key] = {
            "chosen_translation": request.chosen_translation,
            "apply_to_all": request.apply_to_all,
        }

        # 唤醒等待的翻译线程
        event = events.get(term_key)

    if event:
        event.set()

    return {
        "status": "resolved",
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
