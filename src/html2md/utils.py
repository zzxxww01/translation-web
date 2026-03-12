from __future__ import annotations

import re


def collapse_ws(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def sanitize_basename(text: str) -> str:
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", text.strip())
    text = re.sub(r"\s+", "_", text)
    return text.strip("._") or "article"


def join_markdown_authors(parts: list[str]) -> str:
    parts = [collapse_ws(part) for part in parts if collapse_ws(part)]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"
