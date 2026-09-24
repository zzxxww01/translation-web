"""Slack router request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..utils.json_utils import unwrap_relay_lines


class ConversationMessage(BaseModel):
    role: Literal["them", "me"]
    content: str = Field(..., max_length=50000)


class SlackReplyVariant(BaseModel):
    version: str
    english: str
    chinese: str = ""
    style: Optional[str] = None  # '简洁', '标准', '正式'; legacy labels accepted at edit boundaries


class SlackProcessRequest(BaseModel):
    message: str = Field(..., max_length=50000)
    custom_prompt: Optional[str] = Field(None, max_length=10000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=100)


class SlackProcessResponse(BaseModel):
    translation: str
    suggested_replies: list[SlackReplyVariant] = Field(default_factory=list)


class SlackSyncRequest(BaseModel):
    chinese_reply: str = Field(..., max_length=50000)


class SlackSyncResponse(BaseModel):
    english_reply: str


class SlackComposeRequest(BaseModel):
    content: str = Field(..., max_length=50000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=100)


class SlackComposeResponse(BaseModel):
    versions: list[SlackReplyVariant] = Field(default_factory=list)


class SlackRefineRequest(BaseModel):
    """Request to refine a previous result"""
    context_type: Literal["incoming", "draft"]
    original_result: str = Field(..., max_length=50000)
    adjustment_instruction: str = Field(..., max_length=10000)
    conversation_history: list[dict[str, str]] = Field(default_factory=list, max_length=100)


class SlackRefineResponse(BaseModel):
    """Response from refine endpoint"""
    refined_result: str


class SlackOptimizeRequest(BaseModel):
    content: str = Field(..., max_length=50000)
    target_language: str = Field(..., pattern="^(en|cn)$")
    context_type: str = Field(..., pattern="^(translation|grammar|tone|formality)$")
    original_text: Optional[str] = Field(None, max_length=50000)


class SlackOptimizeResponse(BaseModel):
    optimized_text: str
    improvements: list[str]
    confidence: float


VERSION_ORDER = ("A", "B", "C")
STYLE_MAP = {"A": "简洁", "B": "标准", "C": "正式"}


def normalize_variants(raw_variants: object, chinese_fallback: str = "") -> list[SlackReplyVariant]:

    from src.prompts.contracts import PromptContractError
    if not isinstance(raw_variants, list):
        raise PromptContractError("Reply variants must be an array")
    mapping = {}
    for item in raw_variants:
        if not isinstance(item, dict):
            raise PromptContractError("Invalid reply variant")
        version = item.get("version")
        english = item.get("english")
        if version not in VERSION_ORDER or version in mapping or not isinstance(english, str) or not english.strip():
            raise PromptContractError("Missing, duplicate or empty reply variant")
        chinese = item.get("chinese", chinese_fallback)
        if not isinstance(chinese, str):
            raise PromptContractError("Invalid Chinese reply")
        mapping[version] = SlackReplyVariant(version=version, english=unwrap_relay_lines(english.strip()), chinese=unwrap_relay_lines(chinese.strip()), style=STYLE_MAP[version])
    if set(mapping) != set(VERSION_ORDER):
        raise PromptContractError("Expected exactly A/B/C reply variants")
    return [mapping[key] for key in VERSION_ORDER]
