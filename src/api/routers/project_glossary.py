"""Project glossary and terminology review router."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Literal, Optional
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field, field_validator, model_validator

from src.api.dependencies import (
    GlossaryManagerDep,
    LongformLLMProviderDep,
    ProjectManagerDep,
)
from src.api.middleware import BadRequestException, ConflictException, NotFoundException
from src.api.utils.concurrency import run_blocking
from src.api.utils.llm_factory import create_llm_provider
from src.core.glossary import infer_glossary_tags, normalize_glossary_tags
from src.core.models import GlossaryTerm, TranslationStrategy
from src.services.terminology_review_job_service import (
    ActiveTerminologyReviewModelConflict,
    TerminologyReviewJobStore,
)
from src.services.terminology_review_service import (
    TerminologyReviewService,
    TermReviewArtifactConflict,
)


router = APIRouter(prefix="", tags=["projects"])
logger = logging.getLogger(__name__)
_term_review_tasks: Dict[str, asyncio.Task[None]] = {}


class AddTermRequest(BaseModel):
    original: str = Field(..., min_length=1, max_length=500)
    translation: Optional[str] = Field(None, max_length=500)
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default_factory=list, max_length=50)
    status: str = Field(default="active", max_length=50)


class UpdateTermRequest(BaseModel):
    translation: Optional[str] = Field(None, max_length=500)
    strategy: Optional[TranslationStrategy] = None
    note: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)


class BatchGlossaryRequest(BaseModel):
    originals: List[str] = Field(default_factory=list, max_length=200)
    action: Literal[
        "delete",
        "set_status",
        "set_strategy",
        "add_tags",
        "replace_tags",
        "remove_tags",
    ]
    status: Optional[str] = Field(None, max_length=50)
    strategy: Optional[TranslationStrategy] = None
    tags: List[str] = Field(default_factory=list, max_length=50)


class MatchTermsRequest(BaseModel):
    paragraph: str = Field(..., min_length=1, max_length=50000)
    max_terms: int = Field(default=20, ge=1, le=100)


class TermReviewDecisionRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=500)
    action: Literal["accept", "custom", "skip"]
    translation: Optional[str] = Field(None, max_length=500)
    note: Optional[str] = Field(None, max_length=2000)
    first_occurrence: Optional[str] = Field(None, max_length=1000)

    @field_validator("term")
    @classmethod
    def validate_term(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Term must not be blank")
        return value

    @model_validator(mode="after")
    def validate_translation(self):
        if self.translation is not None:
            self.translation = self.translation.strip() or None
        if self.action != "skip" and not self.translation:
            raise ValueError("Accepted and custom terms require a translation")
        return self


class SubmitTermReviewRequest(BaseModel):
    artifact_id: Optional[str] = Field(None, min_length=1, max_length=128)
    decisions: List[TermReviewDecisionRequest] = Field(
        ...,
        min_length=1,
        max_length=500,
    )


class CheckConflictRequest(BaseModel):
    original: str = Field(..., min_length=1, max_length=500)
    translation: Optional[str] = Field(None, max_length=500)


class PrepareTermReviewRequest(BaseModel):
    model: Optional[str] = Field(None, max_length=100)


async def _run_term_review_job(
    *,
    job_store: TerminologyReviewJobStore,
    job_id: str,
    project_id: str,
    service: TerminologyReviewService,
) -> None:
    try:
        await run_blocking(job_store.mark_running, project_id, job_id)
        result = await run_blocking(
            service.prepare_review,
            project_id,
            artifact_id=job_id,
        )
        await run_blocking(
            job_store.mark_succeeded,
            project_id,
            job_id,
            result,
        )
    except asyncio.CancelledError:
        await run_blocking(
            job_store.mark_failed,
            project_id,
            job_id,
            "Terminology review job stopped before completion.",
        )
        raise
    except Exception as exc:
        logger.exception(
            "Terminology review job %s failed for project %s",
            job_id,
            project_id,
        )
        await run_blocking(
            job_store.mark_failed,
            project_id,
            job_id,
            str(exc),
        )


def _normalize_tags(tags: Optional[List[str]]) -> List[str]:
    return normalize_glossary_tags(tags)


def _initial_tags(original: str, tags: Optional[List[str]]) -> List[str]:
    normalized = _normalize_tags(tags)
    if normalized:
        return normalized
    return infer_glossary_tags(original)


def _apply_term_updates(existing: GlossaryTerm, request: UpdateTermRequest) -> GlossaryTerm:
    fields_set = request.model_fields_set
    updated = existing.model_copy(deep=True)

    if "translation" in fields_set:
        updated.translation = request.translation
    if "strategy" in fields_set and request.strategy is not None:
        updated.strategy = request.strategy
    if "note" in fields_set:
        updated.note = request.note
    if "tags" in fields_set:
        updated.tags = _normalize_tags(request.tags)
    if "status" in fields_set and request.status is not None:
        updated.status = request.status

    updated.updated_at = datetime.now()
    return updated


def _apply_batch_action(glossary, request: BatchGlossaryRequest) -> tuple[list[GlossaryTerm], int]:
    originals = {item.strip().lower() for item in request.originals if item.strip()}
    matched = [term for term in glossary.terms if term.original.lower() in originals]

    if request.action == "delete":
        glossary.terms = [term for term in glossary.terms if term.original.lower() not in originals]
        return [], len(matched)

    if request.action == "set_status" and request.status is None:
        raise ValueError("Batch action 'set_status' requires status")
    if request.action == "set_strategy" and request.strategy is None:
        raise ValueError("Batch action 'set_strategy' requires strategy")

    normalized_tags = _normalize_tags(request.tags)
    if request.action in {"add_tags", "replace_tags", "remove_tags"} and not normalized_tags:
        raise ValueError(f"Batch action '{request.action}' requires tags")

    updated_terms: list[GlossaryTerm] = []
    for term in matched:
        updated = term.model_copy(deep=True)
        if request.action == "set_status":
            updated.status = request.status or updated.status
        elif request.action == "set_strategy":
            updated.strategy = request.strategy or updated.strategy
        elif request.action == "add_tags":
            updated.tags = _normalize_tags([*updated.tags, *normalized_tags])
        elif request.action == "replace_tags":
            updated.tags = normalized_tags
        elif request.action == "remove_tags":
            removed = {tag.lower() for tag in normalized_tags}
            updated.tags = [tag for tag in updated.tags if tag.lower() not in removed]
        updated.updated_at = datetime.now()
        glossary.add_term(updated)
        updated_terms.append(updated)

    return updated_terms, len(matched)


@router.get("/projects/{project_id}/glossary")
async def get_project_glossary(project_id: str, gm: GlossaryManagerDep):
    try:
        def load_glossary() -> dict:
            glossary = gm.load_project(project_id)
            global_glossary = gm.load_global()
            global_terms = {
                term.original.lower(): term
                for term in global_glossary.terms
            }
            visible_terms = []
            for term in glossary.terms:
                global_term = global_terms.get(term.original.lower())
                is_inherited_seed = (
                    global_term is not None
                    and global_term.translation == term.translation
                    and global_term.strategy == term.strategy
                    and (global_term.note or "") == (term.note or "")
                    and list(global_term.tags) == list(term.tags)
                    and (global_term.status or "active")
                    == (term.status or "active")
                )
                if not is_inherited_seed:
                    visible_terms.append(term)
            return {
                "version": glossary.version,
                "terms": [
                    term.model_dump(mode="json")
                    for term in visible_terms
                ],
            }

        return await run_blocking(load_glossary)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.put("/projects/{project_id}/glossary")
async def update_project_glossary(
    project_id: str,
    request: AddTermRequest,
    gm: GlossaryManagerDep,
):
    try:
        def add_term() -> dict:
            with gm.project_lock(project_id):
                glossary = gm.load_project(project_id)
                term = GlossaryTerm(
                    original=request.original,
                    translation=request.translation,
                    strategy=request.strategy,
                    note=request.note,
                    tags=_initial_tags(request.original, request.tags),
                    scope="project",
                    source="manual",
                    status=request.status,
                )
                glossary.add_term(term)
                gm.save_project(project_id, glossary)
            return {
                "message": "Term added",
                "term": term.model_dump(mode="json"),
            }

        return await run_blocking(add_term)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.put("/projects/{project_id}/glossary/terms/{original}")
async def update_glossary_term(
    project_id: str,
    original: str,
    request: UpdateTermRequest,
    gm: GlossaryManagerDep,
):
    try:
        original_decoded = unquote(original)

        def update_term() -> dict:
            with gm.project_lock(project_id):
                glossary = gm.load_project(project_id)
                existing = glossary.get_term(original_decoded)
                if not existing:
                    raise NotFoundException(
                        detail=f"Term '{original_decoded}' not found in glossary"
                    )

                updated_term = _apply_term_updates(existing, request)
                glossary.add_term(updated_term)
                gm.save_project(project_id, glossary)
            return {
                "message": "Term updated",
                "term": updated_term.model_dump(mode="json"),
            }

        return await run_blocking(update_term)
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.delete("/projects/{project_id}/glossary/terms/{original}")
async def delete_glossary_term(
    project_id: str,
    original: str,
    gm: GlossaryManagerDep,
):
    try:
        original_decoded = unquote(original)

        def delete_term() -> dict:
            with gm.project_lock(project_id):
                glossary = gm.load_project(project_id)
                original_lower = original_decoded.lower()
                filtered_terms = [
                    term
                    for term in glossary.terms
                    if term.original.lower() != original_lower
                ]
                if len(filtered_terms) == len(glossary.terms):
                    raise NotFoundException(
                        detail=f"Term '{original_decoded}' not found in glossary"
                    )
                glossary.terms = filtered_terms
                gm.save_project(project_id, glossary)
            return {"message": "Term deleted", "original": original_decoded}

        return await run_blocking(delete_term)
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/batch")
async def batch_update_project_glossary(
    project_id: str,
    request: BatchGlossaryRequest,
    gm: GlossaryManagerDep,
):
    try:
        def update_batch() -> dict:
            with gm.project_lock(project_id):
                glossary = gm.load_project(project_id)
                updated_terms, matched_count = _apply_batch_action(
                    glossary,
                    request,
                )
                gm.save_project(project_id, glossary)
            return {
                "message": "Batch action applied",
                "action": request.action,
                "matched_count": matched_count,
                "updated_count": len(updated_terms),
                "terms": [
                    term.model_dump(mode="json")
                    for term in updated_terms
                ],
                "originals": request.originals,
            }

        return await run_blocking(update_batch)
    except ValueError as exc:
        raise BadRequestException(detail=str(exc))
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/check-conflict")
async def check_term_conflict(
    project_id: str,
    request: CheckConflictRequest,
    gm: GlossaryManagerDep,
):
    try:
        def check_conflicts() -> dict:
            project_glossary = gm.load_project(project_id)
            global_glossary = gm.load_global()

            conflicts = []
            for scope, glossary in [
                ("project", project_glossary),
                ("global", global_glossary),
            ]:
                existing = glossary.get_term(request.original)
                if existing and existing.translation != request.translation:
                    conflicts.append(
                        {
                            "scope": scope,
                            "existing_translation": existing.translation,
                            "existing_strategy": existing.strategy.value,
                            "existing_note": existing.note,
                        }
                    )

            return {
                "has_conflict": bool(conflicts),
                "conflicts": conflicts,
            }

        return await run_blocking(check_conflicts)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/match")
async def match_paragraph_terms(
    project_id: str,
    request: MatchTermsRequest,
    gm: GlossaryManagerDep,
):
    try:
        def match_terms() -> dict:
            from src.core.glossary import create_default_global_glossary
            from src.core.term_matcher import TermMatcher

            glossary = gm.load_merged(project_id)
            if not glossary.terms:
                glossary = create_default_global_glossary()

            matcher = TermMatcher(glossary)
            matches = matcher.match_paragraph(
                request.paragraph,
                request.max_terms,
            )
            return {
                "total_terms": len(glossary.terms),
                "matched_count": len(matches),
                "matches": [
                    {
                        "original": match.term.original,
                        "translation": match.term.translation,
                        "strategy": match.term.strategy.value,
                        "note": match.term.note,
                        "score": match.score,
                        "match_type": match.match_type,
                    }
                    for match in matches
                ],
            }

        return await run_blocking(match_terms)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/term-review/prepare")
async def prepare_term_review(
    project_id: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
    request: PrepareTermReviewRequest = Body(default_factory=PrepareTermReviewRequest),
):
    try:
        if request.model:
            llm = create_llm_provider(provider=request.model)

        service = TerminologyReviewService(
            llm_provider=llm,
            project_manager=pm,
            glossary_manager=gm,
        )
        return await run_blocking(service.prepare_review, project_id)
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/term-review/jobs", status_code=202)
async def start_term_review_job(
    project_id: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LongformLLMProviderDep,
    request: PrepareTermReviewRequest = Body(default_factory=PrepareTermReviewRequest),
):
    """Start terminology preparation without keeping the HTTP request open."""
    try:
        await run_blocking(pm.get, project_id)
        job_store = TerminologyReviewJobStore(pm.projects_path)
        job, created = await run_blocking(
            job_store.create_or_get_active,
            project_id,
            request.model,
        )
        if not created:
            existing_task = _term_review_tasks.get(job["job_id"])
            if existing_task is not None and not existing_task.done():
                return job
            await run_blocking(
                job_store.mark_failed,
                project_id,
                job["job_id"],
                "Terminology review task is no longer running.",
            )
            job, created = await run_blocking(
                job_store.create_or_get_active,
                project_id,
                request.model,
            )
            if not created:
                return job
        if request.model:
            llm = create_llm_provider(provider=request.model)
        service = TerminologyReviewService(
            llm_provider=llm,
            project_manager=pm,
            glossary_manager=gm,
        )
        task = asyncio.create_task(
            _run_term_review_job(
                job_store=job_store,
                job_id=job["job_id"],
                project_id=project_id,
                service=service,
            )
        )
        _term_review_tasks[job["job_id"]] = task
        task.add_done_callback(
            lambda _task, job_id=job["job_id"]: _term_review_tasks.pop(job_id, None)
        )
        return job
    except ActiveTerminologyReviewModelConflict as exc:
        raise ConflictException(
            detail=str(exc),
            error_code="TERM_REVIEW_MODEL_CONFLICT",
        ) from exc
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/projects/{project_id}/term-review/jobs/{job_id}")
async def get_term_review_job(
    project_id: str,
    job_id: UUID,
    pm: ProjectManagerDep,
):
    """Return persisted state and, when complete, the prepared review payload."""
    try:
        job_store = TerminologyReviewJobStore(pm.projects_path)
        return await run_blocking(job_store.get, project_id, job_id.hex)
    except FileNotFoundError:
        raise NotFoundException(detail="Terminology review job not found")


@router.post("/projects/{project_id}/term-review/submit")
async def submit_term_review(
    project_id: str,
    request: SubmitTermReviewRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
):
    try:
        service = TerminologyReviewService(
            project_manager=pm,
            glossary_manager=gm,
        )
        return await run_blocking(
            service.apply_review,
            project_id,
            [decision.model_dump() for decision in request.decisions],
            artifact_id=request.artifact_id,
        )
    except TermReviewArtifactConflict as exc:
        raise ConflictException(
            detail=str(exc),
            error_code="TERM_REVIEW_ARTIFACT_CONFLICT",
        ) from exc
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/projects/{project_id}/glossary/recommendations")
async def get_project_glossary_recommendations(
    project_id: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
):
    try:
        service = TerminologyReviewService(
            project_manager=pm,
            glossary_manager=gm,
        )
        return await run_blocking(
            service.get_project_recommendations,
            project_id,
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/terms/{original}/promote")
async def promote_project_term(
    project_id: str,
    original: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
):
    try:
        service = TerminologyReviewService(
            project_manager=pm,
            glossary_manager=gm,
        )
        return await run_blocking(
            service.promote_project_term,
            project_id,
            unquote(original),
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project or term not found")
