"""Slack router request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["them", "me"]
    content: str


class SlackReplyVariant(BaseModel):
    version: str
    english: str
    chinese: str = ""
    style: Optional[str] = None  # '简洁', '正式', '友好'


class SlackProcessRequest(BaseModel):
    message: str
    custom_prompt: Optional[str] = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class SlackProcessResponse(BaseModel):
    translation: str
    suggested_replies: list[SlackReplyVariant] = Field(default_factory=list)


class SlackSyncRequest(BaseModel):
    chinese_reply: str


class SlackSyncResponse(BaseModel):
    english_reply: str


class SlackComposeRequest(BaseModel):
    content: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class SlackComposeResponse(BaseModel):
    versions: list[SlackReplyVariant] = Field(default_factory=list)


class SlackRefineRequest(BaseModel):
    """Request to refine a previous result"""
    context_type: Literal["incoming", "draft"]
    original_result: str
    adjustment_instruction: str
    conversation_history: list[dict[str, str]] = []


class SlackRefineResponse(BaseModel):
    """Response from refine endpoint"""
    refined_result: str


class SlackOptimizeRequest(BaseModel):
    content: str
    target_language: str  # 'en' or 'cn'
    context_type: str  # 'translation' | 'grammar' | 'tone' | 'formality'
    original_text: Optional[str] = None


class SlackOptimizeResponse(BaseModel):
    optimized_text: str
    improvements: list[str]
    confidence: float


VERSION_ORDER = ("A", "B", "C")
STYLE_MAP = {"A": "简洁", "B": "正式", "C": "友好"}


def normalize_variants(raw_variants: object, chinese_fallback: str = "") -> list[SlackReplyVariant]:
    """Parse LLM output into a fixed A/B/C list of SlackReplyVariant."""
    variant_map: dict[str, SlackReplyVariant] = {}

    if isinstance(raw_variants, list):
        for item in raw_variants:
            if not isinstance(item, dict):
                continue

            version = str(item.get("version", "")).strip().upper()
            if version not in VERSION_ORDER:
                continue

            english = str(item.get("english", "")).strip()
            chinese = str(item.get("chinese", chinese_fallback)).strip() or chinese_fallback
            style = STYLE_MAP.get(version)
            variant_map[version] = SlackReplyVariant(
                version=version,
                english=english,
                chinese=chinese,
                style=style,
            )

    return [
        variant_map.get(
            version,
            SlackReplyVariant(version=version, english="", chinese=chinese_fallback, style=STYLE_MAP.get(version)),
        )
        for version in VERSION_ORDER
    ]
