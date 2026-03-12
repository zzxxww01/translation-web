"""Project glossary and terminology review router."""

from datetime import datetime
from typing import List, Literal, Optional
from urllib.parse import unquote

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.api.dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep
from src.api.middleware import BadRequestException, NotFoundException
from src.core.glossary import infer_glossary_tags, normalize_glossary_tags
from src.core.models import GlossaryTerm, TranslationStrategy
from src.services.terminology_review_service import TerminologyReviewService


router = APIRouter(prefix="", tags=["projects"])


class AddTermRequest(BaseModel):
    original: str
    translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    status: str = "active"


class UpdateTermRequest(BaseModel):
    translation: Optional[str] = None
    strategy: Optional[TranslationStrategy] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class BatchGlossaryRequest(BaseModel):
    originals: List[str] = Field(default_factory=list)
    action: Literal[
        "delete",
        "set_status",
        "set_strategy",
        "add_tags",
        "replace_tags",
        "remove_tags",
    ]
    status: Optional[str] = None
    strategy: Optional[TranslationStrategy] = None
    tags: List[str] = Field(default_factory=list)


class MatchTermsRequest(BaseModel):
    paragraph: str
    max_terms: int = 20


class TermReviewDecisionRequest(BaseModel):
    term: str
    action: Literal["accept", "custom", "skip"]
    translation: Optional[str] = None
    note: Optional[str] = None
    first_occurrence: Optional[str] = None


class SubmitTermReviewRequest(BaseModel):
    decisions: List[TermReviewDecisionRequest]


class CheckConflictRequest(BaseModel):
    original: str
    translation: Optional[str] = None


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
        glossary = gm.load_project(project_id)
        global_glossary = gm.load_global()
        visible_terms = []
        for term in glossary.terms:
            global_term = global_glossary.get_term(term.original)
            is_inherited_seed = (
                global_term is not None
                and global_term.translation == term.translation
                and global_term.strategy == term.strategy
                and (global_term.note or "") == (term.note or "")
                and list(global_term.tags) == list(term.tags)
                and (global_term.status or "active") == (term.status or "active")
            )
            if is_inherited_seed:
                continue
            visible_terms.append(term)
        return {
            "version": glossary.version,
            "terms": [term.model_dump(mode="json") for term in visible_terms],
        }
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.put("/projects/{project_id}/glossary")
async def update_project_glossary(
    project_id: str,
    request: AddTermRequest,
    gm: GlossaryManagerDep,
):
    try:
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
        return {"message": "Term added", "term": term.model_dump(mode="json")}
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
        glossary = gm.load_project(project_id)
        existing = glossary.get_term(original_decoded)
        if not existing:
            raise NotFoundException(detail=f"Term '{original_decoded}' not found in glossary")

        updated_term = _apply_term_updates(existing, request)
        glossary.add_term(updated_term)
        gm.save_project(project_id, glossary)
        return {"message": "Term updated", "term": updated_term.model_dump(mode="json")}
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
        glossary = gm.load_project(project_id)
        original_lower = original_decoded.lower()
        filtered_terms = [term for term in glossary.terms if term.original.lower() != original_lower]
        if len(filtered_terms) == len(glossary.terms):
            raise NotFoundException(detail=f"Term '{original_decoded}' not found in glossary")
        glossary.terms = filtered_terms
        gm.save_project(project_id, glossary)
        return {"message": "Term deleted", "original": original_decoded}
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
        glossary = gm.load_project(project_id)
        updated_terms, matched_count = _apply_batch_action(glossary, request)
        gm.save_project(project_id, glossary)
        return {
            "message": "Batch action applied",
            "action": request.action,
            "matched_count": matched_count,
            "updated_count": len(updated_terms),
            "terms": [term.model_dump(mode="json") for term in updated_terms],
            "originals": request.originals,
        }
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
        project_glossary = gm.load_project(project_id)
        global_glossary = gm.load_global()

        conflicts = []
        for scope, glossary in [("project", project_glossary), ("global", global_glossary)]:
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
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
        }
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/match")
async def match_paragraph_terms(
    project_id: str,
    request: MatchTermsRequest,
    gm: GlossaryManagerDep,
):
    try:
        from src.core.glossary import create_default_global_glossary
        from src.core.term_matcher import TermMatcher

        glossary = gm.load_merged(project_id)
        if not glossary.terms:
            global_glossary = gm.load_global()
            if not global_glossary.terms:
                global_glossary = create_default_global_glossary()
            glossary = global_glossary

        matcher = TermMatcher(glossary)
        matches = matcher.match_paragraph(request.paragraph, request.max_terms)
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
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/term-review/prepare")
async def prepare_term_review(
    project_id: str,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
    llm: LLMProviderDep,
):
    try:
        service = TerminologyReviewService(
            llm_provider=llm,
            project_manager=pm,
            glossary_manager=gm,
        )
        return service.prepare_review(project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


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
        return service.apply_review(
            project_id,
            [decision.model_dump() for decision in request.decisions],
        )
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
        return service.get_project_recommendations(project_id)
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
        return service.promote_project_term(project_id, unquote(original))
    except FileNotFoundError:
        raise NotFoundException(detail="Project or term not found")
