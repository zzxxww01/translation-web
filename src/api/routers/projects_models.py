"""
Shared request/response models for project routers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str
    html_path: str


class TranslateRequest(BaseModel):
    model: str = "gemini"
    instruction: Optional[str] = None


class DirectTranslateRequest(BaseModel):
    model: str = "gemini"


class ConfirmRequest(BaseModel):
    translation: str


class WordMeaningMessage(BaseModel):
    role: str
    content: str


class WordMeaningRequest(BaseModel):
    word: str
    query: str
    history: List[WordMeaningMessage] = Field(default_factory=list)
    model: str = "gemini"


class WordMeaningResponse(BaseModel):
    answer: str


class UpdateParagraphRequest(BaseModel):
    translation: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    status: str
    progress: dict
    created_at: str


class SectionResponse(BaseModel):
    section_id: str
    title: str
    title_translation: Optional[str]
    total_paragraphs: int
    approved_count: int
    is_complete: bool


class ParagraphResponse(BaseModel):
    id: str
    index: int
    source: str
    translation: Optional[str]
    status: str
