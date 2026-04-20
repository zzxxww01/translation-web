"""Paragraph translation/update endpoints."""

import asyncio
from typing import List

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.config.timeout_config import TimeoutConfig
from src.core.glossary_prompt import build_term_usage_from_project
from src.core.models import ParagraphStatus

from ..dependencies import (
    ConfirmationServiceDep,
    GlossaryManagerDep,
    LongformLLMProviderDep,
    MemoryServiceDep,
    ProjectManagerDep,
)
from ..middleware import BadRequestException, NotFoundException
from .confirmation_models import resolve_retranslate_instruction
from .projects_models import (
    BatchTranslateRequest,
    BatchTranslateResponse,
    ConfirmRequest,
    DirectTranslateRequest,
    TranslateRequest,
    UpdateParagraphRequest,
    WordMeaningRequest,
    WordMeaningResponse,
)
from .translate_utils import build_retranslate_instruction, get_latest_translation_text, validate_path_component


router = APIRouter()

def _find_paragraph(section, paragraph_id: str):
    for index, paragraph in enumerate(section.paragraphs):
        if paragraph.id == paragraph_id:
            return paragraph, index
    return None, None


def _build_translation_context(
    section,
    para_index: int,
    glossary,
    learned_rules,
    *,
    sections=None,
) -> TranslationContext:
    context = TranslationContext(glossary=glossary, learned_rules=learned_rules)
    context.previous_paragraphs = [
        (p.source, p.confirmed) for p in section.paragraphs[:para_index] if p.confirmed
    ][-5:]
    context.next_preview = [
        p.source for p in section.paragraphs[para_index + 1 : para_index + 3]
    ]
    if sections and 0 <= para_index < len(section.paragraphs):
        context.term_usage = build_term_usage_from_project(
            sections,
            glossary,
            current_section_id=section.section_id,
            current_paragraph_id=section.paragraphs[para_index].id,
        )
    return context

def _translate_paragraph_sync(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: TranslateRequest,
    pm,
    gm,
    llm,
    memory_service,
):
    section = pm.get_section(project_id, section_id)
    if not section:
        raise NotFoundException(detail="Section not found")

    paragraph, para_index = _find_paragraph(section, paragraph_id)
    if paragraph is None or para_index is None:
        raise NotFoundException(detail="Paragraph not found")

    glossary = gm.load_merged(project_id)
    learned_rules = memory_service.get_rules_for_prompt()
    sections = pm.get_sections(project_id)
    context = _build_translation_context(
        section,
        para_index,
        glossary,
        learned_rules,
        sections=sections,
    )

    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)
    instruction = resolve_retranslate_instruction(request.instruction, getattr(request, 'option_id', None))
    if instruction:
        formatted_instruction = build_retranslate_instruction(
            instruction,
            paragraph.source,
            get_latest_translation_text(paragraph),
        )
        payload = agent.retranslate_paragraph(
            paragraph,
            context,
            formatted_instruction,
        )
    else:
        payload = agent.translate_paragraph(paragraph, context)

    persisted_paragraph = pm.update_paragraph_locked(
        project_id,
        section_id,
        paragraph_id,
        translation=payload.text,
        tokenized_text=payload.tokenized_text,
        format_issues=payload.format_issues,
        status=ParagraphStatus.TRANSLATED,
        model="default",
    )
    return {
        "id": persisted_paragraph.id,
        "source": persisted_paragraph.source,
        "translation": payload.text,
        "status": persisted_paragraph.status.value,
        "confirmed": persisted_paragraph.confirmed,
    }


