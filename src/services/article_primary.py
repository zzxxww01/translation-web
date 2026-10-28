"""主译本：文章工作台中间那一栏、「导出主译本」和文章列表进度看的那一版。

用户在工作台点「设为主译本」时存进主项目 meta 的 primary_target；没选过（或指向的版本已经没了）时按默认规则：
网页版有译文或正在翻 → 网页版；否则最近导入的 Agent 版；都没有 → 网页版。
有了第一版 Agent 译文后就把当时显示的那一版写进 meta（导入时；旧数据在打开工作台时），
之后再加 Agent 版、在网页版里写字都不会让主译本自己换。设计见
docs/superpowers/specs/2026-10-28-workbench-agent-model-design.md 4.2。
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from src.core.project import ProjectManager
from src.services import article_variants
from src.services.translation_run_registry import translation_run_registry


def started(main_id: str, translated_paragraphs: int) -> bool:
    """网页版算不算开始了：翻过（或手写过）一段，或者正在翻。工作台和文章列表都按这一条。"""
    return translated_paragraphs > 0 or translation_run_registry.get_active_run(main_id) is not None


def main_started(pm: ProjectManager, main_id: str) -> bool:
    return started(main_id, pm.get_translation_summary(main_id).translated_paragraphs)


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


def _shown_default(pm: ProjectManager, main_id: str) -> Optional[str]:
    """还没存过主译本时现在显示的是哪一版；存过返回 None。"""
    if pm.get(main_id).primary_target:
        return None
    ids = [v.id for v in article_variants.list_variants(pm, main_id)]
    return resolve_primary(pm, main_id, ids, primary_target=None, main_started=main_started(pm, main_id))


def pin_existing_default(pm: ProjectManager, main_id: str) -> None:
    """旧数据：已经有 Agent 版却没存过主译本，就把现在显示的那一版记下来。"""
    with article_variants.variant_lock(main_id):
        shown = _shown_default(pm, main_id)
        if shown is None:
            return
        if any(article_variants.read_import_record(pm, v.id) for v in article_variants.list_variants(pm, main_id)):
            pm.merge_meta_fields(main_id, fields={"primary_target": shown})


def import_agent_version(pm: ProjectManager, main_id: str, **kwargs) -> Dict:
    """导入 Agent 译文；还没存过主译本时顺手记下：网页版没开始又没有别的 Agent 版 → 就是这一版，否则是导入前显示的那一版。"""
    with article_variants.variant_lock(main_id):
        shown = _shown_default(pm, main_id)
        fresh = shown == main_id and not main_started(pm, main_id)
        result = article_variants.import_claude_translation(pm, main_id, **kwargs)
        if shown is not None:
            pm.merge_meta_fields(main_id, fields={"primary_target": result["variant_id"] if fresh else shown})
        return result
