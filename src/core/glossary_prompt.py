"""Helpers for selecting and rendering glossary entries before prompt injection."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from .models import Glossary, GlossaryTerm, Section
from .models.enums import TranslationStrategy
from .term_matcher import TermMatcher

DEFAULT_GLOSSARY_PROMPT_TITLE = "## 术语约束（仅列出当前文本命中的术语，必须优先遵守）"
MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT = 48


def _count_term_occurrences(text: str, term: str) -> int:
    normalized_text = text.lower()
    normalized_term = term.lower().strip()
    if not normalized_term:
        return 0

    if re.fullmatch(r"[a-z0-9 .,+\-/]+", normalized_term):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])"
        return len(re.findall(pattern, normalized_text))

    return normalized_text.count(normalized_term)


def _normalize_whitespace(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _truncate_note(note: str, max_chars: int) -> str:
    normalized = _normalize_whitespace(note)
    if not normalized or max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _iter_prompt_terms(terms: Optional[Iterable[Any]]) -> Iterable[Any]:
    if isinstance(terms, dict):
        for original, translation in terms.items():
            yield {
                "original": original,
                "translation": translation,
                "strategy": "translate",
            }
        return

    for term in terms or []:
        yield term


def _normalize_prompt_term(term: Any) -> Optional[Dict[str, Any]]:
    if isinstance(term, dict):
        strategy = term.get("strategy", "")
        strategy_value = getattr(strategy, "value", strategy) or "translate"
        original = _normalize_whitespace(term.get("term") or term.get("original", ""))
        translation = _normalize_whitespace(term.get("translation"))
        note = _normalize_whitespace(term.get("context_meaning") or term.get("note"))
        first_occurrence_note = bool(term.get("first_occurrence_note", False))
    else:
        strategy_value = getattr(
            getattr(term, "strategy", None),
            "value",
            getattr(term, "strategy", ""),
        ) or "translate"
        original = _normalize_whitespace(
            getattr(term, "term", None) or getattr(term, "original", "")
        )
        translation = _normalize_whitespace(getattr(term, "translation", ""))
        note = _normalize_whitespace(
            getattr(term, "context_meaning", None) or getattr(term, "note", None)
        )
        first_occurrence_note = bool(getattr(term, "first_occurrence_note", False))

    if not original:
        return None
    if not translation and strategy_value != "preserve":
        return None

    return {
        "original": original,
        "translation": translation or original,
        "strategy": strategy_value,
        "note": note,
        "first_occurrence_note": first_occurrence_note,
    }


def _build_requirement_text(
    *,
    original: str,
    translation: str,
    strategy: str,
    first_occurrence_note: bool = False,
    already_used: bool = False,
) -> str:
    if strategy == "preserve":
        return "保留英文原文，不加注释"

    if strategy == "preserve_annotate":
        if already_used:
            return f"本段直接写\u201c{original}\u201d"
        if translation and translation != original:
            return f"首次出现写\u201c{original}（{translation}）\u201d，后文写\u201c{original}\u201d"
        return f"首次出现时加简短中文注释，后文继续写\u201c{original}\u201d"

    if strategy == "first_annotate" or first_occurrence_note:
        if already_used:
            return f"本段直接写\u201c{translation}\u201d"
        if translation != original:
            return f"首次出现写\u201c{translation}（{original}）\u201d，后文写\u201c{translation}\u201d"
        return f"首次出现时加简短注释，后文继续写\u201c{translation}\u201d"

    return "直接使用该写法"


def _render_glossary_prompt_line(
    term: Any,
    *,
    already_used: bool = False,
    max_note_chars: int = MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT,
) -> str:
    payload = _normalize_prompt_term(term)
    if not payload:
        return ""

    requirement = _build_requirement_text(
        original=payload["original"],
        translation=payload["translation"],
        strategy=payload["strategy"],
        first_occurrence_note=payload["first_occurrence_note"],
        already_used=already_used,
    )
    parts = [
        f"原文：{payload['original']}",
        f"标准写法：{payload['translation']}",
        f"要求：{requirement}",
    ]

    note = _truncate_note(payload["note"], max_note_chars)
    if note:
        parts.append(f"词义：{note}")

    return "- " + "；".join(parts)


def select_glossary_terms_for_text(
    glossary: Optional[Glossary],
    source_text: Optional[str],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[GlossaryTerm]:
    """Select only active glossary terms that are relevant to the source text."""
    if glossary is None or not glossary.terms:
        return []

    active_terms = [
        term
        for term in glossary.terms
        if getattr(term, "status", "active") == "active"
    ]
    if not active_terms:
        return []

    if not source_text or not source_text.strip():
        return active_terms[:max_terms]

    matcher = TermMatcher(Glossary(version=glossary.version, terms=active_terms))
    matches = matcher.match_paragraph(source_text, max_terms)
    return [
        match.term
        for match in matches
        if _count_term_occurrences(source_text, match.term.original) > 0
    ]


def build_glossary_prompt_entries(
    glossary: Optional[Glossary],
    source_text: Optional[str],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[Dict[str, Any]]:
    """Convert selected glossary terms into the normalized prompt payload format."""
    return [
        {
            "original": term.original,
            "translation": term.translation,
            "strategy": term.strategy.value,
            "note": term.note,
        }
        for term in select_glossary_terms_for_text(glossary, source_text, max_terms)
    ]


def render_glossary_prompt_block(
    terms: Optional[Iterable[Any]],
    *,
    title: str = DEFAULT_GLOSSARY_PROMPT_TITLE,
    include_title: bool = True,
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
    term_usage: Optional[Dict[str, List[str]]] = None,
    max_note_chars: int = MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT,
    empty_text: str = "",
) -> str:
    """Render prompt-ready glossary constraints from term objects or dictionaries."""
    if not terms or max_terms <= 0:
        return empty_text

    used_keys = {
        _normalize_whitespace(key).lower()
        for key in (term_usage or {})
        if _normalize_whitespace(key)
    }

    lines: List[str] = []
    for term in _iter_prompt_terms(terms):
        payload = _normalize_prompt_term(term)
        if not payload:
            continue

        line = _render_glossary_prompt_line(
            payload,
            already_used=payload["original"].lower() in used_keys,
            max_note_chars=max_note_chars,
        )
        if not line:
            continue

        lines.append(line)
        if len(lines) >= max_terms:
            break

    if not lines:
        return empty_text

    if include_title:
        return "\n".join([title, *lines])
    return "\n".join(lines)


def build_term_usage_from_project(
    sections: List[Section],
    glossary: Glossary,
    current_section_id: str,
    current_paragraph_id: str,
) -> Dict[str, List[str]]:
    """Scan all translated paragraphs before the current one to build term usage.

    Only tracks terms with ``first_annotate`` or ``preserve_annotate`` strategy.
    Iterates sections in order and stops when reaching the current paragraph.
    For each paragraph that already has a translation, checks whether its
    source text contains any tracked terms.

    Returns a dict ``{term_original_lower: [translation]}`` compatible with
    :func:`render_glossary_prompt_block`'s *term_usage* parameter.
    """
    if not glossary or not glossary.terms:
        return {}

    # Collect terms that need first-occurrence tracking
    tracked: List[GlossaryTerm] = [
        t
        for t in glossary.terms
        if getattr(t, "status", "active") == "active"
        and t.strategy
        in (TranslationStrategy.FIRST_ANNOTATE, TranslationStrategy.PRESERVE_ANNOTATE)
    ]
    if not tracked:
        return {}

    usage: Dict[str, List[str]] = {}

    for section in sections:
        for para in section.paragraphs:
            # Stop when we reach the current paragraph
            if (
                section.section_id == current_section_id
                and para.id == current_paragraph_id
            ):
                return usage

            # Only consider paragraphs that have a translation
            translation = para.confirmed or (
                para.latest_translation_text(non_empty=True)
                if hasattr(para, "latest_translation_text")
                else None
            )
            if not translation:
                continue

            source = para.source or ""
            if not source:
                continue

            for term in tracked:
                key = term.original.lower()
                if key in usage:
                    continue  # already recorded
                if _count_term_occurrences(source, term.original) > 0:
                    usage[key] = [term.translation or term.original]

    return usage
