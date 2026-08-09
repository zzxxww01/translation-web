"""Shared parsing and allow-list helpers for project image assets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


BROWSER_IMAGE_EXTENSIONS = frozenset(
    {
        ".avif",
        ".bmp",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".png",
        ".svg",
        ".webp",
    }
)


@dataclass(frozen=True)
class MarkdownImageReference:
    alt: str
    source: str
    title: str = ""


_IMAGE_PREFIX = re.compile(r"^!\[(?P<alt>[^\]]*)\]\(")
_TRAILING_QUOTED_TITLE = re.compile(
    r"^(?P<source>.+?)\s+(?P<quote>['\"])(?P<title>.*)(?P=quote)$",
    re.DOTALL,
)


def _has_balanced_parentheses(value: str) -> bool:
    depth = 0
    escaped = False
    for character in value:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _unescape_destination(value: str) -> str:
    return re.sub(r"\\([\\()<> ])", r"\1", value)


def parse_markdown_image_reference(value: str) -> Optional[MarkdownImageReference]:
    """Parse one complete Markdown image, including balanced parentheses.

    A regex such as ``[^)]+`` truncates valid saved-page paths like
    ``images/Co_Packaged_Optics_(CPO)/chart.png``. The final character is the
    outer delimiter, so parse the complete interior and validate parentheses
    within the destination separately.
    """

    stripped = value.strip()
    prefix = _IMAGE_PREFIX.match(stripped)
    if prefix is None or not stripped.endswith(")"):
        return None

    interior = stripped[prefix.end() : -1].strip()
    if not interior:
        return None

    title = ""
    if interior.startswith("<"):
        closing = interior.find(">", 1)
        if closing < 0:
            return None
        source = interior[1:closing].strip()
        remainder = interior[closing + 1 :].strip()
        if remainder:
            title_match = re.fullmatch(
                r"(?P<quote>['\"])(?P<title>.*)(?P=quote)",
                remainder,
                re.DOTALL,
            )
            if title_match is None:
                return None
            title = title_match.group("title")
    else:
        title_match = _TRAILING_QUOTED_TITLE.fullmatch(interior)
        if title_match is not None:
            source = title_match.group("source").strip()
            title = title_match.group("title")
        else:
            source = interior

    if not source or not _has_balanced_parentheses(source):
        return None
    return MarkdownImageReference(
        alt=prefix.group("alt"),
        source=_unescape_destination(source),
        title=title,
    )
