"""
Confirmation translation/review endpoints.
"""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Body, Request

from src.agents.translation import TranslationAgent, TranslationContext
from src.config.timeout_config import TimeoutConfig
from src.settings import settings
from src.core.glossary_prompt import build_term_usage_from_project
from src.core.models import ArticleAnalysis, ParagraphStatus
from src.core.project import ConcurrentParagraphUpdateError
from src.api.utils.concurrency import run_blocking
from src.api.utils.llm_factory import create_llm_provider
from src.api.utils.glossary import get_combined_glossary
from src.services.batch_translation_service import BatchTranslationService
from src.services.terminology_review_job_service import (
    ActiveTerminologyReviewModelConflict,
    TerminologyReviewJobStore,
)
from src.services.terminology_review_service import (
    TermReviewArtifactConflict,
    TerminologyReviewService,
)

from ..dependencies import (
    ProjectManagerDep,
    LongformLLMProviderDep,
    BatchServiceDep,
    ConfirmationServiceDep,
    MemoryServiceDep,
    TranslationStatusServiceDep,
)
from ..middleware import BadRequestException, ConflictException, NotFoundException
from ..middleware.rate_limit import limiter
from .confirmation_models import (
    ConfirmParagraphRequest,
    UpdateTermsRequest,
    RetranslateRequest,
    RETRANSLATE_OPTIONS,
    resolve_retranslate_instruction,
)
from .project_glossary import ensure_term_review_job
from .translate_models import LongformWorkflowStartRequest
from .translate_utils import build_retranslate_instruction, get_latest_translation_text


router = APIRouter()
logger = logging.getLogger(__name__)

# Background translations started by the confirmation workflow must outlive the
# request that acknowledged them. Keeping strong references also prevents an
# unobserved task from being garbage-collected after the browser navigates away.
_confirmation_translation_tasks: set[asyncio.Task] = set()
_longform_workflow_tasks: set[asyncio.Task] = set()

ALLOWED_CONSISTENCY_ISSUE_TYPES = {"terminology"}


def _build_auto_term_review_decisions(review: Dict[str, Any]) -> list[dict]:
    """Accept the current suggestions once the human confirmation window ends."""
    decisions: list[dict] = []
    seen: set[str] = set()
    for section in review.get("sections") or []:
        for candidate in section.get("candidates") or []:
            term = str(candidate.get("term") or "").strip()
            if not term:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            translation = str(
                candidate.get("suggested_translation") or ""
            ).strip()
            decision = {
                "term": term,
                "action": "accept" if translation else "skip",
                "translation": translation or None,
                "first_occurrence": candidate.get("first_occurrence"),
            }
            decisions.append(decision)
    return decisions


def _build_longform_service(
    base_service: BatchTranslationService,
    body: LongformWorkflowStartRequest,
) -> BatchTranslationService:
    if body.model:
        llm = create_llm_provider(provider=body.model)
        analysis_llm = llm
    else:
        llm = base_service.llm
        analysis_llm = base_service.analysis_llm
    translation_mode = (
        BatchTranslationService.TRANSLATION_MODE_FOUR_STEP
        if body.method == "four-step"
        else BatchTranslationService.TRANSLATION_MODE_SECTION
    )
    return BatchTranslationService(
        llm_provider=llm,
        project_manager=base_service.project_manager,
        translation_mode=translation_mode,
        max_concurrent_sections=10,
        analysis_llm_provider=analysis_llm,
        user_model_override=body.model,
    )


