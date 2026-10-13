"""Normalize vendor usage without inventing missing counts or double billing.

OpenAI-compatible completion_tokens already includes reasoning tokens. Gemini
candidatesTokenCount does not include thoughtsTokenCount. Preserve both visible
output and billable-output counts. Tool/cache-storage charges are not inferred.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


def value(obj: Any, *names: str) -> int | None:
    for name in names:
        item = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            return item
    return None


def child(obj: Any, name: str):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    billable_output_tokens: int | None = None

    def as_metrics(self) -> dict:
        return asdict(self)


def openai_usage(usage: Any) -> TokenUsage:
    inputs = value(usage, "prompt_tokens", "input_tokens")
    outputs = value(usage, "completion_tokens", "output_tokens")
    cached = value(child(usage, "prompt_tokens_details"), "cached_tokens")
    if cached is None:
        cached = value(usage, "prompt_cache_hit_tokens")
    if cached is not None and inputs is not None and cached > inputs:
        cached = None  # Invalid vendor metadata is unknown, not silently clamped.
    reasoning = value(child(usage, "completion_tokens_details"), "reasoning_tokens")
    return TokenUsage(inputs, outputs, value(usage, "total_tokens"), cached, reasoning, outputs)


def gemini_usage(usage: Any) -> TokenUsage:
    inputs = value(usage, "prompt_token_count", "promptTokenCount")
    visible = value(usage, "candidates_token_count", "candidatesTokenCount")
    thoughts = value(usage, "thoughts_token_count", "thoughtsTokenCount")
    total = value(usage, "total_token_count", "totalTokenCount")
    cached = value(usage, "cached_content_token_count", "cachedContentTokenCount")
    if cached is not None and inputs is not None and cached > inputs:
        cached = None
    # Missing thoughts means zero only when the supplied total proves that all
    # generated tokens are already accounted for. Otherwise billing is unknown.
    if thoughts is None and inputs is not None and visible is not None and total == inputs + visible:
        thoughts = 0
    billable = visible + thoughts if visible is not None and thoughts is not None else None
    return TokenUsage(inputs, visible, total, cached, thoughts, billable)
