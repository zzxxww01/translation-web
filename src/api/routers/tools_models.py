"""
Tools router request/response models.
"""

from typing import List

from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"  # auto, en, zh
    target_lang: str = "zh"  # en, zh


class TranslateResponse(BaseModel):
    translation: str


class EmailReplyRequest(BaseModel):
    sender: str = ""
    subject: str = ""
    content: str
    style: str = "professional"  # professional, polite, casual


class EmailReplyResponse(BaseModel):
    replies: List[dict]


class TimezoneConvertRequest(BaseModel):
    input: str
    source_timezone: str = "auto"  # auto, EST5EDT, CST6CDT, MST7MDT, PST8PDT, Asia/Shanghai


class TimezoneConvertResponse(BaseModel):
    est: str
    cst: str
    mst: str
    pst: str
    beijing: str
    original: str