async def _run_longform_workflow(
    *,
    project_id: str,
    lease_id: str,
    term_review_job_id: str,
    translation_service: BatchTranslationService,
    confirmation_timeout_seconds: float,
    poll_interval_seconds: float = 1.0,
) -> None:
    """Own the pre-review gate and translation independently of any browser."""
    project_manager = translation_service.project_manager
    job_store = TerminologyReviewJobStore(project_manager.projects_path)
    review_service = TerminologyReviewService(
        project_manager=project_manager,
        glossary_manager=project_manager.glossary_manager,
    )

    def cancelled() -> bool:
        return translation_service._is_cancelled(project_id)

    try:
        job: Dict[str, Any]
        while True:
            if cancelled():
                await asyncio.to_thread(
                    job_store.mark_confirmation_resolved,
                    project_id,
                    term_review_job_id,
                    "cancelled",
                )
                return
            job = await asyncio.to_thread(
                job_store.get,
                project_id,
                term_review_job_id,
            )
            if job.get("status") not in {"queued", "running"}:
                break
            await asyncio.sleep(poll_interval_seconds)

        if job.get("status") == "succeeded":
            review = job.get("result") or {}
            review_required = bool(
                review.get("review_required")
                and int(review.get("total_candidates") or 0) > 0
            )
            if review_required:
                translation_service._set_active_run(
                    project_id,
                    run_id=term_review_job_id,
                    status="starting",
                    current_step="等待术语确认",
                )
                await asyncio.to_thread(
                    job_store.mark_waiting_confirmation,
                    project_id,
                    term_review_job_id,
                    timeout_seconds=max(1, int(confirmation_timeout_seconds)),
                )
                logger.info(
                    "[%s] Waiting up to %.1fs for terminology confirmation",
                    project_id,
                    confirmation_timeout_seconds,
                )
                loop = asyncio.get_running_loop()
                deadline = loop.time() + confirmation_timeout_seconds
                while True:
                    if cancelled():
                        await asyncio.to_thread(
                            job_store.mark_confirmation_resolved,
                            project_id,
                            term_review_job_id,
                            "cancelled",
                        )
                        return
                    current = await asyncio.to_thread(
                        job_store.get,
                        project_id,
                        term_review_job_id,
                    )
                    if current.get("confirmation_status") == "submitted":
                        break
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        decisions = _build_auto_term_review_decisions(review)
                        if decisions:
                            try:
                                await asyncio.to_thread(
                                    review_service.apply_review,
                                    project_id,
                                    decisions,
                                    artifact_id=term_review_job_id,
                                )
                            except TermReviewArtifactConflict:
                                # A human submission can win the artifact lock at
                                # the exact timeout boundary. Either winner is a
                                # valid release of the gate, so continue once.
                                logger.info(
                                    "[%s] Terminology review was resolved while the auto-accept ran",
                                    project_id,
                                )
                            except Exception:
                                logger.exception(
                                    "[%s] Failed to auto-accept terminology; continuing with the persisted glossary",
                                    project_id,
                                )
                                await asyncio.to_thread(
                                    job_store.mark_confirmation_resolved,
                                    project_id,
                                    term_review_job_id,
                                    "auto_apply_failed",
                                )
                            else:
                                await asyncio.to_thread(
                                    job_store.mark_confirmation_resolved,
                                    project_id,
                                    term_review_job_id,
                                    "auto_accepted",
                                )
                        else:
                            await asyncio.to_thread(
                                job_store.mark_confirmation_resolved,
                                project_id,
                                term_review_job_id,
                                "auto_skipped",
                            )
                        break
                    await asyncio.sleep(min(poll_interval_seconds, remaining))
            else:
                translation_service._set_active_run(
                    project_id,
                    run_id=term_review_job_id,
                    status="starting",
                    current_step="术语预检完成，准备翻译",
                )
                await asyncio.to_thread(
                    job_store.mark_confirmation_resolved,
                    project_id,
                    term_review_job_id,
                    "not_required",
                )
        else:
            translation_service._set_active_run(
                project_id,
                run_id=term_review_job_id,
                status="starting",
                current_step="术语预检失败，继续翻译",
            )
            logger.warning(
                "[%s] Terminology preparation failed; translation will continue: %s",
                project_id,
                job.get("error") or "unknown error",
            )
            await asyncio.to_thread(
                job_store.mark_confirmation_resolved,
                project_id,
                term_review_job_id,
                "preparation_failed",
            )

        if cancelled():
            return

        translation_service._set_active_run(
            project_id,
            run_id=term_review_job_id,
            status="starting",
            current_step="开始全文翻译",
        )

        def _run_translation_in_thread() -> Dict[str, Any]:
            async def _runner() -> Dict[str, Any]:
                return await translation_service.translate_project(project_id)

            return asyncio.run(_runner())

        await asyncio.to_thread(_run_translation_in_thread)
    except asyncio.CancelledError:
        logger.warning(
            "[%s] Long-form workflow stopped because the API process is shutting down",
            project_id,
        )
        raise
    except Exception:
        logger.exception("[%s] Long-form background workflow failed", project_id)
    finally:
        translation_service._clear_cancelled(project_id)
        translation_service._release_active_run(
            project_id,
            lease_id=lease_id,
        )


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


