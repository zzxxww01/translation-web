"""Backward-compatible metadata translation service wrapper."""

from __future__ import annotations

from src.core.format_tokens import (
    apply_translation_payload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
    format_token_context,
)
from src.core.models import Paragraph
from src.llm.base import LLMProvider


class MetadataTranslationService:
    """Minimal compatibility wrapper for legacy metadata tests."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def detect_and_translate_metadata(self, paragraph: Paragraph) -> bool:
        source_text = (paragraph.source or "").strip()
        if not source_text:
            return False

        paragraph.is_metadata = True
        paragraph.metadata_type = self._detect_metadata_type(source_text)

        dehydrated_payload = build_dehydrated_link_payload(paragraph)
        if dehydrated_payload is not None:
            payload = dehydrated_payload
        else:
            prepared = build_translation_input(paragraph)
            translated = self.llm.translate(
                prepared.tokenized_text or prepared.text,
                context={
                    "instruction": "Translate this metadata into concise Chinese. Preserve hidden format tokens exactly.",
                    "format_tokens": format_token_context(paragraph),
                },
            )
            payload = build_translation_payload(paragraph, translated)

        apply_translation_payload(paragraph, payload, "metadata")
        paragraph.confirm(
            payload.text,
            "metadata",
            tokenized_text=payload.tokenized_text,
            format_issues=payload.format_issues,
        )
        return True

    def _detect_metadata_type(self, source_text: str) -> str:
        normalized = source_text.lower()
        if normalized.startswith("source:") or normalized.startswith("sources:"):
            return "source"
        if normalized.startswith("by "):
            return "byline"
        return "author"
