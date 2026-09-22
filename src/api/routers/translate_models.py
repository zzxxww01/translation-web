"""
Translate router request/response models.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from src.core.efficiency import EfficiencyOptions


# 内容长度限制（公网环境防止滥用）
MAX_POST_CONTENT_LENGTH = 10000  # 10K 字符，约 3000 词
MAX_CUSTOM_PROMPT_LENGTH = 2000


class PostTranslateRequest(BaseModel):
    content: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    preserve_tone: bool = True
    include_hashtags: bool = True
    custom_prompt: Optional[str] = Field(None, max_length=MAX_CUSTOM_PROMPT_LENGTH)
    model: Optional[str] = None

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class PostTranslateResponse(BaseModel):
    translation: str
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    fallback_used: bool = False


class GenerateTitleRequest(BaseModel):
    content: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    instruction: Optional[str] = None
    model: Optional[str] = None

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class GenerateTitleResponse(BaseModel):
    title: str
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    fallback_used: bool = False


class PostHashtagRequest(BaseModel):
    content: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    translation: str = Field("", max_length=MAX_POST_CONTENT_LENGTH)
    model: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_hashtag_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content cannot be empty")
        return value


class PostHashtagResponse(BaseModel):
    tags: list[str]
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    fallback_used: bool = False


class ProjectAnalysisResponse(BaseModel):
    summary: str
    notes: list[str]
    key_terms: list[str]


class SectionAnalysisResponse(BaseModel):
    summary: str
    tips: list[str]


class PostOptimizeRequest(BaseModel):
    original_text: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    current_translation: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    instruction: Optional[str] = Field(None, max_length=1000)
    option_id: Optional[str] = None
    include_hashtags: Optional[bool] = None
    conversation_history: Optional[list[dict]] = Field(None, max_length=10)
    model: Optional[str] = None

    @field_validator('original_text', 'current_translation')
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v

    @field_validator('conversation_history')
    @classmethod
    def validate_history(cls, v: Optional[list[dict]]) -> Optional[list[dict]]:
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Conversation history too long (max 10 messages)")
        for msg in v:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                raise ValueError("Invalid conversation history format")
        return v


class PostOptimizeResponse(BaseModel):
    optimized_translation: str
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    fallback_used: bool = False


class FullTranslateRequest(BaseModel):
    model: Optional[str] = None
    efficiency: EfficiencyOptions = Field(default_factory=EfficiencyOptions)


class LongformWorkflowStartRequest(BaseModel):
    efficiency: EfficiencyOptions = Field(default_factory=EfficiencyOptions)
    method: Literal["normal", "four-step"] = "four-step"
    model: Optional[str] = Field(None, max_length=100)
    # 覆盖已有译文的范围。默认 resume 是历史行为——只翻没有可用译文的段落。
    # section 需要同时给出 retranslate_section_ids。
    retranslate_scope: Literal["resume", "section", "all"] = "resume"
    retranslate_section_ids: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def _check_section_ids(self) -> "LongformWorkflowStartRequest":
        if self.retranslate_scope == "section" and not self.retranslate_section_ids:
            raise ValueError(
                "retranslate_scope='section' requires retranslate_section_ids"
            )
        if self.retranslate_scope != "section" and self.retranslate_section_ids:
            # 范围不是 section 时带 id 属于调用方笔误，静默忽略会让用户以为只重译了部分。
            raise ValueError(
                "retranslate_section_ids is only valid with retranslate_scope='section'"
            )
        return self


class ResolveConflictRequest(BaseModel):
    term: str
    chosen_translation: str
    apply_to_all: bool = True


# Pre-defined post optimization instruction templates.
from src.prompts.editing_options import POST_OPTIMIZE_OPTIONS


def resolve_post_optimize_instruction(
    instruction: Optional[str], option_id: Optional[str]
) -> str:
    """
    Resolve optimization instruction. Prioritizes custom instruction if provided,
    otherwise looks up the option_id.
    """
    if instruction and instruction.strip():
        return instruction.strip()

    if option_id and option_id in POST_OPTIMIZE_OPTIONS:
        return POST_OPTIMIZE_OPTIONS[option_id]

    return ""