def _prepare_retranslation_sync(
    sections,
    glossary,
    learned_rules,
    paragraph_id: str,
):
    """Locate a paragraph and build its project-wide prompt context off-loop."""
    target_section = None
    target_paragraph = None
    target_local_index = None

    for section in sections:
        for index, paragraph in enumerate(section.paragraphs):
            if paragraph.id == paragraph_id:
                target_section = section
                target_paragraph = paragraph
                target_local_index = index
                break
        if target_paragraph is not None:
            break

    if (
        target_paragraph is None
        or target_section is None
        or target_local_index is None
    ):
        raise NotFoundException(detail="Paragraph not found")

    context = TranslationContext(glossary=glossary, learned_rules=learned_rules)
    context.previous_paragraphs = [
        (paragraph.source, translation)
        for paragraph in target_section.paragraphs[:target_local_index]
        if (translation := paragraph.best_translation_text())
    ][-5:]
    context.next_preview = [
        paragraph.source
        for paragraph in target_section.paragraphs[
            target_local_index + 1 : target_local_index + 3
        ]
    ]
    context.term_usage = build_term_usage_from_project(
        sections,
        glossary,
        current_section_id=target_section.section_id,
        current_paragraph_id=paragraph_id,
    )
    latest = target_paragraph.latest_translation(non_empty=True)
    old_translation = latest.text if latest is not None else None

    return (
        target_section.section_id,
        target_paragraph,
        target_paragraph.model_copy(deep=True),
        context,
        old_translation,
    )


def _run_consistency_review_sync(project_id: str, pm, llm) -> dict:
    from src.agents.consistency_reviewer import ConsistencyReviewer

    sections = pm.get_sections(project_id)
    translations = {}
    for section in sections:
        translations[section.section_id] = [
            (
                paragraph.confirmed
                if paragraph.confirmed
                else (
                    paragraph.latest_translation_text(non_empty=True) or ""
                    if paragraph.has_draft_translation()
                    else ""
                )
            )
            for paragraph in section.paragraphs
        ]

    report = ConsistencyReviewer(llm).review(
        sections,
        translations,
        article_analysis=_load_latest_article_analysis(pm, project_id),
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
                "section_id": issue.section_id,
                "paragraph_index": issue.paragraph_index,
                "issue_type": issue.issue_type,
                "description": issue.description,
                "auto_fixable": issue.auto_fixable,
                "fix_suggestion": issue.fix_suggestion,
            }
            for issue in report.issues
        ],
    }


def _get_latest_consistency_report_sync(project_id: str, pm) -> dict:
    pm.get(project_id)
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
            "is_consistent": not filtered_issues,
            "issue_count": len(filtered_issues),
            "total_issues": len(filtered_issues),
            "auto_fixable_count": sum(
                1 for issue in filtered_issues if issue.get("auto_fixable")
            ),
            "manual_review_count": sum(
                1 for issue in filtered_issues if not issue.get("auto_fixable")
            ),
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


