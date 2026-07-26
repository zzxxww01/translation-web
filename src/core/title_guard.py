"""Helpers for preserving critical title semantics in translated headings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


PREFIX_DELIMITER_RE = re.compile(r"\s*[:：]\s*")
VERSION_MARKER_RE = re.compile(r"\bv\d+(?:\.\d+)?\b", re.IGNORECASE)
INTERNAL_CAP_RE = re.compile(r"[a-z][A-Z]|[A-Z].*\d|\d.*[A-Z]")
# 只有"短产品代号"才有资格回插：过长或空格 >= 2 的前缀（如
# "Anthropic 3Q26 Profit Over $1B"）是完整标题片段而非代号，回插会产生
# "英文标题：中文标题" 双标题文件名（2026-07 20 篇审校实测 bug）。
MAX_PRESERVED_PREFIX_CHARS = 12
MAX_PRESERVED_PREFIX_SPACES = 1
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
    if len(candidate) > MAX_PRESERVED_PREFIX_CHARS:
        return False
    if candidate.count(" ") > MAX_PRESERVED_PREFIX_SPACES:
        return False
    return bool(
        VERSION_MARKER_RE.search(candidate) or INTERNAL_CAP_RE.search(candidate)
    )


def _prefix_lost_in_translation(prefix: str, translated: str) -> bool:
    """前缀是否真的在译文中"丢失"。

    译文标题长度已 >= 原前缀时，说明是完整重译而非丢失短代号，
    一律不回插，避免生成双标题。
    """
    if prefix in translated:
        return False
    return len(translated) < len(prefix)


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

    if requirements.required_prefix and _prefix_lost_in_translation(
        requirements.required_prefix, translated
    ):
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

    if requirements.required_prefix and _prefix_lost_in_translation(
        requirements.required_prefix, enforced
    ):
        cleaned = enforced.lstrip("：:- ").strip()
        enforced = f"{requirements.required_prefix}：{cleaned}"

    if requirements.former_name and requirements.former_name not in enforced:
        if "（原" not in enforced and "(原" not in enforced:
            enforced = f"{enforced}（原 {requirements.former_name}）"
        else:
            enforced = f"{enforced} {requirements.former_name}"

    return enforced
