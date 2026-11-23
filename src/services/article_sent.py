"""「已发送」标记：译文发出去（公众号等，在系统外面）之后手动标一下，和翻译进度分开。

记录放在主项目的 artifacts/sent.json，不放 meta.json（后台翻译拿着旧快照存 meta 时会把它冲掉，同阅读书签）：
{"at": 标记时间, "target": 当时的主译本 id, "digest": 当时主译本译文的指纹}。
打开工作台时重新算一次指纹，和记录对不上（改过译文或换了主译本）就提示「发送后有改动」。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.core.models import ElementType, Section
from src.core.project import ProjectManager


def _path(pm: ProjectManager, main_id: str) -> Path:
    return pm._project_dir(main_id) / "artifacts" / "sent.json"


def read(pm: ProjectManager, main_id: str) -> Optional[Dict[str, str]]:
    """没标过、文件坏了都当没发送；不改动原文件。"""
    try:
        record = pm._read_json(_path(pm, main_id))
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or not isinstance(record.get("at"), str):
        return None
    try:
        datetime.fromisoformat(record["at"])
    except ValueError:
        return None
    return {key: record[key] for key in ("at", "target", "digest") if isinstance(record.get(key), str)}


def digest(title_translation: Optional[str], sections: List[Section]) -> str:
    """主译本译文的指纹：标题、章节标题和各段译文，图片不算。"""
    hasher = hashlib.sha256()

    def feed(text: Optional[str]) -> None:
        hasher.update((text or "").strip().encode("utf-8"))
        hasher.update(b"\x00")

    feed(title_translation)
    for section in sections:
        feed(section.title_translation)
        for paragraph in section.paragraphs:
            if paragraph.element_type != ElementType.IMAGE:
                feed(paragraph.best_translation_text())
    return hasher.hexdigest()


def primary_digest(pm: ProjectManager, primary_id: str) -> str:
    return digest(pm.get(primary_id).title_translation, pm.get_sections(primary_id))


def mark(pm: ProjectManager, main_id: str, primary_id: str) -> Dict[str, str]:
    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": primary_id,
        "digest": primary_digest(pm, primary_id),
    }
    pm._write_json(_path(pm, main_id), record)
    return record


def clear(pm: ProjectManager, main_id: str) -> None:
    _path(pm, main_id).unlink(missing_ok=True)


def changed_since(record: Dict[str, str], primary_id: str, current_digest: str) -> bool:
    return record.get("target") != primary_id or record.get("digest") != current_digest