def _direct_translate_paragraph_sync(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: DirectTranslateRequest,
    pm,
    llm,
):
    section = pm.get_section(project_id, section_id)
    if not section:
        raise NotFoundException(detail="Section not found")

    paragraph, _ = _find_paragraph(section, paragraph_id)
    if paragraph is None:
        raise NotFoundException(detail="Paragraph not found")

    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)
    payload = agent.translate_paragraph(
        paragraph,
        TranslationContext(),
    )
    persisted_paragraph = pm.update_paragraph_locked(
        project_id,
        section_id,
        paragraph_id,
        translation=payload.text,
        tokenized_text=payload.tokenized_text,
        format_issues=payload.format_issues,
        status=ParagraphStatus.TRANSLATED,
        model="default-direct",
    )
    return {
        "id": persisted_paragraph.id,
        "source": persisted_paragraph.source,
        "translation": payload.text,
        "status": persisted_paragraph.status.value,
        "confirmed": persisted_paragraph.confirmed,
        "method": "direct",
    }


def _query_word_meaning_sync(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: WordMeaningRequest,
    pm,
    llm,
) -> WordMeaningResponse:
    section = pm.get_section(project_id, section_id)
    if not section:
        raise NotFoundException(detail="Section not found")

    paragraph, _ = _find_paragraph(section, paragraph_id)
    if paragraph is None:
        raise NotFoundException(detail="Paragraph not found")

    word = request.word.strip()
    query = request.query.strip()
    if not word:
        raise BadRequestException(detail="查询词语不能为空")
    if not query:
        raise BadRequestException(detail="查询问题不能为空")

    history_lines: List[str] = []
    for message in request.history[-8:]:
        role = "用户" if message.role == "user" else "助手"
        content = message.content.strip()
        if content:
            history_lines.append(f"{role}: {content}")

    if not history_lines:
        prompt = query
    else:
        history_text = "\n".join(history_lines)
        prompt = (
            "你是词义助手，请根据历史对话继续回答用户问题。\n\n"
            f"历史对话：\n{history_text}\n\n"
            f"用户最新问题：\n{query}"
        )

    answer = llm.generate(
        prompt,
        temperature=0.3,
        max_retries=2,
    )
    return WordMeaningResponse(answer=answer.strip())


def _confirm_paragraph_sync(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: ConfirmRequest,
    pm,
):
    paragraph = pm.update_paragraph_locked(
        project_id,
        section_id,
        paragraph_id,
        translation=request.translation,
        status=ParagraphStatus.APPROVED,
        model="manual",
    )
    return {
        "id": paragraph.id,
        "translation": paragraph.confirmed,
        "status": paragraph.status.value,
        "confirmed": paragraph.confirmed,
    }


def _update_paragraph_sync(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: UpdateParagraphRequest,
    pm,
):
    section = pm.get_section(project_id, section_id)
    if not section:
        raise FileNotFoundError(f"Section not found: {section_id}")

    existing_paragraph, _ = _find_paragraph(section, paragraph_id)
    if existing_paragraph is None:
        raise FileNotFoundError(f"Paragraph not found: {paragraph_id}")

    previous_translation = existing_paragraph.confirmed
    if not previous_translation:
        previous_translation = existing_paragraph.latest_translation_text(non_empty=True)

    status = ParagraphStatus(request.status) if request.status else None
    current_translation = get_latest_translation_text(existing_paragraph)
    if request.translation is not None and status is None:
        if existing_paragraph.status == ParagraphStatus.PENDING and request.translation.strip():
            status = ParagraphStatus.TRANSLATED
        elif current_translation != request.translation:
            status = (
                ParagraphStatus.MODIFIED
                if current_translation
                else ParagraphStatus.TRANSLATED
            )

    paragraph = pm.update_paragraph_locked(
        project_id,
        section_id,
        paragraph_id,
        translation=request.translation,
        status=status,
    )

    correction_payload = None
    if (
        request.translation is not None
        and request.edit_source == "immersive_auto_save"
        and previous_translation
        and previous_translation != request.translation
    ):
        correction_payload = {
            "source_text": request.source_text or existing_paragraph.source,
            "previous_translation": previous_translation,
            "updated_translation": request.translation,
        }

    return (
        {
            "id": paragraph.id,
            "translation": paragraph.best_translation_text(),
            "status": paragraph.status.value,
            "confirmed": paragraph.confirmed,
        },
        correction_payload,
    )


