"""人工改动：机翻初稿和现在的译文对比。

段落的机翻草稿按模型名存在 paragraph.translations 里，人在工作台改的会再记一条 model="manual"
并写进 confirmed。所以「机翻初稿」= 最新一条非人工草稿，「现在」= best_translation_text()。

两者都一直存在项目数据里，改动随时算得出来，不需要「定稿」之类的动作：工作台里随时看，
也能一次导出所有文章的改动（JSONL），给以后优化提示词用。
"""

from __future__ import annotations

import difflib
import json
from typing import Any, Dict, Iterator, List, Optional

from src.core.models import ElementType, Paragraph, Section
from src.core.project import ProjectManager

HUMAN_MODELS = {"manual"}


def machine_text(paragraph: Paragraph) -> Optional[str]:
    """最新一条机器译文（网页版各模型、Codex/Claude 导入的都算），人工改的不算。"""
    records = [
        record for name, record in paragraph.translations.items()
        if name not in HUMAN_MODELS and record.model not in HUMAN_MODELS and record.text.strip()
    ]
    if not records:
        return None
    return max(records, key=lambda record: record.created_at.timestamp()).text.strip()


def diff_segments(before: str, after: str) -> List[Dict[str, str]]:
    """逐字对比（中文没有空格分词），给前端标出删掉和加上的部分。"""
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    segments: List[Dict[str, str]] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            segments.append({"op": "equal", "text": before[i1:i2]})
            continue
        if i2 > i1:
            segments.append({"op": "delete", "text": before[i1:i2]})
        if j2 > j1:
            segments.append({"op": "insert", "text": after[j1:j2]})
    return segments


def collect_changes(sections: List[Section]) -> Dict[str, Any]:
    """有译文的段数，以及人工改过的段落（初稿为 None 表示原来没有译文、是人写的）。"""
    total = 0
    changes: List[Dict[str, Any]] = []
    for section in sections:
        for paragraph in section.paragraphs:
            if paragraph.element_type == ElementType.IMAGE:
                continue
            after = paragraph.best_translation_text()
            if not after:
                continue
            total += 1
            before = machine_text(paragraph)
            if before == after.strip():
                continue
            changes.append({
                "key": f"{section.section_id}/{paragraph.id}",
                "section_id": section.section_id,
                "section_title": section.title,
                "paragraph_id": paragraph.id,
                "kind": paragraph.element_type.value,
                "source": paragraph.source,
                "before": before,
                "after": after,
            })
    return {"total": total, "changed": len(changes), "changes": changes}


def with_segments(report: Dict[str, Any]) -> Dict[str, Any]:
    return {**report, "changes": [{**c, "segments": diff_segments(c["before"] or "", c["after"])} for c in report["changes"]]}


def export_all(pm: ProjectManager) -> Iterator[str]:
    """所有文章、所有版本（网页版和译本 2）里人工改过的段落，一行一段（JSONL）。"""
    for summary in pm.list_summaries(include_variants=True):
        try:
            meta = pm.get(summary.id)
            report = collect_changes(pm.get_sections(summary.id))
        except (FileNotFoundError, OSError, ValueError):
            continue
        if not report["changed"]:
            continue
        shared = {
            "project_id": meta.id,
            "main_id": meta.variant_of or meta.id,
            "version": meta.variant_label or "网页版",
            "title": meta.title,
            "original_url": meta.metadata.original_url if meta.metadata else None,
        }
        for change in report["changes"]:
            yield json.dumps({**shared, **change}, ensure_ascii=False) + "\n"
