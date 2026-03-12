"""
Translate router request/response models.
"""

from typing import Optional

from pydantic import BaseModel


class PostTranslateRequest(BaseModel):
    content: str
    preserve_tone: bool = True
    custom_prompt: Optional[str] = None


class PostTranslateResponse(BaseModel):
    translation: str


class GenerateTitleRequest(BaseModel):
    content: str
    instruction: Optional[str] = None


class GenerateTitleResponse(BaseModel):
    title: str


class ProjectAnalysisResponse(BaseModel):
    summary: str
    notes: list[str]
    key_terms: list[str]


class SectionAnalysisResponse(BaseModel):
    summary: str
    tips: list[str]


class PostOptimizeRequest(BaseModel):
    original_text: str
    current_translation: str
    instruction: str
    conversation_history: Optional[list[dict]] = None


class PostOptimizeResponse(BaseModel):
    optimized_translation: str


class FullTranslateRequest(BaseModel):
    pass


class ResolveConflictRequest(BaseModel):
    term: str
    chosen_translation: str
    apply_to_all: bool = True


class ResolveConflictResponse(BaseModel):
    status: str
    affected_paragraphs: int
