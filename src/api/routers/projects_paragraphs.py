"""
Paragraph translation/update endpoints.
"""

from typing import List

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.core.models import ParagraphStatus

from ..dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep
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


@router.post("/projects/{project_id}/sections/{section_id}/paragraphs/{paragraph_id}/translate")
async def translate_paragraph(
    project_id: str,
    section_id: str,
    paragraph_id: str,
    request: TranslateRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LLMProviderDep,
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
        context = TranslationContext(glossary=glossary)
        context.previous_paragraphs = [
            (p.source, p.confirmed) for p in section.paragraphs[:para_index] if p.confirmed
        ][-5:]
        context.next_preview = [
            p.source for p in section.paragraphs[para_index + 1 : para_index + 3]
        ]

        agent = TranslationAgent(llm)
        if request.instruction:
            translation = agent.retranslate_paragraph(
                paragraph,
                context,
                request.instruction,
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

        translation = llm.generate(simple_prompt, temperature=0.5, max_retries=2)
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

        answer = llm.generate(prompt, temperature=0.3, max_retries=2)
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
):
    try:
        status = ParagraphStatus(request.status) if request.status else None
        paragraph = pm.update_paragraph(
            project_id,
            section_id,
            paragraph_id,
            translation=request.translation,
            status=status,
        )
        return {
            "id": paragraph.id,
            "translation": paragraph.confirmed,
            "status": paragraph.status.value,
        }
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))
    except ValueError as e:
        raise BadRequestException(detail=str(e))
