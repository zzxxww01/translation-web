"""
Shared request/response models for project routers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    html_path: str = Field(..., min_length=1, max_length=500)


class TranslateRequest(BaseModel):
    instruction: Optional[str] = Field(None, max_length=2000)
    option_id: Optional[str] = Field(None, max_length=100)


class DirectTranslateRequest(BaseModel):
    pass


class ConfirmRequest(BaseModel):
    translation: str = Field(..., min_length=1, max_length=50000)


class WordMeaningMessage(BaseModel):
    role: str = Field(..., max_length=50)
    content: str = Field(..., max_length=10000)


class WordMeaningRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=200)
    query: str = Field(..., min_length=1, max_length=2000)
    history: List[WordMeaningMessage] = Field(default_factory=list, max_length=50)


class WordMeaningResponse(BaseModel):
    answer: str


class UpdateParagraphRequest(BaseModel):
    translation: Optional[str] = Field(None, max_length=50000)
    status: Optional[str] = Field(None, max_length=50)
    edit_source: Optional[str] = Field(None, max_length=50)
    source_text: Optional[str] = Field(None, max_length=50000)


class BatchTranslateRequest(BaseModel):
    paragraph_ids: List[str] = Field(..., max_length=100)
    instruction: Optional[str] = Field(None, max_length=2000)
    option_id: Optional[str] = Field(None, max_length=100)


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
