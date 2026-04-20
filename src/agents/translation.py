"""Paragraph-level translation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.format_tokens import (
    TranslationPayload,
    apply_translation_payload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
    format_token_context,
)
from ..core.constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from ..core.glossary_prompt import build_glossary_prompt_entries
from ..core.models import (
    Paragraph,
    ParagraphStatus,
    Section,
    StyleGuide,
)
from ..llm.base import LLMProvider


@dataclass
class TranslationContext:
    """Runtime translation context for one paragraph."""

    glossary: Optional[Glossary] = None
    style_guide: Optional[StyleGuide] = None
    previous_paragraphs: List[Tuple[str, str]] = None
    next_preview: List[str] = None
    source_text: Optional[str] = None
    article_title: Optional[str] = None
    current_section_title: Optional[str] = None
    heading_chain: Optional[List[str]] = None
    learned_rules: Optional[List[str]] = None
    term_usage: Optional[Dict[str, List[str]]] = None

    def __post_init__(self):
        if self.previous_paragraphs is None:
            self.previous_paragraphs = []
        if self.next_preview is None:
            self.next_preview = []
        if self.heading_chain is None:
            self.heading_chain = []
        if self.learned_rules is None:
            self.learned_rules = []


class ContextWindow:
    """Sliding window of confirmed translations."""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.confirmed: List[Tuple[str, str]] = []

    def add_confirmed(self, source: str, translation: str) -> None:
        self.confirmed.append((source, translation))

    def get_context(self) -> List[Tuple[str, str]]:
        return self.confirmed[-self.window_size :]

    def clear(self) -> None:
        self.confirmed.clear()


class TranslationAgent:
    """Translate working segments while preserving hidden formatting tokens."""

    def __init__(self, llm_provider: LLMProvider, context_window_size: int = 5, timeout: Optional[int] = None):
        self.llm = llm_provider
        self.context_window = ContextWindow(window_size=context_window_size)
        self.timeout = timeout

    def translate_paragraph(
        self,
        paragraph: Paragraph,
        context: TranslationContext,
    ) -> TranslationPayload:
        dehydrated_payload = build_dehydrated_link_payload(paragraph)
        if dehydrated_payload is not None:
            return dehydrated_payload

        translation_input = build_translation_input(paragraph)
        context.source_text = paragraph.source
        llm_context = self._build_llm_context(context, paragraph)

        prompt_text = translation_input.tokenized_text or translation_input.text
        translated = self.llm.translate(prompt_text, llm_context, timeout=self.timeout)
        payload = build_translation_payload(
            paragraph,
            translated,
            token_repairer=self._repair_format_tokens,
        )
        return payload

    def translate_section(
        self,
        section: Section,
        context: TranslationContext,
        on_progress: Optional[Callable[[int, int, Paragraph], None]] = None,
    ) -> Section:
        total = len(section.paragraphs)

        for i, paragraph in enumerate(section.paragraphs):
            if paragraph.status == ParagraphStatus.APPROVED:
                if paragraph.confirmed:
                    self.context_window.add_confirmed(
                        paragraph.source,
                        paragraph.confirmed,
                    )
                continue

            context.previous_paragraphs = self.context_window.get_context()
            context.next_preview = [p.source for p in section.paragraphs[i + 1 : i + 3]]

            payload = self.translate_paragraph(paragraph, context)
            apply_translation_payload(paragraph, payload, "default")
            self.context_window.add_confirmed(paragraph.source, payload.text)

            if on_progress:
                on_progress(i + 1, total, paragraph)

        return section

    def retranslate_paragraph(
        self,
        paragraph: Paragraph,
        context: TranslationContext,
        instruction: Optional[str] = None,
    ) -> TranslationPayload:
        dehydrated_payload = build_dehydrated_link_payload(paragraph)
        if dehydrated_payload is not None:
            return dehydrated_payload

        translation_input = build_translation_input(paragraph)
        context.source_text = paragraph.source
        llm_context = self._build_llm_context(context, paragraph)
        current_translation = ""

        if instruction:
            llm_context["instruction"] = instruction

        prev_trans = paragraph.latest_translation(non_empty=True)
        if prev_trans is not None:
            current_translation = prev_trans.tokenized_text or prev_trans.text

        prompt_text = translation_input.tokenized_text or translation_input.text
        translated = self.llm.retranslate(
            prompt_text,
            current_translation=current_translation,
            context=llm_context,
        )
        return build_translation_payload(
            paragraph,
            translated,
            token_repairer=self._repair_format_tokens,
        )

    def _build_llm_context(
        self,
        context: TranslationContext,
        paragraph: Paragraph,
    ) -> Dict[str, Any]:
        llm_context: Dict[str, Any] = {}

        if context.glossary and context.glossary.terms:
            llm_context["glossary"] = build_glossary_prompt_entries(
                context.glossary,
                context.source_text,
                max_terms=MAX_GLOSSARY_TERMS_IN_PROMPT,
            )

        if context.style_guide:
            llm_context["style_guide"] = {
                "tone": context.style_guide.tone,
                "formality": context.style_guide.formality,
                "notes": context.style_guide.notes,
            }

        if context.previous_paragraphs:
            llm_context["previous_paragraphs"] = context.previous_paragraphs
        if context.next_preview:
            llm_context["next_preview"] = context.next_preview
        if context.article_title:
            llm_context["article_title"] = context.article_title
        if context.current_section_title:
            llm_context["current_section_title"] = context.current_section_title
        if context.heading_chain:
            llm_context["heading_chain"] = context.heading_chain
        if context.learned_rules:
            llm_context["learned_rules"] = context.learned_rules

        if context.term_usage:
            llm_context["term_usage"] = context.term_usage

        if paragraph.inline_elements:
            llm_context["format_tokens"] = format_token_context(paragraph)

        return llm_context

    def reset_context(self) -> None:
        self.context_window.clear()

    def load_confirmed_context(self, paragraphs: List[Paragraph]) -> None:
        self.context_window.clear()
        for paragraph in paragraphs:
            if paragraph.status == ParagraphStatus.APPROVED and paragraph.confirmed:
                self.context_window.add_confirmed(paragraph.source, paragraph.confirmed)

    def _repair_format_tokens(
        self,
        paragraph: Paragraph,
        translated_tokenized_text: str,
        issues: List[str],
    ) -> Optional[str]:
        if not paragraph.inline_elements:
            return None

        prepared = build_translation_input(paragraph)
        return self.llm.repair_format_tokens(
            source_text=prepared.tokenized_text or prepared.text,
            translated_text=translated_tokenized_text,
            format_tokens=format_token_context(paragraph),
            issues=issues,
        )


def create_translation_agent(
    llm_provider: LLMProvider,
    context_window_size: int = 5,
) -> TranslationAgent:
    """Factory helper for the default translation agent."""
    return TranslationAgent(llm_provider, context_window_size=context_window_size)
