"""
Shared request/response models for project routers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str
    html_path: str


class TranslateRequest(BaseModel):
    instruction: Optional[str] = None
    option_id: Optional[str] = None


class DirectTranslateRequest(BaseModel):
    pass


class ConfirmRequest(BaseModel):
    translation: str


class WordMeaningMessage(BaseModel):
    role: str
    content: str


class WordMeaningRequest(BaseModel):
    word: str
    query: str
    history: List[WordMeaningMessage] = Field(default_factory=list)


class WordMeaningResponse(BaseModel):
    answer: str


class UpdateParagraphRequest(BaseModel):
    translation: Optional[str] = None
    status: Optional[str] = None
    edit_source: Optional[str] = None
    source_text: Optional[str] = None


class BatchTranslateRequest(BaseModel):
    paragraph_ids: List[str]
    instruction: Optional[str] = None
    option_id: Optional[str] = None


class BatchTranslateResponse(BaseModel):
    translations: List[dict]
    success_count: int
    error_count: int
    errors: List[dict] = Field(default_factory=list)


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
