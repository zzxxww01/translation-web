"""人工改动：机翻初稿和人改后的译文对比，以及工作台的「保存全文」。

段落的机翻草稿按模型名存在 paragraph.translations 里，人在工作台改的会再记一条 model="manual"
并写进 confirmed。所以「最初版本」= 最新一条非人工草稿，「最终版本」= best_translation_text()。

保存全文时把全篇一次确认（不用逐段确认），并把改动落盘到该版本项目目录的 finalized/ 下：
    final.md       导出的整篇中文
    changes.json   改过的段落（原文、初稿、改后），给以后分析人工改了什么用
    changes.md     同上，人读的版本
    diff.patch     初稿全文和最终全文的 unified diff
"""

from __future__ import annotations

import difflib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from src.core.models import ElementType, Paragraph, Section
from src.core.project import ProjectManager

logger = logging.getLogger(__name__)

HUMAN_MODELS = {"manual"}
FINAL_DIR = "finalized"


def machine_text(paragraph: Paragraph) -> Optional[str]:
    """最新一条机器译文（网页版各模型、Claude/Codex 导入的都算），人工改的不算。"""
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


def _text_paragraphs(sections: List[Section]) -> Iterator[tuple[Section, Paragraph]]:
    for section in sections:
        for paragraph in section.paragraphs:
            if paragraph.element_type != ElementType.IMAGE:
                yield section, paragraph


def collect_changes(sections: List[Section]) -> Dict[str, Any]:
    """有译文的段数，以及人工改过的段落（初稿为 None 表示原来没有译文、是人写的）。"""
    total = 0
    changes: List[Dict[str, Any]] = []
    for section, paragraph in _text_paragraphs(sections):
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


def _changes_markdown(title: str, report: Dict[str, Any], saved_at: str) -> str:
    lines = [f"# 人工改动：{title}", "", f"保存于 {saved_at}，共 {report['total']} 段，改了 {report['changed']} 段。", ""]
    for index, change in enumerate(report["changes"], 1):
        lines += [
            f"## {index}. {change['section_title'] or change['section_id']} / {change['paragraph_id']}",
            "",
            f"原文：{change['source']}",
            "",
            f"初稿：{change['before'] if change['before'] is not None else '（没有，人工写的）'}",
            "",
            f"改后：{change['after']}",
            "",
        ]
    return "\n".join(lines)


def _unified_diff(sections: List[Section], label: str) -> str:
    before: List[str] = []
    after: List[str] = []
    for _section, paragraph in _text_paragraphs(sections):
        final = paragraph.best_translation_text()
        draft = machine_text(paragraph)
        if not final and not draft:
            continue
        before.append((draft if draft is not None else "") + "\n")
        after.append(final + "\n")
    return "".join(difflib.unified_diff(before, after, fromfile=f"{label}/初稿", tofile=f"{label}/定稿", n=1))


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def finalized_dir(pm: ProjectManager, project_id: str) -> Path:
    return pm._project_dir(project_id) / FINAL_DIR


def read_summary(pm: ProjectManager, project_id: str) -> Optional[Dict[str, Any]]:
    """上次保存全文的概况（时间、段数、改了几段）；没保存过为 None。"""
    try:
        data = json.loads((finalized_dir(pm, project_id) / "changes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"saved_at": data.get("saved_at"), "total": data.get("total", 0), "changed": data.get("changed", 0)}


def finalize(pm: ProjectManager, main_id: str, target_id: str) -> Dict[str, Any]:
    """保存全文：全篇一次确认，落盘定稿和人工改动，主项目记上定稿时间。"""
    confirmed = pm.confirm_all_paragraphs(target_id)
    meta = pm.get(target_id)
    sections = pm.get_sections(target_id)
    report = collect_changes(sections)
    now = datetime.now()
    saved_at = now.isoformat(timespec="seconds")
    label = meta.variant_label or "网页版"
    try:
        final_md = pm.export(target_id, format="zh", allow_qa_override=True)
    except Exception:  # noqa: BLE001 - 导出失败不该挡住保存，退回逐段拼接
        logger.exception("export failed while finalizing %s", target_id)
        final_md = "\n\n".join(p.best_translation_text() for _s, p in _text_paragraphs(sections) if p.best_translation_text())

    folder = finalized_dir(pm, target_id)
    folder.mkdir(exist_ok=True)
    record = {
        "project_id": target_id,
        "main_id": main_id,
        "label": label,
        "title": meta.title,
        "original_url": meta.metadata.original_url if meta.metadata else None,
        "saved_at": saved_at,
        **report,
    }
    _write(folder / "final.md", final_md)
    _write(folder / "changes.json", json.dumps(record, ensure_ascii=False, indent=1))
    _write(folder / "changes.md", _changes_markdown(f"{meta.title}（{label}）", report, saved_at))
    _write(folder / "diff.patch", _unified_diff(sections, label))

    pm.merge_meta_fields(target_id, fields={"finalized_at": now})
    if target_id != main_id:
        pm.merge_meta_fields(main_id, fields={"finalized_at": now})
    return {"saved_at": saved_at, "total": report["total"], "changed": report["changed"], "confirmed": confirmed}


def export_all(pm: ProjectManager) -> Iterator[str]:
    """所有保存过全文的版本的人工改动，一行一段（JSONL），给以后批量分析。"""
    for summary in pm.list_summaries(include_variants=True):
        try:
            data = json.loads((finalized_dir(pm, summary.id) / "changes.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        shared = {key: data.get(key) for key in ("project_id", "main_id", "label", "title", "original_url", "saved_at")}
        for change in data.get("changes", []):
            yield json.dumps({**shared, **change}, ensure_ascii=False) + "\n"
