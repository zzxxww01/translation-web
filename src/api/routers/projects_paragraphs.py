"""
Paragraph translation/update endpoints.
"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.models import ParagraphStatus

from ..dependencies import (
    GlossaryManagerDep,
    LLMProviderDep,
    ProjectManagerDep,
    MemoryServiceDep,
    ConfirmationServiceDep,
)
from ..middleware import BadRequestException, NotFoundException
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


router = APIRouter()


def _get_latest_translation_text(paragraph) -> Optional[str]:
    if paragraph.confirmed:
        return paragraph.confirmed
    return paragraph.latest_translation_text(non_empty=True)


def _build_retranslate_instruction(
    user_instruction: str,
    source_text: str,
    current_translation: Optional[str],
) -> str:
    """Build a full retranslation prompt so short user input can stay on context."""
    instruction = user_instruction.strip()
    if not instruction:
        return ""

    # Avoid double-wrapping if caller already sends a fully-structured prompt.
    if "【原文】" in instruction and "【固定要求】" in instruction:
        return instruction

    _ = source_text
    _ = current_translation
    return f"""【重译目标】
请在不偏离原文的前提下，基于当前段落上下文重写译文。

【用户要求】
{instruction}

【固定要求】
1. 以原文为准：信息、事实、逻辑关系不能丢失或改写错误。
2. 先纠错再优化：若当前译文有误，必须优先修正，再执行用户要求。
3. 术语一致：专有名词、技术术语、数字和单位保持一致且准确。
4. 长文风格：表达自然、清晰、可读，避免翻译腔和空洞套话。
5. 输出约束：仅输出“新的完整译文”，不要解释、不要Markdown。
"""


@router.post("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/translate")
async def translate_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: TranslateRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        paragraph = None
        para_index = 0
        for i, p in enumerate(section.paragraphs):
            if p.id == paragraph_id:
                paragraph = p
                para_index = i
                break
        if not paragraph:
            raise NotFoundException(detail="Paragraph not found")

        glossary = gm.load_project(project_id)

        # 加载已学习的翻译规则
        learned_rules = memory_service.get_relevant_rules(
            paragraph.source,
            project_id=project_id,
        )

        context = TranslationContext(glossary=glossary, learned_rules=learned_rules)
        context.previous_paragraphs = [
            (p.source, p.confirmed) for p in section.paragraphs[:para_index] if p.confirmed
        ][-5:]
        context.next_preview = [
            p.source for p in section.paragraphs[para_index + 1 : para_index + 3]
        ]

        agent = TranslationAgent(llm)
        instruction = (request.instruction or "").strip()
        if instruction:
            formatted_instruction = _build_retranslate_instruction(
                instruction,
                paragraph.source,
                _get_latest_translation_text(paragraph),
            )
            translation = agent.retranslate_paragraph(
                paragraph,
                context,
                formatted_instruction,
                request.model,
            )
        else:
            translation = agent.translate_paragraph(paragraph, context, request.model)

        persisted_paragraph = pm.update_paragraph_locked(
            project_id,
            section_id,
            paragraph_id,
            translation=translation,
            status=ParagraphStatus.TRANSLATED,
            model=request.model,
        )
        await service.invalidate_project_cache(project_id)
        return {
            "id": persisted_paragraph.id,
            "source": persisted_paragraph.source,
            "translation": translation,
            "status": persisted_paragraph.status.value,
            "confirmed": persisted_paragraph.confirmed,
        }
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            raise BadRequestException(
                detail="API请求频率限制，请稍后再试。建议等待1-2分钟后重新尝试翻译。"
            )
        elif "Generation failed after" in error_msg and "retries" in error_msg:
            raise BadRequestException(
                detail="翻译服务暂时不可用，请稍后再试。如果问题持续存在，请联系管理员。"
            )
        else:
            raise BadRequestException(detail=f"翻译失败：{error_msg}")
    except Exception as e:
        raise BadRequestException(detail=f"翻译过程中发生错误：{str(e)}")


@router.post(
    "/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/direct-translate"
)
async def direct_translate_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: DirectTranslateRequest,
    pm: ProjectManagerDep,
    llm: LLMProviderDep,
    service: ConfirmationServiceDep,
):
    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        paragraph = None
        for p in section.paragraphs:
            if p.id == paragraph_id:
                paragraph = p
                break
        if not paragraph:
            raise NotFoundException(detail="Paragraph not found")

        simple_prompt = f"""请将以下英文翻译成中文：

{paragraph.source}

