"""
Shared request/response models for project routers.
"""

from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("translation")
    @classmethod
    def reject_blank_translation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Translation cannot be blank")
        return value


class WordMeaningMessage(BaseModel):
    role: Literal["user", "assistant"]
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
    paragraph_ids: List[str] = Field(..., min_length=1, max_length=100)

    @field_validator("paragraph_ids")
    @classmethod
    def validate_paragraph_ids(cls, values: List[str]) -> List[str]:
        if any(not value or value != value.strip() or len(value) > 200 for value in values):
            raise ValueError("Paragraph ids must be non-blank, unpadded and at most 200 characters")
        if len(values) != len(set(values)):
            raise ValueError("Paragraph ids must be unique")
        return values

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
