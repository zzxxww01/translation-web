"""Translation memory and section prescan models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from .enums import RuleType, ErrorCategory
from .analysis import EnhancedTerm


class TranslationRule(BaseModel):
    """可复用的翻译规则"""

    id: str
    wrong: str
    right: str
    instruction: str
    rule_type: RuleType
    category: ErrorCategory
    source_context: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    hit_count: int = 0
    confidence: float = 0.5


class TranslationMemory(BaseModel):
    """翻译记忆存储"""

    version: int = 1
    rules: List[TranslationRule] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class PrescanTerm(BaseModel):
    """预扫描提取的术语"""

    term: str
    suggested_translation: str
    context: str = ""
    confidence: float = 0.8


class SectionPrescanResult(BaseModel):
    """章节预扫描结果（方案 C - Phase 1 Step 1）"""

    section_id: str
    new_terms: List[PrescanTerm] = Field(default_factory=list)
    term_usages: Dict[str, str] = Field(default_factory=dict)
    scan_coverage: float = 1.0
    scanned_at: datetime = Field(default_factory=datetime.now)


class TermConflict(BaseModel):
    """术语冲突信息（需要人工确认）"""

    term: str
    existing_translation: str
    new_translation: str
    existing_context: str = ""
    new_context: str = ""
    existing_section_id: str = ""
    new_section_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class TermConflictResolution(BaseModel):
    """术语冲突解决方案"""

    term: str
    chosen_translation: str
    apply_to_all: bool = True
    resolved_at: datetime = Field(default_factory=datetime.now)


class TerminologyVersion(BaseModel):
    """术语表版本（支持增量更新）"""

    version: int = 1
    terms: Dict[str, EnhancedTerm] = Field(default_factory=dict)
    conflicts: List[TermConflict] = Field(default_factory=list)
    resolved_conflicts: List[TermConflictResolution] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_term(self, term: EnhancedTerm) -> Optional[TermConflict]:
        """
        添加术语，如果存在冲突则返回冲突对象
        """
        key = term.term.lower()
        if key in self.terms:
            existing = self.terms[key]
            if existing.translation != term.translation:
                conflict = TermConflict(
                    term=term.term,
                    existing_translation=existing.translation or "",
                    new_translation=term.translation or "",
                    existing_context=existing.context_meaning,
                    new_context=term.context_meaning,
                )
                self.conflicts.append(conflict)
                return conflict
        else:
            self.terms[key] = term
            self.version += 1
            self.updated_at = datetime.now()
        return None

    def get_term(self, term: str) -> Optional[EnhancedTerm]:
        """根据术语获取翻译"""
        return self.terms.get(term.lower())

    def resolve_conflict(self, resolution: TermConflictResolution) -> None:
        """解决冲突"""
        key = resolution.term.lower()
        if key in self.terms:
            self.terms[key].translation = resolution.chosen_translation
        self.conflicts = [c for c in self.conflicts if c.term.lower() != key]
        self.resolved_conflicts.append(resolution)
        self.version += 1
        self.updated_at = datetime.now()
