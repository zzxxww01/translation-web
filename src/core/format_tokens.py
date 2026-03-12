"""Helpers for hidden format-token translation and export reconstruction."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

from .models import InlineElement, Paragraph


TOKEN_TYPE_MAP = {
    "link": "LINK",
    "strong": "STRONG",
    "bold": "STRONG",
    "em": "EM",
    "italic": "EM",
    "code": "CODE",
}
TOKEN_PATTERN = re.compile(
    r"\[\[\[(?P<token>(?:LINK|STRONG|EM|CODE)_\d+)\|(?P<text>.*?)\]\]\]",
    re.DOTALL,
)


class FormatRecoveryError(ValueError):
    """Raised when a block cannot be safely reconstructed for export."""


@dataclass
class TranslationPayload:
    """Plain-text + hidden-token translation result."""

    text: str
    tokenized_text: Optional[str] = None
    format_issues: List[str] = field(default_factory=list)

    @property
    def format_valid(self) -> bool:
        return not self.format_issues


def assign_span_ids(elements: Optional[Sequence[InlineElement]]) -> List[InlineElement]:
    """Ensure every inline span has a stable token id."""
    if not elements:
        return []

    counters: dict[str, int] = {}
    assigned: List[InlineElement] = []
    for element in elements:
        normalized_type = normalize_inline_type(element.type)
        counter = counters.get(normalized_type, 0) + 1
        counters[normalized_type] = counter
        clone = element.model_copy(deep=True)
        clone.type = normalized_type
        clone.span_id = clone.span_id or f"{TOKEN_TYPE_MAP[normalized_type]}_{counter}"
        assigned.append(clone)
    return assigned


def normalize_inline_type(inline_type: str) -> str:
    """Collapse legacy aliases onto one canonical type set."""
    if inline_type == "bold":
        return "strong"
    if inline_type == "italic":
        return "em"
    return inline_type


def expected_token_ids(elements: Optional[Sequence[InlineElement]]) -> List[str]:
    """Return token ids in source order."""
    return [element.span_id for element in assign_span_ids(elements) if element.span_id]


def tokenize_text(text: str, elements: Optional[Sequence[InlineElement]]) -> str:
    """Replace inline spans with hidden translation tokens."""
    assigned = assign_span_ids(elements)
    if not assigned:
        return text

    result = text
    for element in sorted(assigned, key=lambda item: item.start, reverse=True):
        token_id = element.span_id
        if not token_id:
            continue
        replacement = f"[[[{token_id}|{element.text}]]]"
        result = result[: element.start] + replacement + result[element.end :]
    return result


def strip_token_markup(tokenized_text: str) -> str:
    """Drop token wrappers but keep the translated inner text."""
    if not tokenized_text:
        return tokenized_text
    return TOKEN_PATTERN.sub(lambda match: match.group("text"), tokenized_text)


def validate_tokenized_text(
    tokenized_text: str,
    elements: Optional[Sequence[InlineElement]],
) -> List[str]:
    """Validate that all expected tokens survived exactly once."""
    assigned = assign_span_ids(elements)
    expected = [element.span_id for element in assigned if element.span_id]
    if not expected:
        return []

    issues: List[str] = []
    found = TOKEN_PATTERN.findall(tokenized_text)
    found_ids = [token_id for token_id, _ in found]

    for token_id in expected:
        count = found_ids.count(token_id)
        if count == 0:
            issues.append(f"Missing token {token_id}.")
        elif count > 1:
            issues.append(f"Duplicate token {token_id}.")

    unexpected = sorted(set(found_ids) - set(expected))
    for token_id in unexpected:
        issues.append(f"Unexpected token {token_id}.")

    lookup = {element.span_id: element for element in assigned if element.span_id}
    for token_id, token_text in found:
        element = lookup.get(token_id)
        if not element:
            continue
        if element.type == "code" and token_text != element.text:
            issues.append(f"Code token {token_id} must keep its original text.")
        if not token_text.strip():
            issues.append(f"Token {token_id} cannot be empty.")

    return issues


def restore_markdown_from_tokenized(
    tokenized_text: str,
    elements: Optional[Sequence[InlineElement]],
) -> str:
    """Restore inline markdown using translated token inner text."""
    if not elements:
        return tokenized_text

    lookup = {
        element.span_id: element
        for element in assign_span_ids(elements)
        if element.span_id
    }

    def replace(match: re.Match[str]) -> str:
        token_id = match.group("token")
        translated_text = match.group("text")
        element = lookup.get(token_id)
        if not element:
            return translated_text
        if element.type == "link" and element.href:
            if element.title:
                return f'[{translated_text}]({element.href} "{element.title}")'
            return f"[{translated_text}]({element.href})"
        if element.type == "strong":
            return f"**{translated_text}**"
        if element.type == "em":
            return f"*{translated_text}*"
        if element.type == "code":
            return f"`{element.text}`"
        return translated_text

    return TOKEN_PATTERN.sub(replace, tokenized_text)


def restore_html_from_tokenized(
    tokenized_text: str,
    elements: Optional[Sequence[InlineElement]],
) -> str:
    """Restore inline HTML using translated token inner text."""
    if not elements:
        return html.escape(tokenized_text)

    lookup = {
        element.span_id: element
        for element in assign_span_ids(elements)
        if element.span_id
    }

    def replace(match: re.Match[str]) -> str:
        token_id = match.group("token")
        translated_text = html.escape(match.group("text"))
        element = lookup.get(token_id)
        if not element:
            return translated_text
        if element.type == "link" and element.href:
            title_attr = (
                f' title="{html.escape(element.title)}"' if element.title else ""
            )
            return (
                f'<a href="{html.escape(element.href, quote=True)}"{title_attr}>'
                f"{translated_text}</a>"
            )
        if element.type == "strong":
            return f"<strong>{translated_text}</strong>"
        if element.type == "em":
            return f"<em>{translated_text}</em>"
        if element.type == "code":
            return f"<code>{html.escape(element.text)}</code>"
        return translated_text

    parts: List[str] = []
    cursor = 0
    for match in TOKEN_PATTERN.finditer(tokenized_text):
        if match.start() > cursor:
            parts.append(html.escape(tokenized_text[cursor:match.start()]))
        parts.append(replace(match))
        cursor = match.end()
    if cursor < len(tokenized_text):
        parts.append(html.escape(tokenized_text[cursor:]))
    return "".join(parts)


def build_translation_payload(
    paragraph: Paragraph,
    translated_tokenized_text: str,
) -> TranslationPayload:
    """Normalize model output into a saved translation payload."""
    if not paragraph.inline_elements:
        return TranslationPayload(
            text=translated_tokenized_text,
            tokenized_text=None,
            format_issues=[],
        )
    issues = validate_tokenized_text(translated_tokenized_text, paragraph.inline_elements)
    return TranslationPayload(
        text=strip_token_markup(translated_tokenized_text),
        tokenized_text=translated_tokenized_text if not issues else None,
        format_issues=issues,
    )


def build_translation_input(paragraph: Paragraph) -> TranslationPayload:
    """Prepare a working segment for translation."""
    tokenized_source = tokenize_text(paragraph.source, paragraph.inline_elements)
    return TranslationPayload(
        text=paragraph.source,
        tokenized_text=tokenized_source if paragraph.inline_elements else None,
        format_issues=[],
    )


def apply_translation_payload(
    paragraph: Paragraph,
    payload: TranslationPayload,
    model: str,
) -> None:
    """Persist one translation payload onto a paragraph."""
    paragraph.add_translation(
        payload.text,
        model,
        tokenized_text=payload.tokenized_text,
        format_issues=payload.format_issues,
    )


def group_paragraphs_by_parent_block(paragraphs: Sequence[Paragraph]) -> List[List[Paragraph]]:
    """Group working segments by parent block, preserving section order."""
    groups: List[List[Paragraph]] = []
    by_key: dict[str, List[Paragraph]] = {}
    order: List[str] = []

    for paragraph in paragraphs:
        key = paragraph.parent_block_id or paragraph.id
        if key not in by_key:
            by_key[key] = []
            order.append(key)
        by_key[key].append(paragraph)

    for key in order:
        groups.append(
            sorted(
                by_key[key],
                key=lambda item: (item.segment_start, item.index),
            )
        )
    return groups


def reconstruct_block_tokenized_text(
    paragraphs: Sequence[Paragraph],
    fallback_to_source: bool = True,
) -> TranslationPayload:
    """Combine child segment translations back into one parent-block token stream."""
    if not paragraphs:
        return TranslationPayload(text="", tokenized_text="", format_issues=[])

    ordered = sorted(paragraphs, key=lambda item: (item.segment_start, item.index))
    parent_text = ordered[0].parent_block_plain_text or ordered[0].source
    pieces: List[str] = []
    cursor = 0
    issues: List[str] = []

    for paragraph in ordered:
        seg_start = paragraph.segment_start
        seg_end = paragraph.segment_end if paragraph.segment_end is not None else len(parent_text)
        gap = parent_text[cursor:seg_start]
        if gap:
            pieces.append(gap)

        tokenized_text = paragraph.best_tokenized_translation_text(
            fallback_to_source=not paragraph.has_usable_translation() and fallback_to_source
        )
        if tokenized_text is None:
            if not paragraph.has_usable_translation() and fallback_to_source:
                tokenized_text = tokenize_text(paragraph.source, paragraph.inline_elements)
            elif paragraph.expected_tokens:
                issues.append(
                    f"{paragraph.id}: missing tokenized translation for formatted segment."
                )
                tokenized_text = paragraph.best_translation_text(fallback_to_source=fallback_to_source)
            else:
                tokenized_text = paragraph.best_translation_text(fallback_to_source=fallback_to_source)

        issues.extend(f"{paragraph.id}: {issue}" for issue in paragraph.best_format_issues())
        pieces.append(tokenized_text)
        cursor = seg_end

    tail = parent_text[cursor:]
    if tail:
        pieces.append(tail)

    tokenized_text = "".join(pieces)
    parent_elements = ordered[0].parent_inline_elements or ordered[0].inline_elements or []
    issues.extend(validate_tokenized_text(tokenized_text, parent_elements))
    return TranslationPayload(
        text=strip_token_markup(tokenized_text),
        tokenized_text=tokenized_text if not issues else None,
        format_issues=issues,
    )


def require_valid_reconstruction(
    paragraphs: Sequence[Paragraph],
    fallback_to_source: bool = True,
) -> TranslationPayload:
    """Reconstruct one parent block or raise a hard export failure."""
    payload = reconstruct_block_tokenized_text(paragraphs, fallback_to_source=fallback_to_source)
    if payload.format_issues:
        block_id = paragraphs[0].parent_block_id or paragraphs[0].id
        message = "; ".join(payload.format_issues)
        raise FormatRecoveryError(f"Block {block_id} failed format recovery: {message}")
    return payload


def paragraph_has_tokens(paragraph: Paragraph) -> bool:
    """Whether the working segment needs token-aware export recovery."""
    return bool(paragraph.expected_tokens)


def sorted_block_groups(paragraphs: Sequence[Paragraph]) -> List[List[Paragraph]]:
    """Group paragraphs by parent block and sort by block index."""
    groups = group_paragraphs_by_parent_block(paragraphs)
    return sorted(
        groups,
        key=lambda group: (
            group[0].parent_block_index
            if group[0].parent_block_index is not None
            else group[0].index
        ),
    )


def format_token_context(paragraph: Paragraph) -> List[dict]:
    """Build the token context list for LLM prompts from a paragraph's inline elements."""
    return [
        {
            "id": element.span_id,
            "type": element.type,
            "text": element.text,
            "href": element.href,
            "title": element.title,
        }
        for element in (paragraph.inline_elements or [])
        if element.span_id
    ]
