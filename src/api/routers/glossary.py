"""Global glossary router."""

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.api.dependencies import GlossaryManagerDep
from src.api.middleware import NotFoundException, BadRequestException
from src.api.middleware.rate_limit import limiter
from src.core.glossary import infer_glossary_tags, normalize_glossary_tags
from src.core.models import GlossaryTerm, TranslationStrategy


router = APIRouter(prefix="/glossary", tags=["glossary"])


class TermRequest(BaseModel):
    original: str
    translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    status: str = "active"


class TermUpdateRequest(BaseModel):
    translation: Optional[str] = None
    strategy: Optional[TranslationStrategy] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class TermResponse(BaseModel):
    original: str
    translation: Optional[str] = None
    strategy: str
    note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    scope: str
    source: Optional[str] = None
    status: str
    updated_at: Optional[str] = None


class GlossaryResponse(BaseModel):
    version: int
    terms: List[TermResponse]


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


def _normalize_tags(tags: Optional[List[str]]) -> List[str]:
    return normalize_glossary_tags(tags)


def _initial_tags(original: str, tags: Optional[List[str]]) -> List[str]:
    normalized = _normalize_tags(tags)
    if normalized:
        return normalized
    return infer_glossary_tags(original)


def _term_to_response(term: GlossaryTerm, scope: str = "global") -> dict:
    payload = term.model_dump(mode="json")
    payload["scope"] = scope
    payload["source"] = term.source or "manual"
    payload["status"] = term.status or "active"
    payload["tags"] = list(term.tags)
    return payload


def _find_existing_term(glossary, original: str) -> GlossaryTerm:
    existing = glossary.get_term(original)
    if not existing:
        raise NotFoundException(detail=f"Term '{original}' not found")
    return existing


def _apply_term_updates(
    existing: GlossaryTerm,
    request: TermUpdateRequest,
    *,
    scope: str,
) -> GlossaryTerm:
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

    updated.scope = scope
    updated.source = existing.source or "manual"
    updated.updated_at = datetime.now()
    return updated


def _apply_batch_action(glossary, request: BatchGlossaryRequest) -> tuple[list[GlossaryTerm], int]:
    originals = {item.strip().lower() for item in request.originals if item.strip()}
    matched = [term for term in glossary.terms if term.original.lower() in originals]

    if request.action == "delete":
        glossary.terms = [term for term in glossary.terms if term.original.lower() not in originals]
        return [], len(matched)

    if request.action == "set_status" and request.status is None:
        raise BadRequestException(detail="Batch action 'set_status' requires status")
    if request.action == "set_strategy" and request.strategy is None:
        raise BadRequestException(detail="Batch action 'set_strategy' requires strategy")

    normalized_tags = _normalize_tags(request.tags)
    if request.action in {"add_tags", "replace_tags", "remove_tags"} and not normalized_tags:
        raise BadRequestException(detail=f"Batch action '{request.action}' requires tags")

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


@router.get("", response_model=GlossaryResponse)
@limiter.limit("100/minute")
async def get_global_glossary(http_request: Request, gm: GlossaryManagerDep):
    glossary = gm.load_global()
    return GlossaryResponse(
        version=glossary.version,
        terms=[TermResponse(**_term_to_response(term)) for term in glossary.terms],
    )


@router.post("", response_model=dict)
@limiter.limit("60/minute")
async def add_global_term(http_request: Request, request: TermRequest, gm: GlossaryManagerDep):
    glossary = gm.load_global()
    replaced = glossary.get_term(request.original) is not None

    term = GlossaryTerm(
        original=request.original,
        translation=request.translation,
        strategy=request.strategy,
        note=request.note,
        tags=_initial_tags(request.original, request.tags),
        scope="global",
        source="manual",
        status=request.status,
    )
    glossary.add_term(term)
    gm.save_global(glossary)

    return {
        "message": "Term added",
        "replaced": replaced,
        "term": _term_to_response(term),
    }


@router.put("/terms/{original}", response_model=dict)
@limiter.limit("60/minute")
async def update_global_term(
    http_request: Request,
    original: str,
    request: TermUpdateRequest,
    gm: GlossaryManagerDep,
):
    glossary = gm.load_global()
    existing = _find_existing_term(glossary, original)
    updated = _apply_term_updates(existing, request, scope="global")
    glossary.add_term(updated)
    gm.save_global(glossary)
    return {"message": "Term updated", "term": _term_to_response(updated)}


@router.delete("/terms/{original}", response_model=dict)
@limiter.limit("60/minute")
async def delete_global_term(http_request: Request, original: str, gm: GlossaryManagerDep):
    glossary = gm.load_global()
    _find_existing_term(glossary, original)
    original_lower = original.lower()
    glossary.terms = [term for term in glossary.terms if term.original.lower() != original_lower]
    gm.save_global(glossary)
    return {"message": "Term deleted", "original": original}


@router.post("/batch", response_model=dict)
@limiter.limit("20/minute")
async def batch_update_global_glossary(
    http_request: Request,
    request: BatchGlossaryRequest,
    gm: GlossaryManagerDep,
):
    glossary = gm.load_global()
    updated_terms, matched_count = _apply_batch_action(glossary, request)
    gm.save_global(glossary)
    return {
        "message": "Batch action applied",
        "action": request.action,
        "matched_count": matched_count,
        "updated_count": len(updated_terms),
        "terms": [_term_to_response(term) for term in updated_terms],
        "originals": request.originals,
    }
