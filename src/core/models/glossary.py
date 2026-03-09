"""Glossary models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .enums import TranslationStrategy


class GlossaryTerm(BaseModel):
    """术语表条目"""

    original: str
    translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None
    first_occurrence: Optional[str] = None
    scope: str = "project"
    source: str = "manual"
    status: str = "active"
    updated_at: datetime = Field(default_factory=datetime.now)


class Glossary(BaseModel):
    """术语表"""

    version: int = 1
    terms: List[GlossaryTerm] = Field(default_factory=list)

    def get_term(self, original: str) -> Optional[GlossaryTerm]:
        """根据原文查找术语"""
        for term in self.terms:
            if term.original.lower() == original.lower():
                return term
        return None

    def add_term(self, term: GlossaryTerm) -> None:
        """添加术语"""
        existing = self.get_term(term.original)
        if existing:
            idx = self.terms.index(existing)
            self.terms[idx] = term
        else:
            self.terms.append(term)
