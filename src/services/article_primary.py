"""主译本：文章工作台中间那一栏、「导出主译本」和文章列表进度看的那一版。

用户在工作台点「设为主译本」时存进主项目 meta 的 primary_target；没选过（或指向的版本已经没了）时按默认规则：
网页版有译文或正在翻 → 网页版；否则最近导入的 Agent 版；都没有 → 网页版。默认值只用来显示，不写回 meta。
设计见 docs/superpowers/specs/2026-10-28-workbench-agent-model-design.md 4.2。
"""

from __future__ import annotations

from typing import Iterable, Optional

from src.core.project import ProjectManager
from src.services import article_variants


def resolve_primary(pm: ProjectManager, main_id: str, variant_ids: Iterable[str], *,
                    primary_target: Optional[str], main_started: bool) -> str:
    ids = list(variant_ids)
    if primary_target and (primary_target == main_id or primary_target in ids):
        return primary_target
    if main_started:
        return main_id
    imported = []
    for vid in ids:
        record = article_variants.read_import_record(pm, vid)
        if record and isinstance(record.get("imported_at"), str):
            imported.append((record["imported_at"], vid))
    return max(imported)[1] if imported else main_id
