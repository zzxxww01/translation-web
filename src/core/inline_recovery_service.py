import logging
from typing import Any, Optional

from .format_tokens import (
    FormatRecoveryError,
    reconstruct_block_tokenized_text,
    require_valid_reconstruction,
    restore_markdown_from_tokenized,
    sorted_block_groups,
    tokenize_text,
)
from .models import ElementType, Paragraph, Section


class InlineRecoveryService:
    """Render and recover markdown blocks without coupling to project storage."""

    def __init__(self, logger_: logging.Logger | None = None) -> None:
        self._logger = logger_ or logging.getLogger(__name__)

    def format_markdown_line(self, element_type: ElementType, text: str) -> str:
        if element_type == ElementType.H3:
            return f"### {text}"
        if element_type == ElementType.H4:
            return f"#### {text}"
        if element_type == ElementType.LI:
            return f"- {text}"
        if element_type == ElementType.BLOCKQUOTE:
            if text.startswith("*") and text.endswith("*"):
                return f"> {text}"
            if text.startswith("_") and text.endswith("_"):
                return f"> {text}"
            if text.startswith(("“", '"', "'")):
                return f"> *{text}*"
            return f"> {text}"
        return text

    def group_section_blocks(self, section: Section) -> list[list[Paragraph]]:
        return sorted_block_groups(section.paragraphs)

    def render_source_block_markdown(self, paragraphs: list[Paragraph]) -> str:
        first = paragraphs[0]
        if first.parent_block_markdown:
            return first.parent_block_markdown
        if first.source_html and first.element_type in {ElementType.IMAGE, ElementType.TABLE}:
            return first.source_html
        if first.inline_elements:
            tokenized = tokenize_text(first.source, first.inline_elements)
            return restore_markdown_from_tokenized(tokenized, first.inline_elements)
        return self.format_markdown_line(first.element_type, first.source)

    def render_block_markdown(
        self,
        paragraphs: list[Paragraph],
        fallback_to_source: bool = True,
    ) -> str:
        first = paragraphs[0]
        block_type = first.parent_block_type or first.element_type

        if block_type == ElementType.IMAGE:
            return first.parent_block_markdown or first.source_html or f"![image]({first.source})"
        if block_type == ElementType.TABLE:
            return first.parent_block_markdown or first.parent_source_html or first.source
        if block_type == ElementType.CODE:
            try:
                text = require_valid_reconstruction(
                    paragraphs,
                    fallback_to_source=fallback_to_source,
                ).text
            except FormatRecoveryError as error:
                self._logger.warning(
                    "Format recovery failed for code block %s, fallback to plain export: %s",
                    first.parent_block_id or first.id,
                    error,
                )
                text = reconstruct_block_tokenized_text(
                    paragraphs,
                    fallback_to_source=fallback_to_source,
                ).text
            return f"```\n{text}\n```"

        try:
            payload = require_valid_reconstruction(
                paragraphs, fallback_to_source=fallback_to_source
            )
            if first.parent_inline_elements:
                text = restore_markdown_from_tokenized(
                    payload.tokenized_text or payload.text,
                    first.parent_inline_elements,
                )
            else:
                text = payload.text
        except FormatRecoveryError as error:
            self._logger.warning(
                "Format recovery failed for block %s, attempting smart fallback: %s",
                first.parent_block_id or first.id,
                error,
            )
            plain_text = reconstruct_block_tokenized_text(
                paragraphs,
                fallback_to_source=fallback_to_source,
            ).text

            if first.parent_inline_elements and first.source:
                text = self.smart_fallback_restore_inline_elements(
                    source_text=first.source,
                    translated_text=plain_text,
                    elements=first.parent_inline_elements,
                    block_id=first.parent_block_id or first.id,
                )
            else:
                text = plain_text
        return self.format_markdown_line(block_type, text)

    def smart_fallback_restore_inline_elements(
        self,
        source_text: str,
        translated_text: str,
        elements: list[Any],
        block_id: str,
    ) -> str:
        result = translated_text
        link_elements = [e for e in elements if e.type == "link"]

        for element in reversed(link_elements):
            try:
                result = self.restore_single_link(
                    source_text=source_text,
                    translated_text=result,
                    link_element=element,
                )
            except Exception as error:  # pragma: no cover - defensive logging path
                self._logger.warning(
                    "Failed to restore link %s in block %s: %s",
                    getattr(element, "href", "unknown"),
                    block_id,
                    error,
                )
        return result

    def restore_single_link(
        self,
        source_text: str,
        translated_text: str,
        link_element: Any,
    ) -> str:
        link_start = source_text.find(link_element.text)
        if link_start == -1:
            self._logger.debug(
                "Cannot locate link text '%s' in source, wrapping entire translation",
                link_element.text[:50],
            )
            return f"[{translated_text}]({link_element.href})"

        relative_pos = link_start / len(source_text) if len(source_text) > 0 else 0.5

        if link_element.text in translated_text:
            match_start = translated_text.find(link_element.text)
            match_end = match_start + len(link_element.text)
            return (
                translated_text[:match_start]
                + f"[{link_element.text}]({link_element.href})"
                + translated_text[match_end:]
            )

        expected_pos = int(len(translated_text) * relative_pos)
        sentence_breaks = [0]
        for index, char in enumerate(translated_text):
            if char in "，。！？；：、":
                sentence_breaks.append(index + 1)
        sentence_breaks.append(len(translated_text))

        for index in range(len(sentence_breaks) - 1):
            start = sentence_breaks[index]
            end = sentence_breaks[index + 1]
            if start <= expected_pos < end:
                segment = translated_text[start:end].strip("，。！？；：、 ")
                if segment:
                    return (
                        translated_text[:start]
                        + f"[{segment}]({link_element.href})"
                        + translated_text[end:]
                    )
                break

        self._logger.debug(
            "No good sentence boundary found for link text '%s', wrapping entire translation",
            link_element.text[:50],
        )
        return f"[{translated_text}]({link_element.href})"

    def extract_chinese_word_candidates(
        self,
        text: str,
        center: int,
        max_candidates: int = 5,
    ) -> list[tuple[int, int, str]]:
        candidates: list[tuple[int, int, str, float]] = []
        word_lengths = [4, 3, 5, 2, 6]
        search_start = max(0, center - 20)
        search_end = min(len(text), center + 20)
        seen: set[tuple[int, int]] = set()

        for length in word_lengths:
            for start in range(search_start, min(search_end, len(text) - length + 1)):
                end = start + length
                candidate = text[start:end]
                if (start, end) in seen:
                    continue
                seen.add((start, end))

                chinese_chars = sum(1 for char in candidate if "\u4e00" <= char <= "\u9fff")
                if chinese_chars < length * 0.9:
                    continue

                boundary_score = 0
                if start == 0 or not ("\u4e00" <= text[start - 1] <= "\u9fff"):
                    boundary_score += 1
                if end == len(text) or not ("\u4e00" <= text[end] <= "\u9fff"):
                    boundary_score += 1

                candidate_center = (start + end) // 2
                distance = abs(candidate_center - center)
                score = boundary_score * 20 - distance * 0.3
                candidates.append((start, end, candidate, score))

        candidates.sort(key=lambda item: item[3], reverse=True)
        return [(start, end, text_) for start, end, text_, _ in candidates[:max_candidates]]

    def find_best_match_window(
        self,
        text: str,
        center: int,
        estimated_length: int,
        reference: str,
        source_text: str = "",
        link_start: int = 0,
    ) -> Optional[tuple[int, int, str]]:
        if not text:
            return None

        before_context: list[str] = []
        after_context: list[str] = []
        if source_text and link_start >= 0:
            before_start = max(0, link_start - 20)
            before_context = (
                source_text[before_start:link_start].strip().split()[-2:] if link_start > 0 else []
            )
            link_end = link_start + len(reference)
            after_end = min(len(source_text), link_end + 20)
            after_context = (
                source_text[link_end:after_end].strip().split()[:2]
                if link_end < len(source_text)
                else []
            )

        search_start = max(0, center - len(text) // 2)
        search_end = min(len(text), center + len(text) // 2)
        min_window = max(1, estimated_length // 5)
        max_window = min(len(text), int(estimated_length * 1.5))

        best_score = 0.0
        best_match: Optional[tuple[int, int, str]] = None
        for window_size in range(min_window, max_window + 1):
            for start in range(search_start, min(search_end, len(text) - window_size + 1)):
                end = start + window_size
                candidate = text[start:end]
                score = self.calculate_match_score(
                    candidate=candidate,
                    reference=reference,
                    candidate_pos=start,
                    expected_pos=center,
                    translated_text=text,
                    before_context=before_context,
                    after_context=after_context,
                )
                if score > best_score:
                    best_score = score
                    best_match = (start, end, candidate)
        return best_match if best_score > 0.4 else None

    def calculate_match_score(
        self,
        candidate: str,
        reference: str,
        candidate_pos: int,
        expected_pos: int,
        translated_text: str = "",
        before_context: list[str] | None = None,
        after_context: list[str] | None = None,
    ) -> float:
        del before_context, after_context
        has_alpha_ref = any(char.isalpha() and ord(char) < 128 for char in reference)
        has_alpha_cand = any(char.isalpha() and ord(char) < 128 for char in candidate)

        if has_alpha_ref and not has_alpha_cand:
            expected_len = len(reference) / 4.0
            len_diff = abs(len(candidate) - expected_len)
            len_score = 1.0 / (1.0 + len_diff)
        else:
            len_score = min(len(candidate), len(reference)) / max(len(candidate), len(reference), 1)

        completeness_score = 0.0
        if not has_alpha_cand and translated_text:
            at_left_boundary = candidate_pos == 0 or not (
                "\u4e00" <= translated_text[candidate_pos - 1] <= "\u9fff"
            )
            candidate_end = candidate_pos + len(candidate)
            at_right_boundary = candidate_end == len(translated_text) or not (
                "\u4e00" <= translated_text[candidate_end] <= "\u9fff"
            )
            if at_left_boundary and at_right_boundary:
                completeness_score = 1.0
            elif at_left_boundary or at_right_boundary:
                completeness_score = 0.5

        pos_diff = abs(candidate_pos - expected_pos)
        pos_score = 1.0 / (1.0 + pos_diff / 20.0)
        return len_score * 0.4 + completeness_score * 0.4 + pos_score * 0.2
