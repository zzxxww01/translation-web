"""Validate generation termination before partial content reaches persistence."""
from __future__ import annotations
from typing import Any
from .errors import LLMError, LLMOutputTruncatedError


def ensure_complete_generation(reason: Any) -> None:
    # Older transports and test doubles may omit finish metadata entirely.
    # When the provider supplies it, never discard it merely because text exists.
    value = getattr(reason, 'value', reason)
    if value is None or value == '':
        return
    if not isinstance(value, str):
        raise LLMError('Invalid model termination metadata')
    value = value.rsplit('.', 1)[-1].upper()
    if value in {'LENGTH', 'MAX_TOKENS', 'MAX_OUTPUT_TOKENS'}:
        raise LLMOutputTruncatedError('Model generation reached its output limit')
    if value not in {'STOP', 'END_TURN'}:
        raise LLMError(f'Model generation did not finish normally ({value})')


def gemini_response_text(data: dict) -> str:
    candidates = data.get('candidates')
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise LLMError('Model response contains no usable candidate')
    candidate = candidates[0]
    ensure_complete_generation(candidate.get('finishReason'))
    parts = candidate.get('content', {}).get('parts', [])
    if not isinstance(parts, list):
        raise LLMError('Invalid model response parts')
    text = ''.join(
        part['text'] for part in parts
        if isinstance(part, dict) and not part.get('thought') and isinstance(part.get('text'), str)
    )
    if not text.strip():
        raise LLMError('Model response contains no answer text')
    return text
