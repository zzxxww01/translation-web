"""
Slack router request/response models.
"""

from typing import Optional

from pydantic import BaseModel


class SlackProcessRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    custom_prompt: Optional[str] = None


class SlackProcessResponse(BaseModel):
    translation: str
    super_casual: str
    super_casual_cn: str
    friendly_pro: str
    friendly_pro_cn: str
    polite_casual: str
    polite_casual_cn: str


class SlackSyncRequest(BaseModel):
    chinese_reply: str
    conversation_id: Optional[str] = None


class SlackSyncResponse(BaseModel):
    english_reply: str


class SlackComposeRequest(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    tone: Optional[str] = "all"


class SlackComposeResponse(BaseModel):
    casual: str
    professional: str
    formal: str


class SlackOptimizeRequest(BaseModel):
    content: str
    target_language: str  # 'en' or 'cn'
    context_type: str  # 'translation' | 'grammar' | 'tone' | 'formality'
    conversation_id: Optional[str] = None
    original_text: Optional[str] = None


class SlackOptimizeResponse(BaseModel):
    optimized_text: str
    improvements: list[str]
    confidence: float
