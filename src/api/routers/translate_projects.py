"""
Translate project-level endpoints.
"""

import asyncio
import json
import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.models import ParagraphStatus

from ..dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep
from ..middleware import BadRequestException, NotFoundException, ServiceUnavailableException
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


def _get_best_translation_text(paragraph) -> str:
    if paragraph.confirmed:
        return paragraph.confirmed
    if paragraph.translations:
        return list(paragraph.translations.values())[0].text
    return ""


def _build_translation_context(section, index: int, glossary):
    context = TranslationContext(glossary=glossary)
    prev_context = []

    for prev_para in section.paragraphs[max(0, index - 5): index]:
        text = _get_best_translation_text(prev_para)
        if text:
            prev_context.append((prev_para.source, text))

    context.previous_paragraphs = prev_context
    context.next_preview = [next_para.source for next_para in section.paragraphs[index + 1: index + 3]]
    return context


@router.post("/projects/{project_id}/analyze", response_model=ProjectAnalysisResponse)
async def analyze_project(project_id: str):
    """分析项目原文，生成摘要和翻译指南。"""
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    try:
        project_dir = f"projects/{project_id}"
        source_path = f"{project_dir}/source.md"
        if not os.path.exists(source_path):
            raise NotFoundException(detail="Source file not found")

        with open(source_path, "r", encoding="utf-8") as file:
            content = file.read()

        preview_content = content[:8000]
        prompt = f"""You are a senior technical editor. Analyze the following article content and provide a translation guide.

## Content Preview
{preview_content}

## Task
1. **Summary**: A concise abstract of the article (in Chinese).
2. **Translation Notes**: 3-5 bullet points on tone, audience, or potential translation pitfalls (in Chinese).
3. **Key Terms**: Extract 5-10 key technical terms that need consistent translation (keep English).

## Output Format (Strict JSON)
{{
    "summary": "文章摘要...",
    "notes": ["注意...", "语气..."],
    "key_terms": ["Wafer", "Lithography"]
}}
"""

        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        analysis_path = f"{project_dir}/analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        return ProjectAnalysisResponse(
            summary=data.get("summary", ""),
            notes=data.get("notes", []),
            key_terms=data.get("key_terms", []),
        )
    except NotFoundException:
        raise
    except Exception as e:
        raise ServiceUnavailableException(detail=f"分析失败: {str(e)}")


@router.post(
    "/projects/{project_id}/sections/{section_id}/analyze",
    response_model=SectionAnalysisResponse,
)
async def analyze_section(project_id: str, section_id: str):
    """分析章节内容，生成摘要和注意事项。"""
    if not validate_path_component(project_id) or not validate_path_component(section_id):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        section_dir = f"projects/{project_id}/sections/{section_id}"
        source_path = f"{section_dir}/source.md"
        if not os.path.exists(source_path):
            raise NotFoundException(detail="Section source file not found")

        with open(source_path, "r", encoding="utf-8") as file:
            content = file.read()

        prompt = f"""You are a technical translator. Analyze the following section content.

## Section Content
{content[:5000]}

## Task
1. **Summary**: A very concise summary of this section (in Chinese, 2-3 sentences).
2. **Translation Tips**: 2-3 specific tips for translating this section (e.g., specific terms, complex sentence structure).

## Output Format (Strict JSON)
{{
    "summary": "本章主要讨论...",
    "tips": ["注意...", "处理..."]
}}
"""

        response_text = generate_with_fallback(prompt)
        data = parse_llm_json_response(response_text)

        analysis_path = f"{section_dir}/analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        return SectionAnalysisResponse(
            summary=data.get("summary", ""),
            tips=data.get("tips", []),
        )
    except NotFoundException:
        raise
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
    if not validate_path_component(project_id) or not validate_path_component(section_id):
        raise BadRequestException(detail="Invalid project_id or section_id")

    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        glossary = gm.load_project(project_id)
        agent = TranslationAgent(llm)
        translated_count = 0

        for index, paragraph in enumerate(section.paragraphs):
            if paragraph.status == ParagraphStatus.APPROVED:
                continue

            context = _build_translation_context(section, index, glossary)

            try:
                translated = agent.translate_paragraph(paragraph, context)
                paragraph.add_translation(translated, "batch_gemini")
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

            glossary = gm.load_project(project_id)
            agent = TranslationAgent(llm)
            total_paragraphs = sum(len(section.paragraphs) for section in sections)
            translated_count = 0

            yield f"data: {json.dumps({'type': 'start', 'total': total_paragraphs})}\n\n"

            for section in sections:
                section_full = pm.get_section(project_id, section.section_id)
                if not section_full:
                    continue

                for index, paragraph in enumerate(section_full.paragraphs):
                    has_translation = bool(paragraph.confirmed) or bool(paragraph.translations)
                    if has_translation:
                        translated_count += 1
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "skip",
                                    "paragraph_id": paragraph.id,
                                    "current": translated_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                        continue

                    context = _build_translation_context(section_full, index, glossary)

                    try:
                        translated = agent.translate_paragraph(paragraph, context, request.model)
                        paragraph.add_translation(translated, "batch_gemini")
                        pm.save_section(project_id, section_full)
                        translated_count += 1

                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "translated",
                                    "paragraph_id": paragraph.id,
                                    "section_id": section.section_id,
                                    "translation": translated,
                                    "current": translated_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                    except Exception as e:
                        translated_count += 1
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "error",
                                    "paragraph_id": paragraph.id,
                                    "error": str(e),
                                    "current": translated_count,
                                    "total": total_paragraphs,
                                }
                            )
                            + "\n\n"
                        )
                        continue

                    await asyncio.sleep(0.1)

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "complete",
                        "translated_count": translated_count,
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
):
    """
    使用四步法翻译整个项目（优化版）。
    """
    if not validate_path_component(project_id):
        raise BadRequestException(detail="Invalid project_id")

    from src.services.batch_translation_service import BatchTranslationService

    sections = pm.get_sections(project_id)
    total_paragraphs = sum(len(section.paragraphs) for section in sections) if sections else 0
    total_sections = len(sections) if sections else 0

    batch_service = BatchTranslationService(
        llm_provider=llm,
        project_manager=pm,
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

            result = await batch_service.translate_project(
                project_id,
                on_progress=on_progress,
            )
            await progress_queue.put(
                {
                    "type": "complete",
                    "translated_count": result.get("translated_paragraphs", total_paragraphs),
                    "total": total_paragraphs,
                    "result": result,
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
                    if event.get("type") in ("complete", "error"):
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


@router.post("/projects/{project_id}/resolve-conflict", response_model=ResolveConflictResponse)
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
                    if term_lower in paragraph.source.lower() and paragraph.translations:
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