请直接输出中文翻译，不要添加任何解释或说明："""

        translation = llm.generate(
            simple_prompt,
            temperature=0.5,
            max_retries=2,
            model=request.model,
        )
        persisted_paragraph = pm.update_paragraph_locked(
            project_id,
            section_id,
            paragraph_id,
            translation=translation,
            status=ParagraphStatus.TRANSLATED,
            model=request.model + "-direct",
        )
        await service.invalidate_project_cache(project_id)

        return {
            "id": persisted_paragraph.id,
            "source": persisted_paragraph.source,
            "translation": translation,
            "status": persisted_paragraph.status.value,
            "confirmed": persisted_paragraph.confirmed,
            "method": "direct",
        }
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            raise BadRequestException(
                detail="API请求频率限制，请稍后再试。建议等待1-2分钟后重新尝试翻译。"
            )
        elif "Generation failed after" in error_msg and "retries" in error_msg:
            raise BadRequestException(
                detail="翻译服务暂时不可用，请稍后再试。如果问题持续存在，请联系管理员。"
            )
        else:
            raise BadRequestException(detail=f"翻译失败：{error_msg}")
    except Exception as e:
        raise BadRequestException(detail=f"翻译过程中发生错误：{str(e)}")


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
    llm: LLMProviderDep,
):
    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        paragraph = None
        for p in section.paragraphs:
            if p.id == paragraph_id:
                paragraph = p
                break
        if not paragraph:
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
            model=request.model,
        )
        return WordMeaningResponse(answer=answer.strip())
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except RuntimeError as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            raise BadRequestException(
                detail="API请求频率限制，请稍后再试。建议等待1-2分钟后重新尝试。"
            )
        elif "Generation failed after" in error_msg and "retries" in error_msg:
            raise BadRequestException(detail="词义查询服务暂时不可用，请稍后再试。")
        else:
            raise BadRequestException(detail=f"词义查询失败：{error_msg}")
    except Exception as e:
        raise BadRequestException(detail=f"词义查询过程中发生错误：{str(e)}")


@router.put("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/confirm")
async def confirm_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: ConfirmRequest,
    pm: ProjectManagerDep,
    service: ConfirmationServiceDep,
):
    try:
        paragraph = pm.update_paragraph_locked(
            project_id,
            section_id,
            paragraph_id,
            translation=request.translation,
            status=ParagraphStatus.APPROVED,
            model="manual",
        )
        await service.invalidate_project_cache(project_id)
        return {
            "id": paragraph.id,
            "translation": paragraph.confirmed,
            "status": paragraph.status.value,
            "confirmed": paragraph.confirmed,
        }
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))


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
    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise FileNotFoundError(f"Section not found: {section_id}")

        existing_paragraph = next(
            (paragraph for paragraph in section.paragraphs if paragraph.id == paragraph_id),
            None,
        )
        if not existing_paragraph:
            raise FileNotFoundError(f"Paragraph not found: {paragraph_id}")

        previous_translation = existing_paragraph.confirmed
        if not previous_translation:
            previous_translation = existing_paragraph.latest_translation_text(
                non_empty=True
            )

        status = ParagraphStatus(request.status) if request.status else None
        current_translation = _get_latest_translation_text(existing_paragraph)
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
        await service.invalidate_project_cache(project_id)

        if (
            request.translation is not None
            and request.edit_source == "immersive_auto_save"
            and previous_translation
            and previous_translation != request.translation
        ):
            asyncio.create_task(
                memory_service.process_correction(
                    request.source_text or existing_paragraph.source,
                    previous_translation,
                    request.translation,
                    project_id=project_id,
                )
            )

        latest_translation = paragraph.best_translation_text()

        return {
            "id": paragraph.id,
            "translation": latest_translation,
            "status": paragraph.status.value,
            "confirmed": paragraph.confirmed,
        }
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))
    except ValueError as e:
        raise BadRequestException(detail=str(e))


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
    llm: LLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            raise NotFoundException(detail="Section not found")

        if not request.paragraph_ids:
            raise BadRequestException(detail="段落ID列表不能为空")

        glossary = gm.load_project(project_id)
        agent = TranslationAgent(llm)

        paragraph_map = {p.id: (i, p) for i, p in enumerate(section.paragraphs)}

        translations = []
        errors = []
        success_count = 0
        error_count = 0

        with pm.section_lock(project_id, section_id):
            for paragraph_id in request.paragraph_ids:
                if paragraph_id not in paragraph_map:
                    errors.append({"id": paragraph_id, "error": "段落不存在"})
                    error_count += 1
                    continue

                para_index, paragraph = paragraph_map[paragraph_id]

                try:
                    learned_rules = memory_service.get_relevant_rules(
                        paragraph.source,
                        project_id=project_id,
                    )

                    context = TranslationContext(glossary=glossary, learned_rules=learned_rules)
                    context.previous_paragraphs = [
                        (p.source, p.confirmed)
                        for p in section.paragraphs[:para_index]
                        if p.confirmed
                    ][-5:]
                    context.next_preview = [
                        p.source for p in section.paragraphs[para_index + 1 : para_index + 3]
                    ]

                    instruction = (request.instruction or "").strip()
                    if instruction:
                        formatted_instruction = _build_retranslate_instruction(
                            instruction,
                            paragraph.source,
                            _get_latest_translation_text(paragraph),
                        )
                        translation = agent.retranslate_paragraph(
                            paragraph,
                            context,
                            formatted_instruction,
                            request.model,
                        )
                    else:
                        translation = agent.translate_paragraph(paragraph, context, request.model)

                    persisted_paragraph = pm.update_paragraph(
                        project_id,
                        section_id,
                        paragraph_id,
                        translation=translation,
                        status=ParagraphStatus.TRANSLATED,
                        model=request.model,
                    )
                    translations.append(
                        {
                            "id": paragraph.id,
                            "translation": translation,
                            "status": persisted_paragraph.status.value,
                            "confirmed": persisted_paragraph.confirmed,
                        }
                    )
                    success_count += 1

                except Exception as e:
                    error_msg = _to_error_message(e)
                    errors.append({"id": paragraph_id, "error": error_msg})
                    error_count += 1

        await service.invalidate_project_cache(project_id)

        return BatchTranslateResponse(
            translations=translations,
            success_count=success_count,
            error_count=error_count,
            errors=errors,
        )

    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"批量翻译失败：{str(e)}")


def _to_error_message(error: Exception) -> str:
    error_msg = str(error)
    if "429" in error_msg or "Too Many Requests" in error_msg:
        return "API请求频率限制，请稍后再试"
    elif "Generation failed after" in error_msg and "retries" in error_msg:
        return "翻译服务暂时不可用，请稍后再试"
    else:
        return f"翻译失败：{error_msg}"
