"""
Tools router request/response models.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


# 内容长度限制（公网环境防止滥用）
MAX_TRANSLATE_TEXT_LENGTH = 10000  # 10K 字符
MAX_EMAIL_CONTENT_LENGTH = 10000
MAX_EMAIL_FIELD_LENGTH = 200
MAX_TIMEZONE_INPUT_LENGTH = 200


class TranslateRequest(BaseModel):
    text: str = Field(..., max_length=MAX_TRANSLATE_TEXT_LENGTH)
    source_lang: str = "auto"  # auto, en, zh
    target_lang: str = "zh"  # en, zh

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v


class TranslateResponse(BaseModel):
    translation: str


class EmailReplyRequest(BaseModel):
    sender: str = Field(default="", max_length=MAX_EMAIL_FIELD_LENGTH)
    subject: str = Field(default="", max_length=MAX_EMAIL_FIELD_LENGTH)
    content: str = Field(..., max_length=MAX_EMAIL_CONTENT_LENGTH)
    style: str = "professional"  # professional, polite, casual

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Email content cannot be empty")
        return v


class EmailReplyResponse(BaseModel):
    replies: List[dict]


class TimezoneConvertRequest(BaseModel):
    input: str = Field(..., max_length=MAX_TIMEZONE_INPUT_LENGTH)
    source_timezone: str = "auto"  # auto, EST5EDT, CST6CDT, MST7MDT, PST8PDT, Asia/Shanghai

    @field_validator('input')
    @classmethod
    def validate_input(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Input cannot be empty")
        return v


class TimezoneConvertResponse(BaseModel):
    est: str
    cst: str
    mst: str
    pst: str
    beijing: str
    original: str
