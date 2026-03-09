"""Project glossary and terminology review router."""

from typing import Optional, List, Literal
from urllib.parse import unquote

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.models import GlossaryTerm, TranslationStrategy
from src.api.dependencies import GlossaryManagerDep, LLMProviderDep, ProjectManagerDep
from src.api.middleware import NotFoundException
from src.services.terminology_review_service import TerminologyReviewService


router = APIRouter(prefix="", tags=["projects"])


class AddTermRequest(BaseModel):
    original: str
    translation: Optional[str] = None
    strategy: str = "translate"
    note: Optional[str] = None
    status: str = "active"


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


@router.get("/projects/{project_id}/glossary")
async def get_project_glossary(project_id: str, gm: GlossaryManagerDep):
    try:
        glossary = gm.load_project(project_id)
        global_glossary = gm.load_global("semiconductor")
        visible_terms = []
        for term in glossary.terms:
            global_term = global_glossary.get_term(term.original)
            is_inherited_seed = (
                global_term is not None
                and global_term.translation == term.translation
                and global_term.strategy == term.strategy
                and (global_term.note or "") == (term.note or "")
            )
            if is_inherited_seed:
                continue
            visible_terms.append(term)
        return {
            "version": glossary.version,
            "terms": [t.model_dump(mode="json") for t in visible_terms],
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
            strategy=TranslationStrategy(request.strategy),
            note=request.note,
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
    gm: GlossaryManagerDep,
    translation: Optional[str] = None,
    strategy: str = "translate",
    note: Optional[str] = None,
    status: Optional[str] = None,
):
    try:
        original_decoded = unquote(original)
        glossary = gm.load_project(project_id)
        existing = glossary.get_term(original_decoded)
        if not existing:
            raise NotFoundException(
                detail=f"Term '{original_decoded}' not found in glossary"
            )

        updated_term = GlossaryTerm(
            original=original_decoded,
            translation=translation if translation is not None else existing.translation,
            strategy=TranslationStrategy(strategy) if strategy else existing.strategy,
            note=note if note is not None else existing.note,
            first_occurrence=existing.first_occurrence,
            scope=existing.scope,
            source=existing.source,
            status=status if status is not None else existing.status,
        )
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
        filtered_terms = [t for t in glossary.terms if t.original.lower() != original_lower]
        if len(filtered_terms) == len(glossary.terms):
            raise NotFoundException(
                detail=f"Term '{original_decoded}' not found in glossary"
            )
        glossary.terms = filtered_terms
        gm.save_project(project_id, glossary)
        return {"message": "Term deleted", "original": original_decoded}
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/glossary/match")
async def match_paragraph_terms(
    project_id: str,
    request: MatchTermsRequest,
    gm: GlossaryManagerDep,
):
    try:
        from src.core.term_matcher import TermMatcher
        from src.core.glossary import create_default_semiconductor_glossary

        glossary = gm.load_merged(project_id)
        if not glossary.terms:
            global_glossary = gm.load_global("semiconductor")
            if not global_glossary.terms:
                global_glossary = create_default_semiconductor_glossary()
            glossary = global_glossary

        matcher = TermMatcher(glossary)
        matches = matcher.match_paragraph(request.paragraph, request.max_terms)
        return {
            "total_terms": len(glossary.terms),
            "matched_count": len(matches),
            "matches": [
                {
                    "original": m.term.original,
                    "translation": m.term.translation,
                    "strategy": m.term.strategy.value,
                    "note": m.term.note,
                    "score": m.score,
                    "match_type": m.match_type,
                }
                for m in matches
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