def _batch_translate_paragraphs_sync(
    project_id: str,
    section_id: str,
    request: BatchTranslateRequest,
    pm,
    gm,
    llm,
    memory_service,
) -> BatchTranslateResponse:
    section = pm.get_section(project_id, section_id)
    if not section:
        raise NotFoundException(detail="Section not found")

    if not request.paragraph_ids:
        raise BadRequestException(detail="段落 ID 列表不能为空")

    glossary = gm.load_merged(project_id)
    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)
    paragraph_map = {p.id: (i, p) for i, p in enumerate(section.paragraphs)}

    translations = []
    errors = []
    success_count = 0
    error_count = 0

    for paragraph_id in request.paragraph_ids:
        if paragraph_id not in paragraph_map:
            errors.append({"id": paragraph_id, "error": "Paragraph not found"})
            error_count += 1
            continue

        para_index, paragraph = paragraph_map[paragraph_id]

        try:
            learned_rules = memory_service.get_rules_for_prompt()
            sections = pm.get_sections(project_id)
            context = _build_translation_context(
                section,
                para_index,
                glossary,
                learned_rules,
                sections=sections,
            )

            instruction = resolve_retranslate_instruction(request.instruction, getattr(request, 'option_id', None))
            if instruction:
                formatted_instruction = build_retranslate_instruction(
                    instruction,
                    paragraph.source,
                    get_latest_translation_text(paragraph),
                )
                payload = agent.retranslate_paragraph(
                    paragraph,
                    context,
                    formatted_instruction,
                )
            else:
                payload = agent.translate_paragraph(paragraph, context)

            persisted_paragraph = pm.update_paragraph_locked(
                project_id,
                section_id,
                paragraph_id,
                translation=payload.text,
                tokenized_text=payload.tokenized_text,
                format_issues=payload.format_issues,
                status=ParagraphStatus.TRANSLATED,
                model="default",
            )
            translations.append(
                {
                    "id": paragraph.id,
                    "translation": payload.text,
                    "status": persisted_paragraph.status.value,
                    "confirmed": persisted_paragraph.confirmed,
                }
            )
            success_count += 1
        except Exception as error:
            errors.append({"id": paragraph_id, "error": _to_error_message(error)})
            error_count += 1

    return BatchTranslateResponse(
        translations=translations,
        success_count=success_count,
        error_count=error_count,
        errors=errors,
    )


def _to_bad_request(error: Exception, action: str) -> BadRequestException:
    import os
    import logging

    error_msg = str(error)
    logger = logging.getLogger(__name__)

    if "429" in error_msg or "Too Many Requests" in error_msg:
        return BadRequestException(detail="API rate limit reached. Please try again later.")
    if "Generation failed after" in error_msg and "retries" in error_msg:
        return BadRequestException(detail=f"{action} service is temporarily unavailable. Please try again later.")

    # 生产环境不暴露详细错误信息
    logger.error(f"{action} failed: {error_msg}")
    if os.getenv("DEBUG") == "true":
        return BadRequestException(detail=f"{action} failed: {error_msg}")
    return BadRequestException(detail=f"{action} failed. Please try again or contact support.")


