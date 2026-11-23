"""把 four-step-translate 产出的 zh.md 对齐到项目的段落上。

skill 自己从 HTML 转出 en.md，再逐块翻成 zh.md，两者块结构一致（它的 QA 门禁核对标题、链接、
图片数量）。所以分两步：zh 块按结构配对到 en 块；en 块再与项目原文（章节标题 + 段落）做单调对齐。
一个 en 块可以对多段（列表、被拆开的长段）；被拆开的长段按句末把中文切给各段（见 split_like）；
没对上任何段的块并进前一段，中文一个字都不丢。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import accumulate
from typing import Dict, List, Optional, Sequence, Tuple

# 覆盖率低于这个值不算对上：短段落（"Introduction"）也要大部分词都在块里出现
MIN_SCORE = 0.5
# 出现在超过这个比例的块里的词当作虚词，不参与打分
COMMON_TOKEN_RATIO = 0.3
# 标题对正文块（或正文对标题块）打八折。短标题的词往往全出现在紧跟着的那段正文里
# （"DeepSeek Open Source" 与「…DeepSeek's open source week…」），只看词会和标题块打平，
# 结果正文进了标题行、标题被并到上一段末尾、这一段空着（2026-10-29 华为与 DeepSeek 一文 3 处）。
KIND_MISMATCH = 0.8
# 覆盖率打平时看块里有多少是这段的词：短段（"Source: Meta"）对短块，不去抢下一段长正文
# （"Meta" 两边都有；抢了之后长段名下挂三段、拼不回原文、拆不开，后两段空着，2026-11-23 TPU 一文）。权重小到只用来破平局
PRECISION_WEIGHT = 0.01

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d+[.)])\s")
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]*\)\s*$")
_TOKEN = re.compile(r"[a-z0-9]+")
_NUMBER = re.compile(r"\d+")
# 仅对纯文本做启发式切分；格式化文本整段保留，避免切断 Markdown 或链接。
_MARKDOWN = re.compile(r"[\[\]*_`<>\\~|&]|https?://|www\.", re.IGNORECASE)
# 链接、加粗、斜体、行内代码：整体不切，但在它们外面的句末照样能切（2026-11-23：带一处链接或加粗的长段
# 原来整段不切，下一行显示缺译，文章进度停在 95%）。去掉这些之后还有别的标记（HTML、实体、转义、裸链接）就仍整段保留
_PROTECTED = re.compile(r"\[[^\]\n]*\]\([^)\s]*\)|\*\*[^\n]+?\*\*|__[^\n]+?__|`[^`\n]+`|\*[^*\n]+\*")
_MD_LINK = re.compile(r"\[([^\]\n]*)\]\([^)\s]*\)")
_MD_MARKS = re.compile(r"\*\*|__|[*`]")
# 句末后紧跟的收尾符号（引号、括号，以及加粗 / 代码的收尾标记）归前一句
_ZH_SENTENCE = re.compile(r".+?(?:[。！？!?]+[”’」』）)\"'*_`]*|$)", re.DOTALL)
_ZH_CLAUSE = re.compile(r".+?(?:[，；：;]+|(?<!\d),(?!\d)|$)", re.DOTALL)
_EN_SENTENCE = re.compile(r".+?(?:[.!?。！？]+(?=\s|$)|$)", re.DOTALL)


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


def _is_heading(kind: str) -> bool:
    """章节标题，或者 h1–h6（块和段落用同一套写法）"""
    return kind == "section" or bool(re.fullmatch(r"h[1-6]", kind))


def align_targets(blocks: Sequence[str], targets: Sequence[str],
                  block_kinds: Optional[Sequence[str]] = None,
                  target_kinds: Optional[Sequence[str]] = None) -> List[Optional[int]]:
    """单调对齐：每个目标对到一个块或不对（None），块序号随目标序号不减。O(块数 × 目标数)。
    给了块和目标的类型时，标题和正文互相对打八折（见 KIND_MISMATCH）。"""
    n, m = len(blocks), len(targets)
    if not n or not m:
        return [None] * m
    block_sets = [set(_tokens(b)) for b in blocks]
    doc_freq: Dict[str, int] = {}
    for tokens in block_sets:
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    limit = max(2, int(n * COMMON_TOKEN_RATIO))
    target_words, target_sets = [], []
    for target in targets:
        words = set(_tokens(target))
        target_sets.append(words)
        target_words.append([t for t in words if doc_freq.get(t, 0) <= limit] or list(words))

    kinds_known = block_kinds is not None and target_kinds is not None

    def score(j: int, i: int) -> float:
        words = target_words[j]
        if not words:
            return 0.0
        covered = sum(1 for t in words if t in block_sets[i]) / len(words)
        if kinds_known and _is_heading(target_kinds[j]) != _is_heading(block_kinds[i]):
            covered *= KIND_MISMATCH
        if covered < MIN_SCORE:
            return covered
        precision = len(target_sets[j] & block_sets[i]) / (len(block_sets[i]) or 1)
        return covered + PRECISION_WEIGHT * precision

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


def fill_gaps(mapping: List[Optional[int]], block_kinds: Sequence[str], target_kinds: Sequence[str]) -> int:
    """两个已对上的段落之间，没对上的段落和没用上的块一样多、标题正文也一一相符时，按顺序配上（原地改 mapping）。
    词对不上但位置确定的段：比如网页把署名折叠成「A, B, C, and 4 others」，en.md 照抄，原文却是完整名单。返回配上了几段。"""
    used = {b for b in mapping if b is not None}
    filled = 0
    j = 0
    while j < len(mapping):
        if mapping[j] is not None or target_kinds[j] == "image":
            j += 1
            continue
        start = j
        while j < len(mapping) and mapping[j] is None:
            j += 1
        before = next((mapping[k] for k in range(start - 1, -1, -1) if mapping[k] is not None), -1)
        after = mapping[j] if j < len(mapping) else len(block_kinds)
        gap_targets = [k for k in range(start, j) if target_kinds[k] != "image"]
        gap_blocks = [b for b in range(before + 1, after) if b not in used and block_kinds[b] != "image"]
        if (gap_targets and len(gap_targets) == len(gap_blocks)
                and all(_is_heading(target_kinds[t]) == _is_heading(block_kinds[b])
                        for t, b in zip(gap_targets, gap_blocks))):
            for t, b in zip(gap_targets, gap_blocks):
                mapping[t] = b
                used.add(b)
            filled += len(gap_targets)
    return filled


def _pieces(pattern: re.Pattern, text: str) -> List[str]:
    return [m.group(0) for m in pattern.finditer(text) if m.group(0).strip()]


def plain_markdown(text: str) -> str:
    """去掉链接、加粗、斜体、代码的标记，只留文字：和导入时从网页里取出的原文比。"""
    return _MD_MARKS.sub("", _MD_LINK.sub(r"\1", text))


def _units(text: str, pattern: re.Pattern) -> List[str]:
    units = [match.group(0) for match in pattern.finditer(text)]
    if len(units) > 1 and not units[-1].strip():
        trailing = units.pop()
        units[-1] += trailing
    # 切点落在链接、加粗等里面就不切：和后一句并起来
    spans = [m.span() for m in _PROTECTED.finditer(text)]
    if not spans:
        return units
    merged: List[str] = []
    current, pos = "", 0
    for unit in units:
        current += unit
        pos += len(unit)
        if not any(start < pos < end for start, end in spans):
            merged.append(current)
            current = ""
    if current:
        merged.append(current)
    return merged


def split_like(zh: str, sources: Sequence[str]) -> Optional[List[str]]:
    """一段中文切成 len(sources) 份，对应导入时按句拆开的几段原文。只在句末切（句子不够才退到逗号）：
    中文句数和英文相同就按每段的句数切，否则按英文各段的长度比例找最近的句末。
    链接、加粗、斜体、行内代码不会被切开；含别的标记（HTML、实体、转义、裸链接）或换行，
    或切不出这么多份时返回 None，由调用方整段保留。"""
    count = len(sources)
    if not count or not zh.strip():
        return None
    if count == 1:
        return [zh]
    if _MARKDOWN.search(_PROTECTED.sub("", zh)) or "\n" in zh or "\r" in zh:
        return None
    units = _units(zh, _ZH_SENTENCE)
    if len(units) < count:
        units = _units(zh, _ZH_CLAUSE)
    if len(units) < count:
        return None
    sentences = [len(_pieces(_EN_SENTENCE, source)) or 1 for source in sources]
    if sum(sentences) == len(units):
        sizes = sentences
    else:
        ends = list(accumulate(len(unit) for unit in units))
        source_ends = list(accumulate(len(source) for source in sources))
        total_en = source_ends[-1] or 1
        cuts: List[int] = []
        for i in range(1, count):
            want = ends[-1] * source_ends[i - 1] / total_en
            # 第 i 刀切在第 j 句之后：前面每份至少一句，后面也要留够句子
            options = range((cuts[-1] if cuts else 0) + 1, len(units) - (count - i) + 1)
            cuts.append(min(options, key=lambda j: abs(ends[j - 1] - want)))
        sizes = [b - a for a, b in zip([0, *cuts], [*cuts, len(units)])]
    parts: List[str] = []
    start = 0
    for size in sizes:
        parts.append("".join(units[start:start + size]))
        start += size
    return parts if all(part.strip() for part in parts) else None


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

    mapping = align_targets([b.text for b in en_blocks], [t.source for t in targets],
                            [b.kind for b in en_blocks], [t.kind for t in targets])
    gap_filled = fill_gaps(mapping, [b.kind for b in en_blocks], [t.kind for t in targets])
    groups: Dict[int, List[int]] = {}
    for target_index, block_index in enumerate(mapping):
        if block_index is not None:
            groups.setdefault(block_index, []).append(target_index)

    texts: Dict[int, List[str]] = {}
    split_failures = 0
    split_by_sentence = 0
    for block_index, members in groups.items():
        zh_text = "\n".join(zh_for_en.get(block_index, []))
        if not zh_text:
            continue
        if len(members) == 1:
            texts.setdefault(members[0], []).append(zh_text)
            continue
        lines = [line for line in zh_text.split("\n") if line.strip()]
        sources = [targets[m].source for m in members]
        # 单调匹配也可能把重复词的无关段落对到同一块；只有原文确实拼回整段时才分句。
        is_split_paragraph = (
            en_blocks[block_index].kind in {"p", "quote"}
            and all(targets[m].kind in {"p", "blockquote", "quote"} for m in members)
            and " ".join(plain_markdown(" ".join(sources)).split()) == " ".join(plain_markdown(en_blocks[block_index].text).split())
        )
        parts = split_like(lines[0], sources) if len(lines) == 1 and is_split_paragraph else None
        if len(lines) == len(members) and not _MARKDOWN.search(zh_text):
            for member, line in zip(members, lines):
                texts.setdefault(member, []).append(line)
        elif parts:
            # 导入时被拆开的长段：一段中文按句末分给各段
            split_by_sentence += 1
            for member, part in zip(members, parts):
                texts.setdefault(member, []).append(part)
        else:
            split_failures += 1
            # 整块交给类型相同的那一个（正文块不给标题行）
            heading_block = _is_heading(en_blocks[block_index].kind)
            same_kind = [m for m in members if _is_heading(targets[m].kind) == heading_block]
            texts.setdefault((same_kind or members)[0], []).append(zh_text)

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
        target = targets[target_index]
        text = "\n\n".join(parts)
        # 网页把「1. Models fail…」存成普通段落、编号留在原文里；parse_blocks 把中文的
        # 编号当列表标记剥掉了，这里补回（GDPx 篇 5 段靠人工补）
        number = _NUMBERED.match(target.source or "")
        if number and target.kind != "li" and not _NUMBERED.match(text):
            text = f"{number.group(1)} {text}"
        alignment.texts[target.key] = text
    alignment.stats = {
        "targets": len(targets),
        "aligned": sum(1 for target in targets if target.key in alignment.texts),
        "unaligned": sum(1 for target in targets if target.key not in alignment.texts and target.kind != "image"),
        "en_blocks": len(en_blocks),
        "zh_blocks": len(zh_blocks),
        "merged_blocks": orphan_blocks,
        "split_by_sentence": split_by_sentence,
        "split_failures": split_failures,
        "gap_filled": gap_filled,
    }
    return alignment
