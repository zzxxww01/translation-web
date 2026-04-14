"""
术语冲突检测器

检测候选术语与已有术语的冲突。
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from src.services.glossary_storage import GlossaryStorage
from src.services.term_extraction_service import TermCandidate


class ConflictType(Enum):
    """冲突类型"""
    TRANSLATION_MISMATCH = "translation_mismatch"  # 翻译不一致
    CONTEXT_MISMATCH = "context_mismatch"  # 上下文不匹配


@dataclass
class TermConflict:
    """术语冲突"""
    original: str  # 原文
    existing_term_id: str  # 已有术语ID
    existing_translation: str  # 已有翻译
    existing_scope: str  # 已有作用域（global/project）
    suggested_translation: str  # 建议翻译
    context: str  # 候选术语上下文
    conflict_type: ConflictType  # 冲突类型


class TermConflictDetector:
    """术语冲突检测器"""

    def __init__(self, storage: GlossaryStorage):
        """
        初始化冲突检测器

        Args:
            storage: 术语存储
        """
        self.storage = storage

    def detect(
        self,
        candidates: List[TermCandidate],
        project_id: Optional[str] = None
    ) -> List[TermConflict]:
        """
        检测候选术语与已有术语的冲突

        Args:
            candidates: 候选术语列表
            project_id: 项目ID（可选）

        Returns:
            冲突列表
        """
        conflicts = []

        for candidate in candidates:
            # 查找已有术语（大小写不敏感）
            existing_terms = self._find_existing_terms(
                candidate.original,
                project_id
            )

            if not existing_terms:
                continue

            # 检查每个已有术语
            for term, metadata in existing_terms:
                # 忽略非激活术语
                if term.status != "active":
                    continue

                # 检查翻译是否一致
                if term.translation != candidate.suggested_translation:
                    conflicts.append(TermConflict(
                        original=candidate.original,
                        existing_term_id=term.id,
                        existing_translation=term.translation,
                        existing_scope=metadata.scope,
                        suggested_translation=candidate.suggested_translation,
                        context=candidate.context,
                        conflict_type=ConflictType.TRANSLATION_MISMATCH
                    ))

        return conflicts

    def _find_existing_terms(
        self,
        original: str,
        project_id: Optional[str] = None
    ) -> List[tuple]:
        """
        查找已有术语（大小写不敏感）

        优先级：项目术语 > 全局术语

        Args:
            original: 原文
            project_id: 项目ID

        Returns:
            (Term, TermMetadata) 元组列表
        """
        results = []

        # 加载全局术语
        global_terms = self.storage.load_terms("global")
        global_metadata = self.storage.load_metadata("global")
        global_meta_dict = {m.term_id: m for m in global_metadata}

        # 加载项目术语
        project_terms = []
        project_meta_dict = {}
        if project_id:
            project_terms = self.storage.load_terms("project", project_id)
            project_metadata = self.storage.load_metadata("project", project_id)
            project_meta_dict = {m.term_id: m for m in project_metadata}

        # 查找匹配的术语（大小写不敏感）
        original_lower = original.lower()

        # 先检查项目术语
        for term in project_terms:
            if term.original.lower() == original_lower:
                metadata = project_meta_dict.get(term.id)
                if metadata:
                    results.append((term, metadata))

        # 如果找到项目术语，直接返回（项目术语覆盖全局术语）
        if results:
            return results

        # 否则检查全局术语
        for term in global_terms:
            if term.original.lower() == original_lower:
                metadata = global_meta_dict.get(term.id)
                if metadata:
                    results.append((term, metadata))

        return results
