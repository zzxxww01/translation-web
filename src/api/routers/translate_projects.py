"""
Translate project-level endpoints.
"""

import asyncio
import json

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.models import ParagraphStatus
from src.services.analysis_service import AnalysisService

from ..dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep
from ..middleware import (
    BadRequestException,
    NotFoundException,
    ServiceUnavailableException,
)
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .translate_models import (
    FullTranslateRequest,
    ProjectAnalysisResponse,
    ResolveConflictRequest,
    ResolveConflictResponse,
    SectionAnalysisResponse,
)
from .translate_utils import validate_path_component


router = APIRouter()
analysis_service = AnalysisService()


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
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    try:
        data = analysis_service.analyze_project(project_id)
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
    if not validate_path_component(project_id) or not validate_path_component(
        section_id
    ):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        data = analysis_service.analyze_section(project_id, section_id)
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
    llm: LLMProviderDep,
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

        glossary = gm.load_merged(project_id)
        agent = TranslationAgent(llm)
        translated_count = 0

        for index, paragraph in enumerate(section.paragraphs):
            if paragraph.status == ParagraphStatus.APPROVED:
                continue

            context = _build_translation_context(section, index, glossary)

            try:
                translated = agent.translate_paragraph(paragraph, context)
                pm.save_section(project_id, section)
                translated_count += 1
            except Exception as e:
                print(f"Error translating paragraph {paragraph.id}: {e}")
                continue

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
    llm: LLMProviderDep,
):
    """
    全文一键翻译（SSE）。
    翻译项目中所有章节的所有段落。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    async def generate_progress():
        try:
            sections = pm.get_sections(project_id)
            if not sections:
                yield f"data: {json.dumps({'error': 'No sections found'})}\n\n"
                return

            glossary = gm.load_merged(project_id)
            agent = TranslationAgent(llm)
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
                        translated = agent.translate_paragraph(
                            paragraph, context, request.model
                        )
                        pm.save_section(project_id, section_full)
                        processed_count += 1

                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "translated",
                                    "paragraph_id": paragraph.id,
                                    "section_id": section.section_id,
                                    "translation": translated,
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
    pm: ProjectManagerDep,
    llm: LLMProviderDep,
    request: FullTranslateRequest = Body(default_factory=FullTranslateRequest),
):
    """
    使用四步法翻译整个项目（优化版）。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    from src.services.batch_translation_service import BatchTranslationService

    sections = pm.get_sections(project_id)
    total_paragraphs = (
        sum(len(section.paragraphs) for section in sections) if sections else 0
    )
    total_sections = len(sections) if sections else 0

    batch_service = BatchTranslationService(
        llm_provider=llm,
        project_manager=pm,
        translation_mode=BatchTranslationService.TRANSLATION_MODE_FOUR_STEP,
    )
    progress_queue = asyncio.Queue()

    async def run_translation():
        """在后台运行翻译任务。"""
        try:

            def on_progress(step: str, current: int, total: int):
                asyncio.get_event_loop().call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {
                        "type": "progress",
                        "step": step,
                        "current": current,
                        "total": total,
                        "message": step,
                    },
                )

            with llm.use_model(request.model):
                result = await batch_service.translate_project(
                    project_id,
                    on_progress=on_progress,
                )
            event_type = "complete" if result.get("status") == "completed" else "incomplete"
            await progress_queue.put(
                {
                    "type": event_type,
                    "translated_count": result.get(
                        "translated_paragraphs", 0
                    ),
                    "total": total_paragraphs,
                    "result": result,
                    "message": result.get(
                        "error"
                    ) or (
                        f"Translation incomplete: "
                        f"{result.get('translated_paragraphs', 0)}/{total_paragraphs} paragraphs usable"
                    ),
                }
            )
        except Exception as e:
            await progress_queue.put(
                {
                    "type": "error",
                    "error": str(e),
                }
            )

    async def generate_progress():
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
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("complete", "error", "incomplete"):
                        break
                except asyncio.TimeoutError:
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
                        break
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


@router.post(
    "/projects/{project_id}/resolve-conflict", response_model=ResolveConflictResponse
)
async def resolve_term_conflict(
    project_id: str,
    request: ResolveConflictRequest,
    pm: ProjectManagerDep,
):
    """
    解决术语冲突。
    当检测到同一术语有不同翻译建议时，用户通过此 API 选择使用的翻译。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    try:
        pm.get(project_id)
        sections = pm.get_sections(project_id)
        affected_count = 0

        if request.apply_to_all:
            term_lower = request.term.lower()

            for section in sections:
                section_modified = False
                for paragraph in section.paragraphs:
                    if (
                        term_lower in paragraph.source.lower()
                        and paragraph.translations
                    ):
                        affected_count += 1
                        section_modified = True

                if section_modified:
                    pm.save_section(project_id, section)

        return ResolveConflictResponse(
            status="resolved",
            affected_paragraphs=affected_count,
        )
    except Exception as e:
        raise ServiceUnavailableException(detail=f"解决冲突失败: {str(e)}")
