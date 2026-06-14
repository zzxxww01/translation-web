"""Helpers for trimming long-form translation context before prompt injection."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .constants import (
    MAX_ARTICLE_CHALLENGES_IN_PROMPT,
    MAX_ARTICLE_GUIDELINES_IN_PROMPT,
    MAX_CONTEXT_GROUP_CHARS,
    MAX_CONTEXT_ITEM_CHARS,
    MAX_FORMAT_TOKENS_IN_PROMPT,
    MAX_GLOSSARY_TERMS_IN_PROMPT,
    MAX_REVIEW_PRIORITIES_IN_PROMPT,
    MAX_REVIEW_TERMS_IN_PROMPT,
    MAX_SECTION_GUIDELINE_LINES_IN_PROMPT,
    MAX_SECTION_KEY_POINTS_IN_PROMPT,
    MAX_SECTION_NOTES_IN_PROMPT,
)


def limit_non_empty_strings(
    items: Optional[Iterable[Any]],
    limit: int,
    max_chars_per_item: Optional[int] = None,
    max_total_chars: Optional[int] = None,
) -> List[str]:
    """裁剪非空字符串列表。

    除"条数"上限外，可选地按字符量收口：
    - max_chars_per_item: 单条超长则截断并加省略号；
    - max_total_chars: 累计字符达到上限即停止。
    使上下文预算不仅控制条数，也控制真实体积（token≈字符量的粗略口径）。
    """
    if not items or limit <= 0:
        return []

    normalized: List[str] = []
    total_chars = 0
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if max_chars_per_item and len(text) > max_chars_per_item:
            text = text[: max_chars_per_item - 1].rstrip() + "…"
        if max_total_chars is not None and total_chars + len(text) > max_total_chars:
            break
        normalized.append(text)
        total_chars += len(text)
        if len(normalized) >= limit:
            break
    return normalized


def build_article_challenge_payload(
    challenges: Optional[Iterable[Any]],
    limit: int = MAX_ARTICLE_CHALLENGES_IN_PROMPT,
) -> List[Dict[str, str]]:
    if not challenges or limit <= 0:
        return []

    result: List[Dict[str, str]] = []
    for challenge in challenges:
        location = ""
        issue = ""
        suggestion = ""
        challenge_type = ""

        if isinstance(challenge, dict):
            location = str(challenge.get("location", "")).strip()
            issue = str(challenge.get("issue", "")).strip()
            suggestion = str(challenge.get("suggestion", "")).strip()
            challenge_type = str(challenge.get("type", "")).strip()
        else:
            location = str(getattr(challenge, "location", "")).strip()
            issue = str(getattr(challenge, "issue", "")).strip()
            suggestion = str(getattr(challenge, "suggestion", "")).strip()
            challenge_type = str(getattr(challenge, "type", "")).strip()

        if not issue:
            continue

        entry: Dict[str, str] = {
            "location": location,
            "issue": issue,
            "suggestion": suggestion,
        }
        if challenge_type:
            entry["type"] = challenge_type

        result.append(entry)
        if len(result) >= limit:
            break

    return result


def build_translation_guidelines(
    guidelines: Optional[Iterable[Any]],
    limit: int = MAX_ARTICLE_GUIDELINES_IN_PROMPT,
) -> List[str]:
    return limit_non_empty_strings(
        guidelines,
        limit,
        max_chars_per_item=MAX_CONTEXT_ITEM_CHARS,
        max_total_chars=MAX_CONTEXT_GROUP_CHARS,
    )


def build_review_priorities(
    priorities: Optional[Iterable[Any]],
    limit: int = MAX_REVIEW_PRIORITIES_IN_PROMPT,
) -> List[str]:
    return limit_non_empty_strings(priorities, limit)


def build_section_context_payload(understanding: Any) -> Dict[str, Any]:
    if not understanding:
        return {}

    if isinstance(understanding, dict):
        role = understanding.get("role", "") or understanding.get("role_in_article", "")
        relation_to_previous = understanding.get("relation_to_previous", "")
        key_points = understanding.get("key_points", [])
        translation_notes = understanding.get("translation_notes", [])
    else:
        role = getattr(understanding, "role_in_article", "") or ""
        relation_to_previous = getattr(understanding, "relation_to_previous", "") or ""
        key_points = getattr(understanding, "key_points", [])
        translation_notes = getattr(understanding, "translation_notes", [])

    return {
        "role": role,
        "relation_to_previous": relation_to_previous,
        "key_points": limit_non_empty_strings(
            key_points,
            MAX_SECTION_KEY_POINTS_IN_PROMPT,
            max_chars_per_item=MAX_CONTEXT_ITEM_CHARS,
            max_total_chars=MAX_CONTEXT_GROUP_CHARS,
        ),
        "translation_notes": limit_non_empty_strings(
            translation_notes,
            MAX_SECTION_NOTES_IN_PROMPT,
            max_chars_per_item=MAX_CONTEXT_ITEM_CHARS,
            max_total_chars=MAX_CONTEXT_GROUP_CHARS,
        ),
    }


def build_glossary_entries_from_terms(
    terms: Optional[Iterable[Any]],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[Dict[str, Any]]:
    if not terms or max_terms <= 0:
        return []

    entries: List[Dict[str, Any]] = []
    for term in terms:
        if isinstance(term, dict):
            strategy = term.get("strategy", "")
            strategy_value = getattr(strategy, "value", strategy)
            translation = term.get("translation")
            original = term.get("term") or term.get("original", "")
            note = term.get("context_meaning") or term.get("note")
            first_occurrence_note = bool(term.get("first_occurrence_note", False))
        else:
            strategy_value = getattr(
                getattr(term, "strategy", None),
                "value",
                getattr(term, "strategy", ""),
            )
            translation = getattr(term, "translation", None)
            original = getattr(term, "term", None) or getattr(term, "original", "")
            note = getattr(term, "context_meaning", None) or getattr(term, "note", None)
            first_occurrence_note = bool(getattr(term, "first_occurrence_note", False))

        if not translation and strategy_value != "preserve":
            continue

        if not original:
            continue

        entries.append(
            {
                "original": original,
                "term": original,
                "translation": translation,
                "strategy": strategy_value or "translate",
                "note": note,
                "first_occurrence_note": first_occurrence_note,
            }
        )
        if len(entries) >= max_terms:
            break

    return entries


def build_review_term_entries(
    terms: Optional[Iterable[Any]],
    max_terms: int = MAX_REVIEW_TERMS_IN_PROMPT,
) -> List[Dict[str, str]]:
    if not terms or max_terms <= 0:
        return []

    entries: List[Dict[str, str]] = []
    for term in terms:
        if isinstance(term, dict):
            original = term.get("term") or term.get("original", "")
            translation = term.get("translation", "") or ""
            context_meaning = term.get("context_meaning") or term.get("note") or ""
        else:
            original = getattr(term, "term", None) or getattr(term, "original", "")
            translation = getattr(term, "translation", None) or ""
            context_meaning = getattr(term, "context_meaning", None) or getattr(term, "note", None) or ""
        if not original or not translation:
            continue

        entries.append(
            {
                "term": original,
                "original": original,
                "translation": translation,
                "context_meaning": context_meaning,
            }
        )
        if len(entries) >= max_terms:
            break

    return entries


def build_section_guideline_lines(
    guidelines: Optional[Iterable[Any]],
    *,
    section_role: str = "",
    translation_voice: str = "",
    target_audience: str = "",
    translation_notes: Optional[Iterable[Any]] = None,
    format_token_rules: str = "",
) -> List[str]:
    lines: List[str] = []

    if format_token_rules:
        lines.append(format_token_rules)
    if section_role:
        lines.append(f"本章角色：{section_role}")
    if translation_voice:
        lines.append(f"目标语气：{translation_voice}")
    if target_audience:
        lines.append(f"目标读者：{target_audience}")

    for note in limit_non_empty_strings(translation_notes, MAX_SECTION_NOTES_IN_PROMPT):
        lines.append(f"本章注意：{note}")

    lines.extend(build_translation_guidelines(guidelines))
    return lines[:MAX_SECTION_GUIDELINE_LINES_IN_PROMPT]


def limit_format_tokens(tokens: Optional[Iterable[Any]]) -> List[Any]:
    if not tokens:
        return []
    return list(tokens)[:MAX_FORMAT_TOKENS_IN_PROMPT]
