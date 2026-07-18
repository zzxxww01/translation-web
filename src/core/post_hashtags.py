"""Deterministic Xiaohongshu hashtag selection for translated posts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence


_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_\-\u3400-\u9fff]+)")
_TAG_SEPARATOR_RE = re.compile(r"^[\s,，、|｜·]*$")
_FORBIDDEN_GENERIC_TAGS = {
    "#科技",
    "#科技资讯",
    "#行业观察",
    "#产业趋势",
    "#热点观察",
}


@dataclass(frozen=True)
class _Topic:
    tag: str
    patterns: Sequence[re.Pattern[str]]


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


_TOPICS = (
    _Topic(
        "#半导体",
        _compile(
            r"semiconductor",
            r"半导体",
            r"foundry",
            r"晶圆",
            r"\bfab(?:s)?\b",
            r"\bTSMC\b",
            r"台积电",
            r"\bASML\b",
            r"\bEUV\b",
            r"光刻",
            r"制程",
        ),
    ),
    _Topic(
        "#ai",
        _compile(
            r"(?<![A-Za-z0-9])AI(?![A-Za-z0-9])",
            r"artificial intelligence",
            r"人工智能",
            r"machine learning",
            r"机器学习",
            r"deep learning",
            r"深度学习",
            r"生成式AI",
        ),
    ),
    _Topic(
        "#大模型",
        _compile(
            r"(?<![A-Za-z0-9])LLMs?(?![A-Za-z0-9])",
            r"large language model",
            r"foundation model",
            r"大模型",
            r"语言模型",
            r"(?<![A-Za-z0-9])GPT(?:-\d+)?(?![A-Za-z0-9])",
            r"ChatGPT",
            r"OpenAI",
            r"Claude",
            r"Gemini",
            r"Transformer",
            r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])",
            r"context window",
            r"上下文窗口",
        ),
    ),
    _Topic(
        "#英伟达",
        _compile(r"NVIDIA", r"英伟达", r"Jensen Huang", r"黄仁勋"),
    ),
    _Topic(
        "#芯片",
        _compile(
            r"(?<![A-Za-z0-9])chips?(?![A-Za-z0-9])",
            r"芯片",
            r"(?<![A-Za-z0-9])(?:GPU|CPU|NPU|TPU|ASIC|SoC|HBM)(?![A-Za-z0-9])",
            r"processor",
            r"accelerator",
            r"处理器",
            r"加速器",
        ),
    ),
    _Topic("#台积电", _compile(r"\bTSMC\b", r"台积电")),
    _Topic(
        "#算力",
        _compile(
            r"computing power",
            r"compute capacity",
            r"算力",
            r"GPU cluster",
            r"GPU集群",
            r"AI infrastructure",
        ),
    ),
    _Topic(
        "#科技股",
        _compile(
            r"科技股",
            r"earnings",
            r"财报",
            r"revenue",
            r"营收",
            r"market cap",
            r"市值",
            r"stock price",
            r"股价",
        ),
    ),
)

_SPECIFIC_TOPICS = (
    (
        "#英伟达",
        (_compile(r"NVIDIA", r"英伟达", r"Jensen Huang", r"黄仁勋"),),
    ),
    (
        "#台积电",
        (_compile(r"\bTSMC\b", r"台积电"),),
    ),
    (
        "#OpenAI",
        (_compile(r"OpenAI", r"ChatGPT", r"Codex"),),
    ),
    (
        "#Claude",
        (_compile(r"Anthropic", r"Claude"),),
    ),
    (
        "#Gemini",
        (_compile(r"Google Gemini", r"(?<![A-Za-z])Gemini(?![A-Za-z])"),),
    ),
    (
        "#AI芯片",
        (
            _compile(r"artificial intelligence", r"人工智能", r"(?<!\w)AI(?!\w)"),
            _compile(
                r"(?<!\w)chips?(?!\w)",
                r"芯片",
                r"(?<!\w)(?:GPU|NPU|TPU|ASIC)(?!\w)",
                r"accelerator",
                r"加速器",
            ),
        ),
    ),
    (
        "#大模型推理",
        (
            _compile(
                r"large language model",
                r"(?<!\w)LLMs?(?!\w)",
                r"大模型",
                r"语言模型",
            ),
            _compile(
                r"inference",
                r"serving",
                r"throughput",
                r"(?<!\w)tokens?(?!\w)",
                r"推理",
                r"吞吐",
            ),
        ),
    ),
    (
        "#先进制程",
        (
            _compile(
                r"(?<!\d)(?:1[024]|[2-7])\s*nm(?!\w)",
                r"先进制程",
                r"(?<!\w)EUV(?!\w)",
                r"光刻",
            ),
        ),
    ),
    (
        "#晶圆代工",
        (_compile(r"foundry", r"晶圆代工", r"晶圆厂"),),
    ),
    (
        "#HBM",
        (_compile(r"(?<!\w)HBM(?:[234]E?)?(?!\w)", r"高带宽内存"),),
    ),
    (
        "#GPU",
        (_compile(r"(?<!\w)GPUs?(?!\w)", r"图形处理器"),),
    ),
    (
        "#AI基础设施",
        (_compile(r"AI infrastructure", r"AI基础设施", r"GPU cluster", r"GPU集群"),),
    ),
)


def _deduplicate(tags: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = raw_tag if raw_tag.startswith("#") else f"#{raw_tag}"
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
    return result


def _tags_from_tag_only_line(line: str) -> list[str]:
    matches = list(_HASHTAG_RE.finditer(line))
    if not matches:
        return []
    remainder_parts: list[str] = []
    cursor = 0
    for match in matches:
        remainder_parts.append(line[cursor : match.start()])
        cursor = match.end()
    remainder_parts.append(line[cursor:])
    if not _TAG_SEPARATOR_RE.fullmatch("".join(remainder_parts)):
        return []
    return [f"#{match.group(1)}" for match in matches]


def select_xiaohongshu_hashtags(
    source_text: str,
    translated_text: str = "",
    *,
    maximum: int = 5,
) -> list[str]:
    """Choose only tags with a direct, deterministic content match."""

    haystack = f"{source_text or ''}\n{translated_text or ''}"
    specific = [
        tag
        for tag, required_groups in _SPECIFIC_TOPICS
        if all(
            any(pattern.search(haystack) for pattern in group)
            for group in required_groups
        )
    ]
    specific = _deduplicate(specific)
    if specific:
        return specific[:maximum]

    selected = [
        topic.tag
        for topic in _TOPICS
        if any(pattern.search(haystack) for pattern in topic.patterns)
    ]
    selected = _deduplicate(selected)
    return selected[:maximum]


def append_xiaohongshu_hashtags(text: str, source_text: str = "") -> str:
    """Ensure a translated post ends with one deduplicated hashtag line."""

    body = (text or "").rstrip()
    if not body:
        return body

    lines = body.splitlines()
    trailing_tags: list[str] = []
    trailing_tag_lines: list[list[str]] = []
    while lines:
        line_tags = _tags_from_tag_only_line(lines[-1])
        if not line_tags:
            break
        trailing_tag_lines.append(line_tags)
        lines.pop()
    if trailing_tag_lines:
        trailing_tags = [
            tag
            for line_tags in reversed(trailing_tag_lines)
            for tag in line_tags
        ]
        body = "\n".join(lines).rstrip()

    source_tag_keys = {
        f"#{match}".casefold()
        for match in _HASHTAG_RE.findall(source_text or "")
    }
    forbidden_keys = {tag.casefold() for tag in _FORBIDDEN_GENERIC_TAGS}
    trailing_tags = [
        tag
        for tag in trailing_tags
        if tag.casefold() not in forbidden_keys
        or tag.casefold() in source_tag_keys
    ]
    recommended = (
        []
        if trailing_tags
        else select_xiaohongshu_hashtags(source_text, body)
    )
    inline_tag_keys = {
        f"#{match}".casefold()
        for match in _HASHTAG_RE.findall(body)
    }
    primary_tags = _deduplicate([*trailing_tags, *recommended])
    tags = [
        tag
        for tag in primary_tags
        if tag.casefold() not in inline_tag_keys
    ]
    tags = tags[:5]
    if not tags:
        return body
    tag_line = " ".join(tags)
    return f"{body}\n\n{tag_line}" if body else tag_line
