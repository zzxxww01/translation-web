"""把 four-step-translate 产出的 zh.md 对齐到项目的段落上。

skill 自己从 HTML 转出 en.md，再逐块翻成 zh.md，两者块结构一致（它的 QA 门禁核对标题、链接、
图片数量）。所以分两步：zh 块按结构配对到 en 块；en 块再与项目原文（章节标题 + 段落）做单调对齐。
一个 en 块可以对多段（列表、被拆开的长段）；没对上任何段的块并进前一段，中文一个字都不丢。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence, Tuple

# 覆盖率低于这个值不算对上：短段落（"Introduction"）也要大部分词都在块里出现
MIN_SCORE = 0.5
# 出现在超过这个比例的块里的词当作虚词，不参与打分
COMMON_TOKEN_RATIO = 0.3

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]*\)\s*$")
_TOKEN = re.compile(r"[a-z0-9]+")
_NUMBER = re.compile(r"\d+")


@dataclass
class Block:
    kind: str  # h1..h6 / p / li / quote / table / image / code
    text: str  # 去掉了行首标记（# 、- 、> ）的正文

    @property
    def signature(self) -> Tuple[str, Tuple[str, ...]]:
        # 数字在翻译前后保持不变，和块类型一起区分结构相同的块
        kind = "h" if self.kind.startswith("h") else self.kind
        return kind, tuple(sorted(set(_NUMBER.findall(self.text.replace(",", "")))))


@dataclass
class Target:
    """项目里一个可接收译文的位置：章节标题或段落。"""

    key: str  # "section:<章节 id>" 或 "<章节 id>/<段落 id>"
    section_id: str
    source: str
    kind: str = "p"  # "section" / 段落的 element_type


@dataclass
class Alignment:
    title: Optional[str] = None
    texts: Dict[str, str] = field(default_factory=dict)  # target key -> 中文
    stats: Dict[str, int] = field(default_factory=dict)


def parse_blocks(markdown: str) -> List[Block]:
    blocks: List[Block] = []
    paragraph: List[str] = []
    lines = markdown.replace("\r\n", "\n").split("\n")

    def flush() -> None:
        if paragraph:
            blocks.append(Block("p", "\n".join(paragraph).strip()))
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            body = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            if i < len(lines):
                body.append(lines[i])
            blocks.append(Block("code", "\n".join(body)))
        elif not stripped:
            flush()
        elif (heading := _HEADING.match(stripped)):
            flush()
            blocks.append(Block(f"h{len(heading.group(1))}", heading.group(2).strip()))
        elif (item := _LIST_ITEM.match(line)):
            flush()
            text = [item.group(1).strip()]
            # 缩进的续行属于同一项
            while i + 1 < len(lines) and lines[i + 1].startswith(("  ", "\t")) and not _LIST_ITEM.match(lines[i + 1]):
                i += 1
                text.append(lines[i].strip())
            blocks.append(Block("li", " ".join(text)))
        elif stripped.startswith(">"):
            flush()
            quote = [stripped.lstrip(">").strip()]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                i += 1
                quote.append(lines[i].strip().lstrip(">").strip())
            blocks.append(Block("quote", "\n".join(quote).strip()))
        elif stripped.startswith("|"):
            flush()
            table = [stripped]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                i += 1
                table.append(lines[i].strip())
            blocks.append(Block("table", "\n".join(table)))
        elif _IMAGE_ONLY.match(stripped):
            flush()
            blocks.append(Block("image", stripped))
        else:
            paragraph.append(stripped)
        i += 1
    flush()
    return [block for block in blocks if block.text]


def pair_blocks(en: Sequence[Block], zh: Sequence[Block]) -> List[Tuple[int, List[int]]]:
    """返回 [(en 块序号, [zh 块序号…])]。块数相同直接按序；不同就按结构签名对齐，多出来的 zh 块并进前一个。"""
    if len(en) == len(zh):
        return [(i, [i]) for i in range(len(en))]
    pairs: Dict[int, List[int]] = {}
    matcher = SequenceMatcher(None, [b.signature for b in en], [b.signature for b in zh], autojunk=False)
    last_en = None
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            target = last_en if last_en is not None else 0
            pairs.setdefault(target, []).extend(range(j1, j2))
            continue
        if tag == "delete":
            continue
        span = min(i2 - i1, j2 - j1)
        for k in range(span):
            pairs.setdefault(i1 + k, []).append(j1 + k)
            last_en = i1 + k
        if j2 - j1 > span:  # zh 多出来的并进这一段的最后一块
            pairs.setdefault(last_en if last_en is not None else i1, []).extend(range(j1 + span, j2))
    return sorted(pairs.items())


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def align_targets(blocks: Sequence[str], targets: Sequence[str]) -> List[Optional[int]]:
    """单调对齐：每个目标对到一个块或不对（None），块序号随目标序号不减。O(块数 × 目标数)。"""
    n, m = len(blocks), len(targets)
    if not n or not m:
        return [None] * m
    block_sets = [set(_tokens(b)) for b in blocks]
    doc_freq: Dict[str, int] = {}
    for tokens in block_sets:
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    limit = max(2, int(n * COMMON_TOKEN_RATIO))
    target_words = []
    for target in targets:
        words = set(_tokens(target))
        target_words.append([t for t in words if doc_freq.get(t, 0) <= limit] or list(words))

    def score(j: int, i: int) -> float:
        words = target_words[j]
        if not words:
            return 0.0
        return sum(1 for t in words if t in block_sets[i]) / len(words)

    neg = float("-inf")
    # best[j][i]：前 j 个目标、所用块都 ≤ i 时的最高分；choice 记回溯
    best = [[0.0] * n for _ in range(m + 1)]
    choice: List[List[int]] = [[0] * n for _ in range(m + 1)]  # 0=沿用 i-1，1=目标 j-1 对到 i，2=目标 j-1 不对
    for j in range(1, m + 1):
        for i in range(n):
            options = [(best[j][i - 1] if i else neg, 0), (best[j - 1][i], 2)]
            s = score(j - 1, i)
            if s >= MIN_SCORE:
                options.append((best[j - 1][i] + s, 1))
            value, how = max(options, key=lambda item: (item[0], item[1] == 1))
            best[j][i], choice[j][i] = value, how
    result: List[Optional[int]] = [None] * m
    j, i = m, n - 1
    while j > 0 and i >= 0:
        how = choice[j][i]
        if how == 0:
            i -= 1
        else:
            if how == 1:
                result[j - 1] = i
            j -= 1
    return result


def align_claude_translation(en_markdown: str, zh_markdown: str, targets: Sequence[Target]) -> Alignment:
    en_blocks, zh_blocks = parse_blocks(en_markdown), parse_blocks(zh_markdown)
    alignment = Alignment()
    # 第一块一级标题是文章标题，项目里不是段落
    if en_blocks and en_blocks[0].kind == "h1" and zh_blocks and zh_blocks[0].kind == "h1":
        alignment.title = zh_blocks[0].text
        en_blocks, zh_blocks = en_blocks[1:], zh_blocks[1:]

    zh_for_en: Dict[int, List[str]] = {}
    for en_index, zh_indexes in pair_blocks(en_blocks, zh_blocks):
        zh_for_en[en_index] = [zh_blocks[k].text for k in zh_indexes]

    mapping = align_targets([b.text for b in en_blocks], [t.source for t in targets])
    groups: Dict[int, List[int]] = {}
    for target_index, block_index in enumerate(mapping):
        if block_index is not None:
            groups.setdefault(block_index, []).append(target_index)

    texts: Dict[int, List[str]] = {}
    split_failures = 0
    for block_index, members in groups.items():
        zh_text = "\n".join(zh_for_en.get(block_index, []))
        if not zh_text:
            continue
        if len(members) == 1:
            texts.setdefault(members[0], []).append(zh_text)
            continue
        lines = [line for line in zh_text.split("\n") if line.strip()]
        if len(lines) == len(members):
            for member, line in zip(members, lines):
                texts.setdefault(member, []).append(line)
        else:
            split_failures += 1
            texts.setdefault(members[0], []).append(zh_text)

    # 没对上任何目标的块：并进前一个已对齐的目标（开头的并进后一个）
    orphan_blocks = 0
    mapped_blocks = sorted(groups)
    for block_index, zh_list in zh_for_en.items():
        if block_index in groups or not zh_list or not mapped_blocks:
            continue
        orphan_blocks += 1
        before = [b for b in mapped_blocks if b < block_index]
        if before:
            host = groups[before[-1]][-1]
            texts.setdefault(host, []).append("\n".join(zh_list))
        else:
            host = groups[mapped_blocks[0]][0]
            texts.setdefault(host, []).insert(0, "\n".join(zh_list))

    for target_index, parts in texts.items():
        alignment.texts[targets[target_index].key] = "\n\n".join(parts)
    alignment.stats = {
        "targets": len(targets),
        "aligned": sum(1 for target in targets if target.key in alignment.texts),
        "unaligned": sum(1 for target in targets if target.key not in alignment.texts and target.kind != "image"),
        "en_blocks": len(en_blocks),
        "zh_blocks": len(zh_blocks),
        "merged_blocks": orphan_blocks,
        "split_failures": split_failures,
    }
    return alignment
