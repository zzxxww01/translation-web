"""Read-only export coverage, independent of review/status flags.

This is a conservative missing-translation check, not a language-quality score.
Chinese text can legitimately retain brands, identifiers, URLs and numbers.
"""
from __future__ import annotations

import re
from typing import Any

from .models import ElementType, ProjectMeta, Section
from .title_validation import is_protected_name

_CJK = re.compile(r"[\u3400-\u9fff\U00020000-\U0002ffff]")


def _visible_text(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"`[^`]*`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$", "", text)
    return text.strip(" \n\t#*_~|:：,，;；")


def _needs_chinese(text: str) -> bool:
    visible = _visible_text(text)
    if not re.search(r"[A-Za-z]", visible) or _CJK.search(visible):
        return False
    if is_protected_name(visible):
        return False
    return True


def _missing_reason(source: str, translated: str | None) -> str | None:
    if not _needs_chinese(source):
        return None
    if not translated or not translated.strip():
        return "missing_translation"
    # Exemptions apply to the source only: replacing a sentence with a brand
    # or a number does not make it a Chinese translation.
    if not _CJK.search(_visible_text(translated)):
        return "untranslated_text"
    return None


def build_translation_completeness(
    sections: list[Section], meta: ProjectMeta | None = None,
) -> dict[str, Any]:
    """Return counts and stable source locations; never edit stored translations."""
    items: list[dict[str, Any]] = []
    if meta is not None:
        reason = _missing_reason(meta.title, meta.title_translation)
        if reason:
            items.append({"kind": "document_title", "reason": reason, "source_preview": meta.title[:160]})
    for section_index, section in enumerate(sections):
        location = {"section_id": section.section_id, "section_index": section_index,
                    "section_title": section.title}
        reason = _missing_reason(section.title, section.title_translation)
        if not section.synthetic and reason:
            items.append({**location, "kind": "section_title", "reason": reason,
                          "source_preview": section.title[:160]})
        for paragraph in section.paragraphs:
            if paragraph.is_metadata or paragraph.element_type in {ElementType.IMAGE, ElementType.CODE}:
                continue
            reason = _missing_reason(paragraph.source, paragraph.best_translation_text(fallback_to_source=False))
            if reason:
                items.append({**location, "kind": "body", "reason": reason,
                              "paragraph_id": paragraph.id, "paragraph_index": paragraph.index,
                              "parent_block_id": paragraph.parent_block_id,
                              "source_preview": paragraph.source[:160]})
    return {
        "is_complete": not items,
        "missing_count": len(items),
        "missing_title_count": sum(i["kind"] == "section_title" for i in items),
        "missing_body_count": sum(i["kind"] == "body" for i in items),
        "missing_document_title_count": sum(i["kind"] == "document_title" for i in items),
        "items": items,
    }


def completeness_summary(report: dict[str, Any]) -> str:
    return (f"中文稿未完成：缺译 {report['missing_count']} 处"
            f"（章节标题 {report['missing_title_count']}，正文 {report['missing_body_count']}，"
            f"文章标题 {report['missing_document_title_count']}）。未完成稿可能保留英文原文，请勿作为完整译稿交付。")
