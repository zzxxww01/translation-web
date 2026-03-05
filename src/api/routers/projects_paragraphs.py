"""
Paragraph translation/update endpoints.
"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.models import ParagraphStatus

from ..dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep, MemoryServiceDep
from ..middleware import BadRequestException, NotFoundException
from .projects_models import (
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
    if paragraph.translations:
        return max(
            paragraph.translations.values(),
            key=lambda item: item.created_at,
        ).text
    return None


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

        pm.save_section(project_id, section)
        return {
            "id": paragraph.id,
            "source": paragraph.source,
            "translation": translation,
            "status": paragraph.status.value,
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
        paragraph.add_translation(translation, request.model + "-direct")
        pm.save_section(project_id, section)

        return {
            "id": paragraph.id,
            "source": paragraph.source,
            "translation": translation,
            "status": paragraph.status.value,
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
):
    try:
        paragraph = pm.confirm_paragraph(project_id, section_id, paragraph_id, request.translation)
        return {
            "id": paragraph.id,
            "translation": paragraph.confirmed,
            "status": paragraph.status.value,
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
        if not previous_translation and existing_paragraph.translations:
            previous_translation = max(
                existing_paragraph.translations.values(),
                key=lambda item: item.created_at,
            ).text

        status = ParagraphStatus(request.status) if request.status else None
        paragraph = pm.update_paragraph(
            project_id,
            section_id,
            paragraph_id,
            translation=request.translation,
            status=status,
        )

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

        latest_translation = paragraph.confirmed
        if not latest_translation and paragraph.translations:
            latest_translation = max(
                paragraph.translations.values(),
                key=lambda item: item.created_at,
            ).text

        return {
            "id": paragraph.id,
            "translation": latest_translation,
            "status": paragraph.status.value,
        }
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))
    except ValueError as e:
        raise BadRequestException(detail=str(e))