@router.post("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/translate")
async def translate_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: TranslateRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id) or not validate_path_component(paragraph_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        result = await asyncio.to_thread(
            _translate_paragraph_sync,
            project_id,
            section_id,
            paragraph_id,
            request,
            pm,
            gm,
            llm,
            memory_service,
        )
        await service.invalidate_project_cache(project_id)
        return result
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as error:
        raise _to_bad_request(error, "Translation")
    except Exception as error:
        raise BadRequestException(detail=f"Unexpected translation error: {str(error)}")


@router.post(
    "/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/direct-translate"
)
async def direct_translate_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: DirectTranslateRequest,
    pm: ProjectManagerDep,
    llm: LongformLLMProviderDep,
    service: ConfirmationServiceDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id) or not validate_path_component(paragraph_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        result = await asyncio.to_thread(
            _direct_translate_paragraph_sync,
            project_id,
            section_id,
            paragraph_id,
            request,
            pm,
            llm,
        )
        await service.invalidate_project_cache(project_id)
        return result
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as error:
        raise _to_bad_request(error, "Translation")
    except Exception as error:
        raise BadRequestException(detail=f"Unexpected translation error: {str(error)}")


@router.post(
    "/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/word-meaning",
    response_model=WordMeaningResponse,
)
async def query_word_meaning(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: WordMeaningRequest,
    pm: ProjectManagerDep,
    llm: LongformLLMProviderDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id) or not validate_path_component(paragraph_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        return await asyncio.to_thread(
            _query_word_meaning_sync,
            project_id,
            section_id,
            paragraph_id,
            request,
            pm,
            llm,
        )
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as error:
        raise _to_bad_request(error, "Word meaning query")
    except Exception as error:
        raise BadRequestException(detail=f"Unexpected word meaning error: {str(error)}")


@router.put("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/confirm")
async def confirm_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: ConfirmRequest,
    pm: ProjectManagerDep,
    service: ConfirmationServiceDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id) or not validate_path_component(paragraph_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        result = await asyncio.to_thread(
            _confirm_paragraph_sync,
            project_id,
            section_id,
            paragraph_id,
            request,
            pm,
        )
        await service.invalidate_project_cache(project_id)
        return result
    except FileNotFoundError as error:
        raise NotFoundException(detail=str(error))


@router.put("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}")
async def update_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: UpdateParagraphRequest,
    pm: ProjectManagerDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id) or not validate_path_component(paragraph_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        result, correction_payload = await asyncio.to_thread(
            _update_paragraph_sync,
            project_id,
            section_id,
            paragraph_id,
            request,
            pm,
        )
        await service.invalidate_project_cache(project_id)

        if correction_payload is not None:
            asyncio.create_task(
                memory_service.process_correction(
                    correction_payload["source_text"],
                    correction_payload["previous_translation"],
                    correction_payload["updated_translation"],
                )
            )

        return result
    except FileNotFoundError as error:
        raise NotFoundException(detail=str(error))
    except ValueError as error:
        raise BadRequestException(detail=str(error))


@router.post(
    "/projects/{project_id}/sections/{section_id}/translate_batch",
    response_model=BatchTranslateResponse,
)
async def batch_translate_paragraphs(
    project_id: str,
    section_id: str,
    request: BatchTranslateRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    if not validate_path_component(project_id) or not validate_path_component(section_id):
        raise BadRequestException(detail="Invalid path component")
    try:
        result = await asyncio.to_thread(
            _batch_translate_paragraphs_sync,
            project_id,
            section_id,
            request,
            pm,
            gm,
            llm,
            memory_service,
        )
        await service.invalidate_project_cache(project_id)
        return result
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except BadRequestException:
        raise
    except Exception as error:
        raise BadRequestException(detail=f"Batch translation failed: {str(error)}")


def _to_error_message(error: Exception) -> str:
    import os
    import logging

    error_msg = str(error)
    logger = logging.getLogger(__name__)
    logger.error(f"Translation error: {error_msg}")

    if "429" in error_msg or "Too Many Requests" in error_msg:
        return "API rate limit reached. Please try again later."
    if "Generation failed after" in error_msg and "retries" in error_msg:
        return "Translation service is temporarily unavailable. Please try again later."

    # 生产环境不暴露详细错误信息
    if os.getenv("DEBUG") == "true":
        return f"Translation failed: {error_msg}"
    return "Translation failed. Please try again or contact support."
