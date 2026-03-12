"""Glossary utilities shared by API routes."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from src.core.constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from src.core.glossary import GlossaryManager
from src.core.glossary_prompt import (
    render_glossary_prompt_block,
    select_glossary_terms_for_text,
)
from src.core.models import Glossary

_gm = GlossaryManager(projects_path="projects")


def get_glossary_manager() -> GlossaryManager:
    """Return the singleton glossary manager used by API helpers."""
    return _gm


def build_glossary_context(
    source_text: Optional[str] = None,
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> str:
    """Build the prompt glossary block for post translation."""
    try:
        glossary = _gm.load_global()
        selected_terms = select_glossary_terms_for_text(
            glossary,
            source_text,
            max_terms=max_terms,
        )
        return build_glossary_context_from_terms(selected_terms)
    except Exception:
        return ""


def build_glossary_context_from_terms(
    terms: Iterable[Any],
    include_strategy: bool = True,
) -> str:
    """Render a glossary prompt block from term objects or dictionaries."""
    del include_strategy
    return render_glossary_prompt_block(
        terms,
        include_title=True,
        empty_text="",
    )


def get_combined_glossary(project_id: str) -> Glossary:
    """Load the merged glossary where project terms override global terms."""
    try:
        return _gm.load_merged(project_id)
    except Exception:
        return Glossary()
