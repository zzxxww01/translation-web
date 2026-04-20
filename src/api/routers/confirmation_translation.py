"""
Confirmation translation/review endpoints.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import uuid

from fastapi import APIRouter

from src.agents.translation import TranslationAgent, TranslationContext
from src.config.timeout_config import TimeoutConfig
from src.core.format_tokens import apply_translation_payload
from src.core.glossary_prompt import build_term_usage_from_project
from src.core.models import ArticleAnalysis
from src.api.utils.glossary import get_combined_glossary

from ..dependencies import (
    ProjectManagerDep,
    LongformLLMProviderDep,
    BatchServiceDep,
    ConfirmationServiceDep,
    MemoryServiceDep,
)
from ..middleware import NotFoundException, BadRequestException
from .confirmation_models import (
    ConfirmParagraphRequest,
    UpdateTermsRequest,
    RetranslateRequest,
    RETRANSLATE_OPTIONS,
    resolve_retranslate_instruction,
)
from .translate_utils import build_retranslate_instruction, get_latest_translation_text


router = APIRouter()

ALLOWED_CONSISTENCY_ISSUE_TYPES = {"terminology"}


def _load_latest_article_analysis(pm, project_id: str) -> ArticleAnalysis | None:
    runs_root = Path(pm.projects_path) / project_id / "artifacts" / "runs"
    if not runs_root.exists():
        return None

    run_dirs = sorted(
        (path for path in runs_root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for run_dir in run_dirs:
        analysis_path = run_dir / "analysis.json"
        if not analysis_path.exists():
            continue
        try:
            with open(analysis_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return ArticleAnalysis.model_validate(payload)
        except (json.JSONDecodeError, OSError, ValueError):
            continue
    return None


def _filter_consistency_issues(issues: list[dict]) -> list[dict]:
    return [
        item for item in issues
        if item.get("issue_type") in ALLOWED_CONSISTENCY_ISSUE_TYPES
    ]


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
    llm: LongformLLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
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

        # 加载已学习的翻译规则
        learned_rules = memory_service.get_rules_for_prompt()

        context = TranslationContext(glossary=glossary, learned_rules=learned_rules)
        context.previous_paragraphs = [
            (p.source, p.confirmed)
            for p in target_section.paragraphs[:target_local_index]
            if p.confirmed
        ][-5:]
        context.next_preview = [
            p.source
            for p in target_section.paragraphs[target_local_index + 1 : target_local_index + 3]
        ]

        # 构建术语使用记录，避免 first_annotate/preserve_annotate 术语重复加注
        context.term_usage = build_term_usage_from_project(
            sections,
            glossary,
            current_section_id=target_section.section_id,
            current_paragraph_id=paragraph_id,
        )

        instruction = resolve_retranslate_instruction(request.instruction, request.option_id)

        # 记录重翻前的译文
        old_translation = None
        latest = target_paragraph.latest_translation(non_empty=True)
        if latest is not None:
            old_translation = latest.text

        timeout_s = TimeoutConfig.get_timeout("longform")
        agent = TranslationAgent(llm, timeout=timeout_s)
        formatted_instruction = build_retranslate_instruction(
            instruction,
            target_paragraph.source,
            get_latest_translation_text(target_paragraph),
        )
        payload = agent.retranslate_paragraph(
            target_paragraph,
            context,
            instruction=formatted_instruction,
        )
        apply_translation_payload(target_paragraph, payload, "default")

        pm.save_section(project_id, target_section)
        await service.invalidate_project_cache(project_id)

        # 自学习：从重翻指令中后台提取风格偏好规则
        if instruction and old_translation:
            asyncio.create_task(
                memory_service.process_retranslation_instruction(
                    instruction,
                    target_paragraph.source,
                    old_translation,
                    payload.text,
                )
            )

        new_version_id = f"retranslate_{uuid.uuid4().hex[:8]}"
        version_obj = target_paragraph.latest_translation(non_empty=True)
        created_at = version_obj.created_at if version_obj else datetime.now()

        return {
            "version_id": new_version_id,
            "paragraph_id": paragraph_id,
            "translation": payload.text,
            "instruction": instruction,
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
    llm: LongformLLMProviderDep,
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
                elif para.has_draft_translation():
                    trans_list.append(para.latest_translation_text(non_empty=True) or "")
                else:
                    trans_list.append("")
            translations[section.section_id] = trans_list

        reviewer = ConsistencyReviewer(llm)
        analysis = _load_latest_article_analysis(pm, project_id)
        report = reviewer.review(
            sections,
            translations,
            article_analysis=analysis,
        )

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


@router.get("/{project_id}/consistency-report")
async def get_latest_consistency_report(
    project_id: str,
    pm: ProjectManagerDep,
):
    try:
        pm.get(project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")

    runs_root = Path(pm.projects_path) / project_id / "artifacts" / "runs"
    if not runs_root.exists():
        return {
            "project_id": project_id,
            "report": None,
            "message": "暂无运行报告",
        }

    run_dirs = sorted(
        (path for path in runs_root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for run_dir in run_dirs:
        summary_path = run_dir / "run-summary.json"
        if not summary_path.exists():
            continue
        try:
            with open(summary_path, "r", encoding="utf-8") as handle:
                summary = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue

        consistency = summary.get("consistency")
        if not consistency:
            continue

        issues = [
            {
                "section_id": item.get("section_id", ""),
                "paragraph_index": item.get("paragraph_index", 0),
                "issue_type": item.get("issue_type", ""),
                "description": item.get("description", ""),
                "auto_fixable": item.get("auto_fixable", False),
                "fix_suggestion": item.get("fix_suggestion"),
            }
            for item in consistency.get("issues", [])
        ]
        filtered_issues = _filter_consistency_issues(issues)
        report = {
            "is_consistent": len(filtered_issues) == 0,
            "issue_count": len(filtered_issues),
            "total_issues": len(filtered_issues),
            "auto_fixable_count": sum(1 for issue in filtered_issues if issue.get("auto_fixable")),
            "manual_review_count": sum(1 for issue in filtered_issues if not issue.get("auto_fixable")),
            "issues": filtered_issues,
        }
        return {
            "project_id": project_id,
            "report": report,
            "run_id": summary.get("run_id") or run_dir.name,
            "status": summary.get("status"),
            "started_at": summary.get("started_at"),
            "finished_at": summary.get("finished_at"),
            "artifacts_path": summary.get("artifacts_path"),
            "source": "latest_run_summary",
        }

    return {
        "project_id": project_id,
        "report": None,
        "message": "暂无一致性报告",
    }


# ============ 翻译规则管理 API（全局） ============


from pydantic import BaseModel


class AddRuleRequest(BaseModel):
    text: str


@router.get("/translation-rules")
async def get_translation_rules(
    memory_service: MemoryServiceDep,
):
    """查看所有全局翻译规则"""
    rules = memory_service.get_all_rules()
    return {
        "rules": [
            {"index": i, "text": r}
            for i, r in enumerate(rules)
        ],
        "total": len(rules),
    }


@router.delete("/translation-rules/{rule_index}")
async def delete_translation_rule(
    rule_index: int,
    memory_service: MemoryServiceDep,
):
    """删除指定索引的全局翻译规则"""
    deleted = memory_service.delete_rule_by_index(rule_index)
    if not deleted:
        raise NotFoundException(detail=f"Rule at index {rule_index} not found")
    return {"deleted": True, "index": rule_index}


@router.post("/translation-rules")
async def add_translation_rule(
    request: AddRuleRequest,
    memory_service: MemoryServiceDep,
):
    """手动添加一条全局翻译规则"""
    text = request.text.strip()
    if not text:
        raise BadRequestException(detail="Rule text cannot be empty")
    memory_service.add_rule_manually(text)
    return {"added": True, "text": text}