@router.post("/{project_id}/translate-all")
@limiter.limit("20/minute")
async def start_translation(
    request: Request,
    project_id: str,
    service: BatchServiceDep,
):
    try:
        await asyncio.to_thread(service.project_manager.get, project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")

    slot_claim = await service.claim_translation_slot(project_id)
    if slot_claim["status"] == "busy":
        raise BadRequestException(
            detail=(
                "This project already has an active translation. "
                f"active_run_id={slot_claim.get('active_run_id')}"
            )
        )
    lease_id = str(slot_claim["lease_id"])

    def _run_translation_in_thread():
        async def _runner():
            return await service.translate_project(project_id)

        return asyncio.run(_runner())

    async def _run_translation_background() -> None:
        try:
            # translate_project 内部仍含同步 LLM 链路，整段放到工作线程；HTTP
            # 请求只负责成功取得项目租约并立即确认启动。
            await asyncio.to_thread(_run_translation_in_thread)
        except Exception:
            logger.exception(
                "[%s] Confirmation workflow background translation failed",
                project_id,
            )
        finally:
            # translate_project 正常终止时会按 run_id 释放；这里再按原 lease
            # 兜底，覆盖项目读取/工件初始化等进入主 try 之前的失败。
            service._release_active_run(project_id, lease_id=lease_id)

    try:
        task = asyncio.create_task(
            _run_translation_background(),
            name=f"confirmation-translation:{project_id}",
        )
    except Exception:
        service._release_active_run(project_id, lease_id=lease_id)
        raise
    _confirmation_translation_tasks.add(task)
    task.add_done_callback(_confirmation_translation_tasks.discard)
    return {
        "status": "started",
        "project_id": project_id,
        "run_id": slot_claim.get("run_id"),
    }


@router.post("/{project_id}/translation-workflow", status_code=202)
@limiter.limit("3/minute")
async def start_longform_workflow(
    request: Request,
    project_id: str,
    service: BatchServiceDep,
    body: LongformWorkflowStartRequest = Body(
        default_factory=LongformWorkflowStartRequest
    ),
):
    """Start a server-owned terminology-review and translation workflow."""
    try:
        await asyncio.to_thread(service.project_manager.get, project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")

    translation_service = await asyncio.to_thread(
        _build_longform_service,
        service,
        body,
    )
    slot_claim = await translation_service.claim_translation_slot(project_id)
    if slot_claim["status"] == "busy":
        raise ConflictException(
            detail=(
                "This project already has an active long-form workflow. "
                f"active_run_id={slot_claim.get('active_run_id')}"
            )
        )
    lease_id = str(slot_claim["lease_id"])

    try:
        job = await ensure_term_review_job(
            project_id=project_id,
            pm=translation_service.project_manager,
            gm=translation_service.project_manager.glossary_manager,
            llm=translation_service.llm,
            model=body.model,
        )
        translation_service._set_active_run(
            project_id,
            run_id=job["job_id"],
            status="starting",
            current_step="术语预检中",
        )
        task = asyncio.create_task(
            _run_longform_workflow(
                project_id=project_id,
                lease_id=lease_id,
                term_review_job_id=job["job_id"],
                translation_service=translation_service,
                confirmation_timeout_seconds=(
                    settings.term_review_confirmation_timeout_seconds
                ),
            ),
            name=f"longform-workflow:{project_id}",
        )
    except ActiveTerminologyReviewModelConflict as exc:
        translation_service._release_active_run(
            project_id,
            lease_id=lease_id,
        )
        raise ConflictException(
            detail=str(exc),
            error_code="TERM_REVIEW_MODEL_CONFLICT",
        ) from exc
    except Exception:
        translation_service._release_active_run(
            project_id,
            lease_id=lease_id,
        )
        raise

    _longform_workflow_tasks.add(task)
    task.add_done_callback(_longform_workflow_tasks.discard)
    return {
        "status": "started",
        "project_id": project_id,
        "run_id": job["job_id"],
        "term_review_job_id": job["job_id"],
        "term_review_timeout_seconds": (
            settings.term_review_confirmation_timeout_seconds
        ),
        "method": body.method,
        "model": body.model,
    }


@router.get("/{project_id}/translation-status")
async def get_translation_status(
    project_id: str,
    service: TranslationStatusServiceDep,
):
    try:
        return await service.get_translation_progress(project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"Failed to get status: {str(e)}")


@router.post("/{project_id}/translation-cancel")
@limiter.limit("20/minute")
async def cancel_translation(
    request: Request,
    project_id: str,
    service: TranslationStatusServiceDep,
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
@limiter.limit("20/minute")
async def confirm_paragraph(
    request: Request,
    project_id: str,
    paragraph_id: str,
    body: ConfirmParagraphRequest,
    service: ConfirmationServiceDep,
):
    try:
        return await service.confirm_paragraph(
            project_id,
            paragraph_id,
            body.translation,
            body.version_id,
            body.custom_edit,
        )
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to confirm: {str(e)}")


@router.post("/{project_id}/term-update")
@limiter.limit("20/minute")
async def update_terms(
    request: Request,
    project_id: str,
    body: UpdateTermsRequest,
    service: ConfirmationServiceDep,
):
    try:
        return await service.update_terms(project_id, body.changes)
    except Exception as e:
        raise BadRequestException(detail=f"Failed to update terms: {str(e)}")


@router.post("/{project_id}/paragraph/{paragraph_id}/retranslate")
@limiter.limit("20/minute")
async def retranslate_paragraph(
    request: Request,
    project_id: str,
    paragraph_id: str,
    body: RetranslateRequest,
    pm: ProjectManagerDep,
    llm: LongformLLMProviderDep,
    service: ConfirmationServiceDep,
    memory_service: MemoryServiceDep,
):
    try:
        sections, glossary, learned_rules = await asyncio.gather(
            run_blocking(pm.get_sections, project_id),
            run_blocking(get_combined_glossary, project_id),
            run_blocking(memory_service.get_rules_for_prompt),
        )
        (
            target_section_id,
            target_paragraph,
            expected_paragraph,
            context,
            old_translation,
        ) = await run_blocking(
            _prepare_retranslation_sync,
            sections,
            glossary,
            learned_rules,
            paragraph_id,
        )

        instruction = resolve_retranslate_instruction(body.instruction, body.option_id)

        timeout_s = TimeoutConfig.get_timeout("longform")
        agent = TranslationAgent(llm, timeout=timeout_s)
        formatted_instruction = build_retranslate_instruction(
            instruction,
            target_paragraph.source,
            get_latest_translation_text(target_paragraph),
        )
        payload = await run_blocking(
            agent.retranslate_paragraph,
            target_paragraph,
            context,
            instruction=formatted_instruction,
        )
        target_paragraph = await run_blocking(
            pm.update_paragraph_locked,
            project_id,
            target_section_id,
            paragraph_id,
            translation=payload.text,
            tokenized_text=payload.tokenized_text,
            format_issues=payload.format_issues,
            status=ParagraphStatus.TRANSLATED,
            model="default",
            expected_paragraph=expected_paragraph,
        )
        await service.invalidate_project_cache(project_id)

        # 自学习：从重翻指令中后台提取风格偏好规则
        if instruction and old_translation:
            # 经 _spawn_background 调度并保留强引用，防止后台学习 Task 被 GC 回收
            memory_service._spawn_background(
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
    except ConcurrentParagraphUpdateError as error:
        raise ConflictException(
            detail=(
                f"Paragraph {error.paragraph_id} was edited while translation "
                "was running. Reload it before retrying."
            ),
            error_code="PARAGRAPH_CHANGED",
        )
    except Exception as e:
        raise BadRequestException(detail=f"Failed to retranslate: {str(e)}")


@router.post("/{project_id}/export-translation")
@limiter.limit("20/minute")
async def export_translation(
    request: Request,
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
@limiter.limit("20/minute")
async def export_bilingual(
    request: Request,
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
        return await run_blocking(
            _run_consistency_review_sync,
            project_id,
            pm,
            llm,
        )
    except Exception as e:
        raise BadRequestException(detail=f"Failed to run review: {str(e)}")


@router.get("/{project_id}/consistency-report")
async def get_latest_consistency_report(
    project_id: str,
    pm: ProjectManagerDep,
):
    try:
        return await run_blocking(
            _get_latest_consistency_report_sync,
            project_id,
            pm,
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


# ============ 翻译规则管理 API（全局） ============


from pydantic import BaseModel


class AddRuleRequest(BaseModel):
    text: str


@router.get("/translation-rules")
async def get_translation_rules(
    memory_service: MemoryServiceDep,
):
    """查看所有全局翻译规则"""
    rules = await run_blocking(memory_service.get_all_rules)
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
    deleted = await run_blocking(memory_service.delete_rule_by_index, rule_index)
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
    await run_blocking(memory_service.add_rule_manually, text)
    return {"added": True, "text": text}
