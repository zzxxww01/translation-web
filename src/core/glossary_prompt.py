"""Helpers for selecting and rendering glossary entries before prompt injection."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

from .constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from .models import Glossary, GlossaryTerm, Section
from .models.enums import TranslationStrategy

DEFAULT_GLOSSARY_PROMPT_TITLE = "## 术语约束（仅列出当前文本命中的术语，必须优先遵守）"
# 短帖（社媒）专用标题：词表在这里只负责"用哪个中文写法"，不负责注释与篇幅——
# 那些由帖子提示词自己决定。沿用长文标题里的"必须优先遵守"会让词表的括注
# 要求压过帖子提示词"注释克制"的规则，一条 80 字的帖子被塞进四五个英文括注。
SHORT_FORM_GLOSSARY_PROMPT_TITLE = (
    "## 术语约束（仅统一用词写法，不改变下文的注释与篇幅规则）"
)
MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT = 48

# 词义栏里的括注部分（多为英文全称），取中文全称时先掐掉。
_CJK_ANNOTATION_PARENS = re.compile(r"[（(][^）)]*[)）]")
_CJK_CHAR_RE = re.compile(r"[一-鿿]")


@lru_cache(maxsize=4096)
def _term_word_pattern(normalized_term: str) -> "re.Pattern | None":
    """按规范化术语缓存已编译的词边界正则；CJK 等术语返回 None（改用 str.count）。

    逐段翻译会对全量术语反复调用本函数，缓存 fullmatch 判断 + re.escape + 编译，
    把每段 O(术语) 的重复编译开销降为一次。
    """
    if re.fullmatch(r"[a-z0-9 .,+\-/]+", normalized_term):
        return re.compile(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])")
    return None


def _count_term_occurrences(text: str, term: str) -> int:
    normalized_text = text.lower()
    normalized_term = term.lower().strip()
    if not normalized_term:
        return 0

    pattern = _term_word_pattern(normalized_term)
    if pattern is not None:
        return len(pattern.findall(normalized_text))

    return normalized_text.count(normalized_term)


def _normalize_whitespace(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _truncate_note(note: str, max_chars: int) -> str:
    normalized = _normalize_whitespace(note)
    if not normalized or max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _iter_prompt_terms(terms: Optional[Iterable[Any]]) -> Iterable[Any]:
    if isinstance(terms, dict):
        for original, translation in terms.items():
            yield {
                "original": original,
                "translation": translation,
                "strategy": "translate",
            }
        return

    for term in terms or []:
        yield term


def select_prompt_terms_for_text(
    terms: Optional[Iterable[Any]],
    source_text: Optional[str],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[Any]:
    """Select prompt terms whose originals are actually present in the source text."""
    if not terms or max_terms <= 0:
        return []

    normalized_source = _normalize_whitespace(source_text)
    candidates: List[tuple[int, int, int, Any]] = []
    fallback: List[Any] = []

    for index, term in enumerate(_iter_prompt_terms(terms)):
        payload = _normalize_prompt_term(term)
        if not payload:
            continue

        if not normalized_source:
            fallback.append(term)
            if len(fallback) >= max_terms:
                break
            continue

        occurrences = _count_term_occurrences(normalized_source, payload["original"])
        if occurrences <= 0:
            continue

        candidates.append((occurrences, len(payload["original"]), index, term))

    if not normalized_source:
        return fallback

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [term for _, _, _, term in candidates[:max_terms]]


def _normalize_prompt_term(term: Any) -> Optional[Dict[str, Any]]:
    if isinstance(term, dict):
        strategy = term.get("strategy", "")
        strategy_value = getattr(strategy, "value", strategy) or "translate"
        original = _normalize_whitespace(term.get("term") or term.get("original", ""))
        translation = _normalize_whitespace(term.get("translation"))
        note = _normalize_whitespace(term.get("context_meaning") or term.get("note"))
        first_occurrence_note = bool(term.get("first_occurrence_note", False))
    else:
        strategy_value = getattr(
            getattr(term, "strategy", None),
            "value",
            getattr(term, "strategy", ""),
        ) or "translate"
        original = _normalize_whitespace(
            getattr(term, "term", None) or getattr(term, "original", "")
        )
        translation = _normalize_whitespace(getattr(term, "translation", ""))
        note = _normalize_whitespace(
            getattr(term, "context_meaning", None) or getattr(term, "note", None)
        )
        first_occurrence_note = bool(getattr(term, "first_occurrence_note", False))

    if not original:
        return None
    if not translation and strategy_value != "preserve":
        return None

    return {
        "original": original,
        "translation": translation or original,
        "strategy": strategy_value,
        "note": note,
        "first_occurrence_note": first_occurrence_note,
    }


def _has_multiple_translation_candidates(translation: str) -> bool:
    """标准写法本身就是一串候选（如 ``良率(制造)/收益率(金融)``、``嵌入/向量化``）。

    只按 ``/``／``／`` 切分判断，不把括号单独当信号——``宽专家并行 (WideEP)``
    这类「中文名 + 英文缩写」条目是单义的，误判会削弱最强的术语约束。
    """
    parts = [part.strip() for part in re.split(r"[/／]", translation or "") if part.strip()]
    return len(parts) >= 2


def _note_maps_multiple_translations(translation: str, note: str) -> bool:
    """【词义】栏写了 ≥2 组「场景=写法」映射，且当前写法正是其中一项。

    如 memory 的 ``系统/DRAM=内存；NAND/盘存=存储；泛指器件=存储器``。
    ``die`` 的 ``与 chip=芯片 区分`` 里的 ``=`` 指向的是别的术语，不算多义。
    """
    targets = [
        segment.split("=", 1)[1].strip()
        for segment in re.split(r"[；;]", note or "")
        if "=" in segment
    ]
    targets = [target for target in targets if target]
    if len(targets) < 2 or not translation:
        return False
    return any(translation in target or target in translation for target in targets)


def _is_polysemous_translation(translation: str, note: str) -> bool:
    """判定词表条目是否为「多义术语」：写法多候选，或【词义】栏分场景映射。"""
    return _has_multiple_translation_candidates(
        translation
    ) or _note_maps_multiple_translations(translation, note)


def _build_requirement_text(
    *,
    original: str,
    translation: str,
    strategy: str,
    first_occurrence_note: bool = False,
    already_used: bool = False,
    note: str = "",
    short_form: bool = False,
) -> str:
    # 短帖模式：词表只约束"用哪个写法"，首现括注/已首现之类的长文规则一概不发。
    # 必须在所有 strategy 分支之前短路——already_used 分支说的"该术语已在前文
    # 完成首现括注"在没有前文的单条帖子里毫无意义。
    if short_form:
        if strategy == "preserve" or not translation or translation == original:
            # 「不加注释」会压过帖子提示词「缩写首现展开」的规则，让面向普通
            # 中文读者的短帖裸写 HBM/UBI 一类缩写。这里改为允许首现展开，但
            # 只在词义栏确实给出了中文全称时才给建议——词义栏也可能是纯英文
            # （CoWoS = "Chip on Wafer on Substrate"），照搬会写出英文全称括注。
            chinese_name = _CJK_ANNOTATION_PARENS.sub("", note or "").strip()
            if chinese_name and _CJK_CHAR_RE.search(chinese_name):
                return (
                    f"保留英文写法；若该缩写对普通中文读者不自明，首次出现可写"
                    f"“{chinese_name}（{original}）”，后文只写“{original}”"
                )
            return f"保留英文写法“{original}”，不要改写成其他中文译名"
        if _is_polysemous_translation(translation, note):
            return "多义词：按【词义】栏择一，禁止整串照抄"
        return f"直接使用该写法“{translation}”"

    if strategy == "preserve":
        return "保留英文原文，不加注释"

    if strategy == "preserve_annotate":
        if already_used:
            return (
                f"该术语已在前文完成首现注释，本段一律只写\u201c{original}\u201d，"
                "禁止再加任何括注"
            )
        if translation and translation != original:
            return f"首次出现写\u201c{original}（{translation}）\u201d，后文写\u201c{original}\u201d"
        return f"首次出现时加简短中文注释，后文继续写\u201c{original}\u201d"

    if strategy == "first_annotate" or first_occurrence_note:
        if already_used:
            return (
                f"该术语已在前文完成首现括注，本段一律只写\u201c{translation}\u201d，"
                "禁止再加括注或英文原名"
            )
        if translation != original:
            return f"首次出现写\u201c{translation}（{original}）\u201d，后文写\u201c{translation}\u201d"
        return f"首次出现时加简短注释，后文继续写\u201c{translation}\u201d"

    if _is_polysemous_translation(translation, note):
        return "多义词：按【词义】栏逐处判义后择一，禁止整串照抄，全篇不得一刀切"

    return "直接使用该写法"


def _render_glossary_prompt_line(
    term: Any,
    *,
    already_used: bool = False,
    max_note_chars: int = MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT,
    short_form: bool = False,
) -> str:
    payload = _normalize_prompt_term(term)
    if not payload:
        return ""

    requirement = _build_requirement_text(
        original=payload["original"],
        translation=payload["translation"],
        strategy=payload["strategy"],
        first_occurrence_note=payload["first_occurrence_note"],
        already_used=already_used,
        note=payload["note"],
        short_form=short_form,
    )
    # 写法本身是一串候选时不能自称「标准写法」，否则与提示词里的「强制采用」
    # 叠加会诱导模型整串照抄或直接取首项。
    is_candidate_list = requirement.startswith(
        "多义词"
    ) and _has_multiple_translation_candidates(payload["translation"])
    parts = [
        f"原文：{payload['original']}",
        f"{'候选写法' if is_candidate_list else '标准写法'}：{payload['translation']}",
        f"要求：{requirement}",
    ]

    note = _truncate_note(payload["note"], max_note_chars)
    if note:
        parts.append(f"词义：{note}")

    return "- " + "；".join(parts)


def select_glossary_terms_for_text(
    glossary: Optional[Glossary],
    source_text: Optional[str],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[GlossaryTerm]:
    """Select only active glossary terms that are relevant to the source text."""
    if glossary is None or not glossary.terms:
        return []

    active_terms = [
        term
        for term in glossary.terms
        if getattr(term, "status", "active") == "active"
    ]
    if not active_terms:
        return []

    if not source_text or not source_text.strip():
        return active_terms[:max_terms]

    # 使用 _count_term_occurrences（带边界匹配）作为统一标准筛选命中术语
    candidates: List[tuple[int, int, int, GlossaryTerm]] = []
    for index, term in enumerate(active_terms):
        occurrences = _count_term_occurrences(source_text, term.original)
        if occurrences > 0:
            candidates.append((occurrences, len(term.original), index, term))

    if not candidates:
        return []

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [term for _, _, _, term in candidates[:max_terms]]


def build_glossary_prompt_entries(
    glossary: Optional[Glossary],
    source_text: Optional[str],
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
) -> List[Dict[str, Any]]:
    """Convert selected glossary terms into the normalized prompt payload format."""
    return [
        {
            "original": term.original,
            "translation": term.translation,
            "strategy": term.strategy.value,
            "note": term.note,
        }
        for term in select_glossary_terms_for_text(glossary, source_text, max_terms)
    ]


def render_glossary_prompt_block(
    terms: Optional[Iterable[Any]],
    *,
    title: str = DEFAULT_GLOSSARY_PROMPT_TITLE,
    include_title: bool = True,
    max_terms: int = MAX_GLOSSARY_TERMS_IN_PROMPT,
    term_usage: Optional[Dict[str, List[str]]] = None,
    max_note_chars: int = MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT,
    empty_text: str = "",
    short_form: bool = False,
) -> str:
    """Render prompt-ready glossary constraints from term objects or dictionaries.

    ``short_form=True`` 供社媒短帖使用：只输出用词写法，不发首现括注一类的
    长文规则（详见 :func:`_build_requirement_text`）。
    """
    if not terms or max_terms <= 0:
        return empty_text

    used_keys = {
        _normalize_whitespace(key).lower()
        for key in (term_usage or {})
        if _normalize_whitespace(key)
    }

    lines: List[str] = []
    for term in _iter_prompt_terms(terms):
        payload = _normalize_prompt_term(term)
        if not payload:
            continue

        line = _render_glossary_prompt_line(
            payload,
            already_used=payload["original"].lower() in used_keys,
            max_note_chars=max_note_chars,
            short_form=short_form,
        )
        if not line:
            continue

        lines.append(line)
        if len(lines) >= max_terms:
            break

    if not lines:
        return empty_text

    if include_title:
        return "\n".join([title, *lines])
    return "\n".join(lines)


def build_term_usage_from_project(
    sections: List[Section],
    glossary: Glossary,
    current_section_id: str,
    current_paragraph_id: str,
) -> Dict[str, List[str]]:
    """Scan all translated paragraphs before the current one to build term usage.

    Only tracks terms with ``first_annotate`` or ``preserve_annotate`` strategy.
    Iterates sections in order and stops when reaching the current paragraph.
    For each paragraph that already has a translation, checks whether its
    source text contains any tracked terms.

    Returns a dict ``{term_original_lower: [translation]}`` compatible with
    :func:`render_glossary_prompt_block`'s *term_usage* parameter.
    """
    if not glossary or not glossary.terms:
        return {}

    # Collect terms that need first-occurrence tracking
    tracked: List[GlossaryTerm] = [
        t
        for t in glossary.terms
        if getattr(t, "status", "active") == "active"
        and t.strategy
        in (TranslationStrategy.FIRST_ANNOTATE, TranslationStrategy.PRESERVE_ANNOTATE)
    ]
    if not tracked:
        return {}

    usage: Dict[str, List[str]] = {}

    for section in sections:
        for para in section.paragraphs:
            # Stop when we reach the current paragraph
            if (
                section.section_id == current_section_id
                and para.id == current_paragraph_id
            ):
                return usage

            # Only consider paragraphs that have a translation
            translation = para.confirmed or (
                para.latest_translation_text(non_empty=True)
                if hasattr(para, "latest_translation_text")
                else None
            )
            if not translation:
                continue

            source = para.source or ""
            if not source:
                continue

            for term in tracked:
                key = term.original.lower()
                if key in usage:
                    continue  # already recorded
                if _count_term_occurrences(source, term.original) > 0:
                    usage[key] = [term.translation or term.original]

            # 所有 tracked 术语都已找到首次出现，后续段落不会改变结果，提前返回
            if len(usage) >= len(tracked):
                return usage

    return usage
