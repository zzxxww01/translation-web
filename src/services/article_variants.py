"""文章工作台的「译本 2」：同源孪生项目。

孪生项目复制主项目的原文和章节结构、清空译文，段落 id 与主项目一一对应；之后要么用另一个模型跑
同一套四步法，要么写入从 Claude（four-step-translate）取回并对齐好的译文。导出、质量检查、编辑
保存都直接复用项目已有的能力。设计见 docs/superpowers/specs/2026-10-25-article-workbench-design.md。
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from src.core.models import ParagraphStatus, ProjectStatus, Section
from src.core.models.translation import Paragraph
from src.core.project import ProjectListSummary, ProjectManager
from src.core.project_lifecycle_service import ProjectLifecycleService
from src.services.claude_alignment import Alignment, Target, align_claude_translation

VARIANT_KINDS = {"model", "claude"}
# 段落里属于「某一版译文」的字段；其余（原文、结构、格式要求）两边共用
_TRANSLATION_FIELDS = {
    "translations", "confirmed", "confirmed_tokenized", "confirmed_format_issues",
    "history", "status", "ai_insight", "format_recovery_status", "format_errors",
}
# 主项目里不复制到孪生项目的东西：中间产物、导出文件
_SKIP_NAMES = {"artifacts", "sections", "meta.json"}
_EXPORT_SUFFIXES = ("_zh.md", "_zh.blocked.md", "_en.md", "_bilingual.md")


def variant_id(main_id: str, suffix: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", suffix.lower()).strip("-") or "v2"
    return f"{main_id}--{clean}"


def list_variants(pm: ProjectManager, main_id: str) -> List[ProjectListSummary]:
    return [s for s in pm.list_summaries(include_variants=True) if s.variant_of == main_id]


def _blank_paragraph(paragraph: Paragraph) -> Paragraph:
    return Paragraph(**paragraph.model_dump(exclude=_TRANSLATION_FIELDS))


def _blank_sections(sections: List[Section]) -> List[Section]:
    blank = []
    for section in sections:
        copy = section.model_copy(deep=True)
        copy.title_translation = None
        copy.paragraphs = [_blank_paragraph(p) for p in section.paragraphs]
        blank.append(copy)
    # 结构化元数据（作者行等）和新建项目一样直接算已确认
    ProjectLifecycleService._auto_approve_structured_metadata(blank)
    return blank


def create_variant(pm: ProjectManager, main_id: str, *, kind: str, label: str, suffix: str,
                   replace: bool = False) -> str:
    """复制主项目建孪生项目，返回其 id。replace=True 时先删掉同名的旧孪生项目（重新导入）。"""
    if kind not in VARIANT_KINDS:
        raise ValueError(f"未知的译本类型：{kind}")
    main = pm.get(main_id)
    if main.variant_of:
        raise ValueError("译本 2 只能挂在主项目上")
    new_id = variant_id(main_id, suffix)
    target_dir = pm._project_dir(new_id)
    if target_dir.exists():
        if not replace:
            raise ValueError(f"已经有这个译本了：{new_id}")
        pm.delete(new_id)

    source_dir = pm._project_dir(main_id)
    target_dir.mkdir(parents=True)
    try:
        for item in source_dir.iterdir():
            if item.name in _SKIP_NAMES or item.name.endswith(_EXPORT_SUFFIXES) or item.is_symlink():
                continue
            if item.is_dir():
                shutil.copytree(item, target_dir / item.name, symlinks=False)
            else:
                shutil.copy2(item, target_dir / item.name)
        (target_dir / "sections").mkdir()
        sections = _blank_sections(pm.get_sections(main_id))
        for section in sections:
            pm._save_section(new_id, section)
        meta = main.model_copy(deep=True, update={
            "id": new_id,
            "title_translation": None,
            "variant_of": main_id,
            "variant_kind": kind,
            "variant_label": label,
            "claude_run_id": None,
            "status": ProjectStatus.CREATED,
            "versions": [],
            "confirmation_map": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
        meta.update_progress(sections)
        pm.save_meta(meta)
    except Exception:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise
    return new_id


def alignment_targets(sections: List[Section]) -> List[Target]:
    targets: List[Target] = []
    for section in sections:
        if section.title and not section.synthetic:
            targets.append(Target(f"section:{section.section_id}", section.section_id, section.title, "section"))
        for paragraph in section.paragraphs:
            # 段落 id 只在章节内唯一（每章都从 p000 起）
            targets.append(Target(f"{section.section_id}/{paragraph.id}", section.section_id, paragraph.source,
                                  paragraph.element_type.value))
    return targets


def import_claude_translation(pm: ProjectManager, main_id: str, *, zh_markdown: str, en_markdown: str,
                              run_id: Optional[str] = None, agent: str = "claude") -> Dict:
    """把 four-step-translate（Claude 或 Codex 跑的）产出的 zh.md 对齐后写进 `--claude`/`--codex` 孪生项目
    （已有就整篇替换），返回对齐统计。"""
    sections = pm.get_sections(main_id)
    alignment: Alignment = align_claude_translation(en_markdown, zh_markdown, alignment_targets(sections))
    if not alignment.texts:
        raise ValueError("Claude 的译文和这篇文章对不上，可能不是同一篇")
    label = "Codex" if agent == "codex" else "Claude"
    new_id = create_variant(pm, main_id, kind="claude", label=label, suffix=label, replace=True)

    for section in pm.get_sections(new_id):
        title = alignment.texts.get(f"section:{section.section_id}")
        if title:
            section.title_translation = title.split("\n")[0].strip()
        for paragraph in section.paragraphs:
            text = alignment.texts.get(f"{section.section_id}/{paragraph.id}")
            if text and paragraph.element_type.value != "image" and paragraph.status != ParagraphStatus.APPROVED:
                paragraph.add_translation(text, "claude")
                paragraph.status = ParagraphStatus.TRANSLATED
        pm._save_section(new_id, section)

    meta = pm.get(new_id)
    if alignment.title:
        meta.title_translation = alignment.title
    meta.update_progress(pm.get_sections(new_id))
    meta.status = ProjectStatus.REVIEWING
    pm.save_meta(meta)
    _write_import_record(pm, new_id, {"run_id": run_id, **alignment.stats})
    return {"variant_id": new_id, "title": alignment.title, **alignment.stats}


def _write_import_record(pm: ProjectManager, project_id: str, record: Dict) -> None:
    artifacts = pm._project_dir(project_id) / "artifacts"
    artifacts.mkdir(exist_ok=True)
    pm._write_json(artifacts / "claude-import.json", {**record, "imported_at": datetime.now().isoformat()})


def read_import_record(pm: ProjectManager, project_id: str) -> Optional[Dict]:
    path = pm._project_dir(project_id) / "artifacts" / "claude-import.json"
    try:
        return pm._read_json(path)
    except (FileNotFoundError, ValueError):
        return None


def delete_with_variants(pm: ProjectManager, main_id: str) -> List[str]:
    removed = []
    for variant in list_variants(pm, main_id):
        pm.delete(variant.id)
        removed.append(variant.id)
    pm.delete(main_id)
    return removed
