"""
Project glossary router.
"""

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.models import GlossaryTerm, TranslationStrategy
from src.api.dependencies import GlossaryManagerDep
from src.api.middleware import NotFoundException


router = APIRouter(prefix="", tags=["projects"])


class AddTermRequest(BaseModel):
    original: str
    translation: Optional[str] = None
    strategy: str = "translate"
    note: Optional[str] = None


class MatchTermsRequest(BaseModel):
    paragraph: str
    max_terms: int = 20


@router.get("/projects/{project_id}/glossary")
async def get_project_glossary(project_id: str, gm: GlossaryManagerDep):
    try:
        glossary = gm.load_project(project_id)
        return {
            "version": glossary.version,
            "terms": [t.model_dump() for t in glossary.terms],
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
        )
        glossary.add_term(term)
        gm.save_project(project_id, glossary)
        return {"message": "Term added", "term": term.model_dump()}
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
        )
        glossary.add_term(updated_term)
        gm.save_project(project_id, glossary)
        return {"message": "Term updated", "term": updated_term.model_dump()}
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

        glossary = gm.load_project(project_id)
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
