"""
Confirmation translation/review endpoints.
"""

from datetime import datetime
import uuid

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.api.utils.glossary import get_combined_glossary

from ..dependencies import (
    ProjectManagerDep,
    LLMProviderDep,
    BatchServiceDep,
    ConfirmationServiceDep,
)
from ..middleware import NotFoundException, BadRequestException
from .confirmation_models import (
    ConfirmParagraphRequest,
    UpdateTermsRequest,
    RetranslateRequest,
    RETRANSLATE_OPTIONS,
)


router = APIRouter()


@router.post("/{project_id}/translate-all")
async def start_translation(
    project_id: str,
    service: BatchServiceDep,
):
    try:
        return await service.translate_project(project_id)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"Failed to start translation: {str(e)}")


@router.get("/{project_id}/translation-status")
async def get_translation_status(
    project_id: str,
    service: BatchServiceDep,
):
    try:
        return await service.get_translation_progress(project_id)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"Failed to get status: {str(e)}")


@router.post("/{project_id}/translation-cancel")
async def cancel_translation(
    project_id: str,
    service: BatchServiceDep,
):
    try:
        return await service.cancel_translation(project_id)
    except Exception as e:
        raise BadRequestException(detail=f"Failed to cancel: {str(e)}")


@router.get("/{project_id}/paragraph/{paragraph_index}/confirmation")
async def get_paragraph_confirmation(
    project_id: str,
    paragraph_index: int,
    service: ConfirmationServiceDep,
):
    try:
        return await service.get_paragraph_confirmation(project_id, paragraph_index)
    except IndexError as e:
        raise NotFoundException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to get confirmation: {str(e)}")


@router.put("/{project_id}/paragraph/{paragraph_id}/confirm")
async def confirm_paragraph(
    project_id: str,
    paragraph_id: str,
    request: ConfirmParagraphRequest,
    service: ConfirmationServiceDep,
):
    try:
        return await service.confirm_paragraph(
            project_id,
            paragraph_id,
            request.translation,
            request.version_id,
            request.custom_edit,
        )
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to confirm: {str(e)}")


@router.post("/{project_id}/term-update")
async def update_terms(
    project_id: str,
    request: UpdateTermsRequest,
    service: ConfirmationServiceDep,
):
    try:
        return await service.update_terms(project_id, request.changes)
    except Exception as e:
        raise BadRequestException(detail=f"Failed to update terms: {str(e)}")


@router.post("/{project_id}/paragraph/{paragraph_id}/retranslate")
async def retranslate_paragraph(
    project_id: str,
    paragraph_id: str,
    request: RetranslateRequest,
    pm: ProjectManagerDep,
    llm: LLMProviderDep,
):
    try:
        sections = pm.get_sections(project_id)
        target_section = None
        target_paragraph = None
        target_local_index = None

        for section in sections:
            for idx, para in enumerate(section.paragraphs):
                if para.id == paragraph_id:
                    target_section = section
                    target_paragraph = para
                    target_local_index = idx
                    break
            if target_paragraph:
                break

        if not target_paragraph or target_section is None or target_local_index is None:
            raise NotFoundException(detail="Paragraph not found")

        glossary = get_combined_glossary(project_id)

        context = TranslationContext(glossary=glossary)
        context.previous_paragraphs = [
            (p.source, p.confirmed)
            for p in target_section.paragraphs[:target_local_index]
            if p.confirmed
        ][-5:]
        context.next_preview = [
            p.source
            for p in target_section.paragraphs[target_local_index + 1 : target_local_index + 3]
        ]

        instruction = request.instruction or ""
        model_name = request.model or "claude"

        agent = TranslationAgent(llm)
        translation = agent.retranslate_paragraph(
            target_paragraph,
            context,
            instruction=instruction,
            model_name=model_name,
        )

        pm.save_section(project_id, target_section)

        new_version_id = f"retranslate_{uuid.uuid4().hex[:8]}"
        version_obj = target_paragraph.translations.get(model_name)
        if version_obj is None and target_paragraph.translations:
            version_obj = max(
                target_paragraph.translations.values(),
                key=lambda t: t.created_at,
            )
        created_at = version_obj.created_at if version_obj else datetime.now()

        return {
            "version_id": new_version_id,
            "paragraph_id": paragraph_id,
            "translation": translation,
            "instruction": instruction,
            "model": model_name,
            "created_at": created_at.isoformat(),
        }

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"Failed to retranslate: {str(e)}")


@router.post("/{project_id}/export-translation")
async def export_translation(
    project_id: str,
    service: ConfirmationServiceDep,
    include_source: bool = False,
):
    try:
        return await service.export_translation(
            project_id,
            include_source=include_source,
        )
    except Exception as e:
        raise BadRequestException(detail=f"Failed to export: {str(e)}")


@router.get("/{project_id}/confirmation-progress")
async def get_confirmation_progress(
    project_id: str,
    service: ConfirmationServiceDep,
):
    try:
        return await service.get_translation_progress(project_id)
    except Exception as e:
        raise BadRequestException(detail=f"Failed to get progress: {str(e)}")


@router.get("/{project_id}/retranslate-options")
async def get_retranslate_options(project_id: str):
    return {"options": RETRANSLATE_OPTIONS}


@router.post("/{project_id}/export-bilingual")
async def export_bilingual(
    project_id: str,
    service: ConfirmationServiceDep,
):
    try:
        return await service.export_translation(
            project_id,
            include_source=False,
            export_format="bilingual",
        )
    except Exception as e:
        raise BadRequestException(detail=f"Failed to export: {str(e)}")


@router.post("/{project_id}/consistency-review")
async def run_consistency_review(
    project_id: str,
    pm: ProjectManagerDep,
    llm: LLMProviderDep,
):
    try:
        from src.agents.consistency_reviewer import ConsistencyReviewer

        sections = pm.get_sections(project_id)

        translations = {}
        for section in sections:
            trans_list = []
            for para in section.paragraphs:
                if para.confirmed:
                    trans_list.append(para.confirmed)
                elif para.translations:
                    trans_list.append(list(para.translations.values())[0].text)
                else:
                    trans_list.append("")
            translations[section.section_id] = trans_list

        reviewer = ConsistencyReviewer(llm)
        report = reviewer.review(sections, translations)

        return {
            "is_consistent": report.is_consistent,
            "style_score": report.style_score,
            "issue_count": len(report.issues),
            "auto_fixable_count": len(report.auto_fixable),
            "manual_review_count": len(report.manual_review),
            "term_stats": report.term_stats,
            "suggestions": report.suggestions,
            "issues": [
                {
                    "section_id": i.section_id,
                    "paragraph_index": i.paragraph_index,
                    "issue_type": i.issue_type,
                    "description": i.description,
                    "auto_fixable": i.auto_fixable,
                    "fix_suggestion": i.fix_suggestion,
                }
                for i in report.issues
            ],
        }

    except Exception as e:
        raise BadRequestException(detail=f"Failed to run review: {str(e)}")
