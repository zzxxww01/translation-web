"""Hard output guards for terms that must remain untranslated."""

from __future__ import annotations

import re


_SOURCE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_TOKEN_WITH_CHINESE_ANNOTATION_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])\s*[（(]\s*词元\s*[)）]",
    re.IGNORECASE,
)
_CHINESE_WITH_TOKEN_ANNOTATION_RE = re.compile(
    r"词元\s*[（(]\s*tokens?\s*[)）]",
    re.IGNORECASE,
)
_TOKEN_SLASH_CHINESE_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])\s*[/／]\s*词元",
    re.IGNORECASE,
)
_CHINESE_SLASH_TOKEN_RE = re.compile(
    r"词元\s*[/／]\s*tokens?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def preserve_protected_terms(source_text: str, translated_text: str) -> str:
    """Enforce untranslated terms when they occur in the source.

    ``token`` is an intentional English technical term in this product. The
    guard is source-aware so unrelated Chinese text containing "词元" is not
    rewritten when the source never mentioned the protected term.
    """

    if not translated_text or not _SOURCE_TOKEN_RE.search(source_text or ""):
        return translated_text

    normalized = _TOKEN_WITH_CHINESE_ANNOTATION_RE.sub("token", translated_text)
    normalized = _CHINESE_WITH_TOKEN_ANNOTATION_RE.sub("token", normalized)
    normalized = _TOKEN_SLASH_CHINESE_RE.sub("token", normalized)
    normalized = _CHINESE_SLASH_TOKEN_RE.sub("token", normalized)
    return normalized.replace("词元", "token")
