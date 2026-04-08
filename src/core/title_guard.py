"""Helpers for preserving critical title semantics in translated headings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


PREFIX_DELIMITER_RE = re.compile(r"\s*[:：]\s*")
VERSION_MARKER_RE = re.compile(r"\bv\d+(?:\.\d+)?\b", re.IGNORECASE)
INTERNAL_CAP_RE = re.compile(r"[a-z][A-Z]|[A-Z].*\d|\d.*[A-Z]")
FORMERLY_RE = re.compile(
    r"(?:^|[\s(（-])formerly\s+(?P<alias>[A-Za-z][A-Za-z0-9._-]*)",
    re.IGNORECASE,
)
PROTECTED_TOKEN_RE = re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9-]*|[A-Z][A-Za-z0-9-]{2,})\b")
TOKEN_STOPWORDS = {
    "A",
    "An",
    "And",
    "By",
    "For",
    "Formerly",
    "From",
    "In",
    "Into",
    "Of",
    "On",
    "Or",
    "The",
    "To",
    "Vs",
}


@dataclass(frozen=True)
class TitleRequirements:
    required_prefix: Optional[str]
    former_name: Optional[str]
    protected_tokens: List[str]


def _title_word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", text))


def _should_preserve_prefix(candidate: str) -> bool:
    if not candidate or _title_word_count(candidate) == 0:
        return False
    return bool(
        VERSION_MARKER_RE.search(candidate) or INTERNAL_CAP_RE.search(candidate)
    )


def extract_title_requirements(source_title: str) -> TitleRequirements:
    normalized = (source_title or "").strip()
    required_prefix: Optional[str] = None

    prefix_parts = PREFIX_DELIMITER_RE.split(normalized, maxsplit=1)
    if len(prefix_parts) == 2:
        candidate = prefix_parts[0].strip()
        if _should_preserve_prefix(candidate):
            required_prefix = candidate

    former_name = None
    former_match = FORMERLY_RE.search(normalized)
    if former_match:
        former_name = former_match.group("alias").strip()

    protected_tokens: List[str] = []
    seen = set()
    for token in PROTECTED_TOKEN_RE.findall(normalized):
        if token in TOKEN_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        protected_tokens.append(token)

    return TitleRequirements(
        required_prefix=required_prefix,
        former_name=former_name,
        protected_tokens=protected_tokens,
    )


def find_missing_title_terms(source_title: str, translated_title: str) -> List[str]:
    translated = (translated_title or "").strip()
    if not translated:
        requirements = extract_title_requirements(source_title)
        missing = []
        if requirements.required_prefix:
            missing.append(requirements.required_prefix)
        if requirements.former_name:
            missing.append(requirements.former_name)
        missing.extend(requirements.protected_tokens)
        return missing

    requirements = extract_title_requirements(source_title)
    missing: List[str] = []

    if requirements.required_prefix and requirements.required_prefix not in translated:
        missing.append(requirements.required_prefix)
    if requirements.former_name and requirements.former_name not in translated:
        missing.append(requirements.former_name)

    return missing


def enforce_translated_title(source_title: str, translated_title: str) -> str:
    translated = (translated_title or "").strip()
    if not translated:
        return translated

    requirements = extract_title_requirements(source_title)
    enforced = translated

    if requirements.required_prefix and requirements.required_prefix not in enforced:
        cleaned = enforced.lstrip("：:- ").strip()
        enforced = f"{requirements.required_prefix}：{cleaned}"

    if requirements.former_name and requirements.former_name not in enforced:
        if "（原" not in enforced and "(原" not in enforced:
            enforced = f"{enforced}（原 {requirements.former_name}）"
        else:
            enforced = f"{enforced} {requirements.former_name}"

    return enforced
