"""Markdown safety post-processor for translated content.

Escapes special characters that interfere with markdown rendering
(e.g., bare `$` triggering MathJax, `<` being interpreted as HTML)
while preserving intentional markdown syntax and embedded images/links.
"""

from __future__ import annotations

import re
from typing import List, Optional

from src.settings import settings

from .protected_terms import desinicize_token, source_mentions_token


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Fenced code blocks (``` ... ```) — content inside must NOT be touched.
_FENCED_CODE_BLOCK = re.compile(
    r"^(?P<fence>`{3,}|~{3,}).*?\n(?P<body>.*?)^(?P=fence)\s*$",
    re.MULTILINE | re.DOTALL,
)

# LaTeX display math blocks: \[...\] or $$...$$
_LATEX_DISPLAY_MATH = re.compile(
    r"(\\\[.*?\\\]|\$\$.*?\$\$)",
    re.DOTALL,
)

# LaTeX inline math: \(...\) or $...$
#
# `$` 定界符采用 Pandoc 的判定规则，否则同一行出现两个货币金额时，中间整段
# 正文会被当成一个行内公式：`价格区间是 $100 到 $200。` → `$100 到 $200` 被
# 识别为公式，既跳过了全部后处理，渲染时还会被 MathJax/KaTeX 吃成数学斜体。
# 仓库现存源文里有 85 行同时含两个以上 `$数字`。三条约束：
#   1. 开定界符后不能是空白（`$ x$` 不是公式）；
#   2. 闭定界符前不能是空白；
#   3. 闭定界符后不能紧跟数字——这一条正是货币与公式的分水岭。
# 真公式 `$x > 0$ 时` 仍然命中（闭定界符后是空格）。
_LATEX_INLINE_MATH = re.compile(
    r"(\\\(.*?\\\)|\$(?![\s$])[^\$\n]*[^\s$]\$(?![\d$]))"
)

# Markdown escaping that is harmful inside LaTeX math.
_LATEX_ESCAPED_SUBSCRIPT = re.compile(r"\\_")
_LATEX_ESCAPED_STAR_ENV = re.compile(r"(\\(?:begin|end)\{[^{}\n]*?)\\\*([^{}\n]*\})")

# 翻译环节偶尔把公式里的反斜杠输出成 `\backslash `，于是 `\mathbf{q}_l` 变成
# `\backslash mathbf{q}\backslash _l`，渲染出来就是字面的 `\mathbfq\_l`。
# `\backslash` 本身是合法命令（集合差），所以只认这两种不合法的位置：后面跟
# 空白+字母（那位置只能是命令名），或紧跟 `_` `^`（集合差不可能这么用）。
_LATEX_BACKSLASH_ARTIFACT = re.compile(r"\\backslash(?:\s+(?=[A-Za-z])|\s*(?=[_^]))")
# 紧跟 `_` `^` 的形态没有任何合法解释，出现一次就足以判定被污染。
_LATEX_BACKSLASH_CERTAIN = re.compile(r"\\backslash\s*[_^]")

# Indented code blocks (lines starting with 4 spaces or a tab) — content must
# NOT be escaped. A run of consecutive indented lines is protected as one block.
_INDENTED_CODE_BLOCK = re.compile(r"(?:^(?: {4}|\t).*(?:\n|$))+", re.MULTILINE)

# Table rows (lines starting with optional whitespace then `|`). Cell contents
# (which may legitimately contain `$`, `<`, `>`) must NOT be escaped.
_TABLE_ROW = re.compile(r"^[ \t]*\|.*$", re.MULTILINE)

# Inline code spans (`...`) — must NOT be touched.
_INLINE_CODE = re.compile(r"`[^`]+`")

# Markdown images: ![alt](url) or ![alt](url "title").
# URL may contain one level of nested parens, e.g. .../wiki/Foo_(bar).
_PAREN_URL = r"\([^()]*(?:\([^()]*\)[^()]*)*\)"
_MD_IMAGE = re.compile(r"!\[[^\]]*\]" + _PAREN_URL)

# Markdown links: [text](url) or [text](url "title").
_MD_LINK = re.compile(r"\[[^\]]*\]" + _PAREN_URL)

# 模型或 inline 兜底偶尔会把一个已经完整的 Markdown 链接再套一层
# ``[[...]]``，甚至再追加第二个 URL：
# ``[[[ROCm.ai](inner)]](outer)``。这不是合法 Markdown，也是 QA 的
# link_collapse 阻断项。收尾层保留内层完整链接（它通常来自源文恢复），并
# 只剥掉多余外壳；普通 Obsidian ``[[Page]]`` 不在这些模式内，不会被改动。
_WIKI_LINK_WITH_OUTER_TARGET = re.compile(
    r"\[\[(?P<link>\[[^\]\n]*\]" + _PAREN_URL + r")\]\]" + _PAREN_URL
)
_WIKI_WRAPPED_MD_LINK = re.compile(
    r"\[\[(?P<link>\[[^\]\n]*\]" + _PAREN_URL + r")\]\]"
)
_DOUBLE_BRACKET_LINK_LABEL = re.compile(
    r"\[\[(?P<label>[^\[\]\n]+)\]\](?P<target>" + _PAREN_URL + r")"
)

# HTML tags (including self-closing) — preserve as-is.
# 收紧匹配，避免把散文里的 `<x and y>`（如 "5 < x and y > 3"）误判为标签而被保护，
# 这类应当作普通文本转义。只识别：无属性标签（<div> </p> <br/>）或含 `=` 属性的标签。
_HTML_TAG = re.compile(
    r"</?[a-zA-Z][a-zA-Z0-9]*\s*/?>"
    r"|<[a-zA-Z][a-zA-Z0-9]*\s+[^<>]*=[^<>]*>"
)

# HTML comments <!-- ... -->
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# Bare `$` that would trigger MathJax/KaTeX rendering.
# We escape standalone `$` but NOT already-escaped `\$`.
# Also skip `$$` pairs which are intentional math blocks.
_BARE_DOLLAR = re.compile(r"(?<!\\)(?<![$])[$](?![$])")

# Bare `<` that is NOT part of an HTML tag or comment.
# Lookahead checks it's not followed by a tag-name pattern or `!--`.
_BARE_LT = re.compile(r"<(?![a-zA-Z/!])")

# Bare `>` mid-line that is NOT a blockquote. Exclude common safe sequences so we
# don't mangle prose arrows/comparisons (a -> b, x => y, n >= m). `<` is already
# escaped and real HTML tags are protected, so these standalone `>` need no escaping.
_MID_LINE_GT = re.compile(r"(?<=[^\s\-=>])>(?![=>])")

# Pipe characters `|` outside of markdown tables can occasionally cause issues.
# We only escape pipes that appear inside normal text paragraphs,
# not in table rows (lines starting with `|`).
_BARE_PIPE_LINE = re.compile(r"^(?!\s*\|)(.+\|.+)$", re.MULTILINE)

# Consecutive blank lines (more than 2) — normalise to exactly 2.
_EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")

# CJK–Latin spacing: missing space between CJK and ASCII letter/digit.
# \u5b57\u7b26\u7c7b\u4e0d\u80fd\u53ea\u6709 [A-Za-z0-9]\uff1a\u6280\u672f\u6587\u91cc\u7d27\u8d34\u4e2d\u6587\u7684\u5f80\u5f80\u662f**\u7b26\u53f7\u578b\u8bcd\u5c3e**\u2014\u2014\u767e\u5206\u53f7\u3001
# \u4e0a\u6807\u5e73\u65b9\u3001\u4e58\u53f7\u3001\u6b27\u59c6\u3001\u5ea6\u3002\u5b9e\u6d4b\u6f0f\u7f51:\u300c45%\u7684\u4ea7\u80fd\u300d\u300c858mm\u00b2\u964d\u81f3\u300d\u300c2\u00d7\u5de6\u53f3\u300d
# \u300c50\u03a9\u7684\u8d70\u7ebf\u300d\u5168\u90fd\u4e0d\u8865\u7a7a\u683c\uff0c\u800c\u300c105\u00b0C \u7684\u7ed3\u6e29\u300d\u56e0\u4e3a\u7ed3\u5c3e\u6070\u597d\u662f\u5b57\u6bcd C \u53cd\u800c\u8865\u4e0a\u4e86\uff0c
# \u540c\u4e00\u7bc7\u91cc\u4e24\u79cd\u98ce\u683c\u5e76\u5b58\u3002
_LATIN_UNIT_TAIL = "A-Za-z0-9%\u00b0\u00b1\u00b2\u00b3\u00d7\u03a9\u00b5\u2030"
_CJK_LATIN_NO_SPACE = re.compile(
    r"([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff])"
    rf"([{_LATIN_UNIT_TAIL}])"
)
_LATIN_CJK_NO_SPACE = re.compile(
    rf"([{_LATIN_UNIT_TAIL}])"
    r"([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff])"
)

# ---------------------------------------------------------------------------
# CJK punctuation normalisation (\u5206\u5757\u62fc\u63a5\u540e\u7684\u5168/\u534a\u89d2\u6f02\u79fb\u6536\u5c3e)
# ---------------------------------------------------------------------------

_CJK_CLASS = r"\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"

_HALF_TO_FULL_PUNCT = {",": "\uff0c", ";": "\uff1b", ":": "\uff1a", "!": "\uff01", "?": "\uff1f"}

# Halfwidth punctuation stranded in Chinese context: preceded by a CJK char and
# followed by CJK/Latin/digit/space/closing marks or end-of-line. One trailing
# ASCII space is consumed because fullwidth punctuation carries its own spacing.
_CJK_HALFWIDTH_PUNCT = re.compile(
    rf"(?<=[{_CJK_CLASS}])([,;:!?])[ \t]?"
    rf"(?=[{_CJK_CLASS}A-Za-z0-9\s\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300c\u300d\u300e\u300f]|$)",
    re.MULTILINE,
)

# Halfwidth parentheses whose content contains CJK, or that directly follow a
# CJK char (annotation style: \u82f1\u4f1f\u8fbe(NVIDIA) \u2192 \u82f1\u4f1f\u8fbe\uff08NVIDIA\uff09).
_PAREN_CJK_INNER = re.compile(
    rf"\(([^()\n]*[{_CJK_CLASS}][^()\n]*)\)"
)
_PAREN_AFTER_CJK = re.compile(
    rf"(?<=[{_CJK_CLASS}])\(([^()\n]*)\)"
)
# \u4e0a\u9762\u4e24\u6761\u6f0f\u6389\u4e86\u6700\u5e38\u89c1\u7684\u62ec\u6ce8\u5f62\u6001\uff1a\u300c\u4e2d\u6587 + \u534a\u89d2\u7a7a\u683c + (\u7eaf\u82f1\u6587)\u300d\u2014\u2014
# \u201c\u5e74\u5ea6\u7ecf\u5e38\u6027\u6536\u5165 (ARR)\u201d \u56e0\u62ec\u53f7\u524d\u662f\u7a7a\u683c\u800c\u4e0d\u662f CJK\u3001\u5185\u5bb9\u53c8\u4e0d\u542b CJK\uff0c
# \u4e24\u6761\u90fd\u4e0d\u547d\u4e2d\uff0c\u4e8e\u662f\u540c\u4e00\u7bc7\u91cc\u4f1a\u540c\u65f6\u5b58\u5728\uff08capex\uff09\u4e0e (ARR)\u3002\u9650\u5b9a\u201c\u7d27\u8ddf\u5728 CJK
# \u540e\u7684\u5355\u4e2a\u7a7a\u683c\u201d\uff0c\u907f\u5f00\u51fd\u6570\u8c03\u7528 foo(bar) \u4e0e\u7eaf\u82f1\u6587\u53e5 appendix (Figure 3)\u3002
_PAREN_AFTER_CJK_SPACE = re.compile(
    rf"(?<=[{_CJK_CLASS}])[ ]\(([^()\n]{{1,60}})\)"
)

# \u5168\u89d2\u62ec\u53f7\u81ea\u5e26\u89c6\u89c9\u95f4\u8ddd\uff0c\u4e24\u4fa7\u4e0d\u5e94\u518d\u6302\u534a\u89d2\u7a7a\u683c\uff08\u8f6c\u5168\u89d2\u540e\u7684\u201cIDE \uff08\u96c6\u6210
# \u5f00\u53d1\u73af\u5883\uff09 \u6216\u201d\uff09\u3002\u53ea\u5728\u7a7a\u683c\u53e6\u4e00\u4fa7\u662f CJK/\u5b57\u6bcd/\u6570\u5b57\u65f6\u624d\u5220\uff0c\u4ee5\u514d\u52a8\u5230
# \u5217\u8868\u6807\u8bb0\u3001\u5f15\u7528\u524d\u7f00\u3001\u6807\u9898\u4e95\u53f7\u540e\u7684\u90a3\u4e2a\u5fc5\u9700\u7a7a\u683c\u3002
_SPACE_BEFORE_FULLWIDTH_PAREN = re.compile(
    rf"(?<=[{_CJK_CLASS}A-Za-z0-9])[ \t]+\uff08"
)
_SPACE_AFTER_FULLWIDTH_PAREN = re.compile(
    rf"\uff09[ \t]+(?=[{_CJK_CLASS}A-Za-z0-9])"
)

# Thousands separators inside numbers followed by a Chinese magnitude word:
# 2,600 \u4e07 \u2192 2600 \u4e07 (the comma reads as a decimal-scale error in Chinese).
_THOUSANDS_BEFORE_CJK_MAGNITUDE = re.compile(
    r"(\d),(?=\d{3}(?:,\d{3})*\s*[\u4e07\u4ebf])"
)

# Doubled fullwidth punctuation left behind by chunk stitching (\uff1a\uff1a \u3002\u3002 \uff0c\uff0c).
_DOUBLED_FULLWIDTH_PUNCT = re.compile(r"([\uff0c\u3002\uff1a\uff1b\u3001])\1+")

# Escape residue that is never meaningful in markdown prose (`\@`, `\&`).
_USELESS_ESCAPES = re.compile(r"\\([@&])")

# Standalone capitalized Token/Tokens。词边界本就放过 Tokenomics /
# TokenBudgeting 这类无空格复合词；`(?!\s+[A-Z])` 再放过带空格的英文专名
# （Token Ring / Token Factory / Token Economics），句首/标题首由 sub 回调
# 里的 _at_sentence_start 判断保留大写。剩下的 AI 语境 token 按 house style
# 一律小写。
_CAPITALIZED_TOKEN_WORD = re.compile(r"\bToken(s)?\b(?!\s+[A-Z])")

# 行首 / 标题标记后 / 句末标点后 —— 这些位置的大写 Token 是正常英文书写，
# 不做小写化。
_SENTENCE_START_BEFORE = re.compile(r"(?:^|\n)[ \t]*(?:#{1,6}[ \t]+|[-*+][ \t]+|>[ \t]*)?$")
_SENTENCE_END_BEFORE = re.compile(r"[.!?][\"')\]]?\s+$")

# `\u4e2d\u6587\uff08English\uff09` first-occurrence annotation. Used to strip exact repeated
# annotations for the same English term (annotation stacking, 2026-07 audit).
_CJK_EN_ANNOTATION = re.compile(
    rf"(?<=[{_CJK_CLASS}])\uff08\s*([A-Za-z][A-Za-z0-9 .&'/+-]{{0,60}}?)\s*\uff09"
)

# \u8bd1\u8005\u81ea\u52a0\u7684**\u4e2d\u6587\u91ca\u4e49**\u62ec\u6ce8\uff1a\u300c\u667a\u80fd\u4f53\uff08\u6307\u80fd\u591f\u81ea\u4e3b\u89c4\u5212\u5e76\u6267\u884c\u590d\u6742\u4efb\u52a1\u7684 AI\uff09\u300d\u3002
# \u4e0a\u9762\u90a3\u6761\u53ea\u8ba4\u62ec\u6ce8\u5185\u5bb9\u662f\u82f1\u6587\u539f\u8bcd\u7684\u5f62\u6001\uff0c\u6240\u4ee5\u8fd9\u7c7b\u4e2d\u6587\u91ca\u4e49\u53ef\u4ee5\u65e0\u9650\u91cd\u590d\u2014\u2014
# \u5b9e\u6d4b\u67d0\u7bc7\u6210\u54c1\u91cc\u540c\u4e00\u6761\u91ca\u4e49\u51fa\u73b0\u4e86 11 \u6b21\u3002\u4ee5\u300c\u6307/\u5373/\u610f\u4e3a/\u8bd1\u6ce8/\u5168\u79f0\u2026\u300d\u8fd9\u7c7b
# \u91ca\u4e49\u5f15\u5bfc\u8bcd\u5f00\u5934\u662f\u5224\u5b9a\u4f9d\u636e\uff1a\u82f1\u6587\u539f\u6587\u4e0d\u53ef\u80fd\u4ea7\u51fa\u4e2d\u6587\u91ca\u4e49\uff0c\u56e0\u6b64\u8fd9\u7c7b\u62ec\u6ce8\u4e00\u5b9a
# \u662f\u8bd1\u8005\u6dfb\u52a0\u7684\uff0c\u53bb\u91cd\u4e0d\u4f1a\u635f\u4f24\u539f\u6587\u4fe1\u606f\u3002
_CJK_GLOSS_ANNOTATION = re.compile(
    rf"(?<=[{_CJK_CLASS}])\uff08\s*"
    r"(?:\u6307|\u5373|\u610f\u4e3a|\u4ea6\u5373|\u4ea6\u79f0|\u53c8\u79f0|\u5168\u79f0|\u7b80\u79f0|\u7f29\u5199\u4e3a|\u8bd1\u6ce8|\u8bd1\u8005\u6ce8)"
    r"[^\uff08\uff09\n]{0,80}\uff09"
)

_CJK_SINGLE = re.compile(rf"[{_CJK_CLASS}]")


def _normalize_cjk_punctuation(text: str) -> str:
    """Normalise halfwidth punctuation drift inside Chinese prose.

    Operates on placeholder-protected text, so code, URLs, links, tables and
    LaTeX are never touched.
    """
    text = _CJK_HALFWIDTH_PUNCT.sub(
        lambda m: _HALF_TO_FULL_PUNCT[m.group(1)], text
    )
    text = _PAREN_CJK_INNER.sub("\uff08\\1\uff09", text)
    text = _PAREN_AFTER_CJK.sub("\uff08\\1\uff09", text)
    text = _PAREN_AFTER_CJK_SPACE.sub("\uff08\\1\uff09", text)
    text = _SPACE_BEFORE_FULLWIDTH_PAREN.sub("\uff08", text)
    text = _SPACE_AFTER_FULLWIDTH_PAREN.sub("\uff09", text)
    text = _THOUSANDS_BEFORE_CJK_MAGNITUDE.sub(r"\1", text)
    text = _DOUBLED_FULLWIDTH_PUNCT.sub(r"\1", text)
    return text


def _pair_quotes_in_line(line: str) -> str:
    """Normalise double quotes line by line to the review house style.

    Target style (2026-07 \u5ba1\u6821\u6807\u51c6): English straight double quotes ``"``,
    with one halfwidth space wherever a quote touches a CJK character on its
    outside. Fullwidth/curly quotes (\u201c \u201d) are flattened to straight quotes
    first \u2014 direction is irrelevant for straight quotes, so single-direction
    model output no longer needs repair. Lines with an odd straight-quote
    count get the conversion but no spacing pass (QA flags them).
    """
    line = line.replace("\u201c", '"').replace("\u201d", '"')

    count = line.count('"')
    if not count or count % 2:
        return line

    parts: List[str] = []
    open_next = True
    for index, ch in enumerate(line):
        if ch != '"':
            parts.append(ch)
            continue
        if open_next:
            if parts and _CJK_SINGLE.match(parts[-1]):
                parts.append(" ")
            parts.append('"')
        else:
            parts.append('"')
            next_char = line[index + 1] if index + 1 < len(line) else ""
            if next_char and _CJK_SINGLE.match(next_char):
                parts.append(" ")
        open_next = not open_next
    return "".join(parts)


def _repair_quotes(text: str) -> str:
    return "\n".join(_pair_quotes_in_line(line) for line in text.split("\n"))


def _dedupe_repeated_annotations(text: str) -> str:
    """Drop the 2nd+ exact repeat of a translator-added annotation.

    Two shapes are handled, both keyed on the annotation's own content so an
    annotation only survives at its first occurrence:

    * ``中文（English）`` — the English term itself (annotation stacking, A-11).
    * ``中文（指……）`` — a Chinese gloss the translator added. The prompt caps
      每个词全篇至多括注一次, but that instruction is not reliably followed:
      一篇成品实测出现同一条释义 11 次。这里做确定性兜底。

    Operates on placeholder-protected text so links/code/tables are never
    touched.
    """
    seen_en: set = set()

    def _replace_en(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in seen_en:
            return ""
        seen_en.add(key)
        return match.group(0)

    text = _CJK_EN_ANNOTATION.sub(_replace_en, text)

    seen_gloss: set = set()

    def _replace_gloss(match: re.Match[str]) -> str:
        key = match.group(0).strip()
        if key in seen_gloss:
            return ""
        seen_gloss.add(key)
        return match.group(0)

    return _CJK_GLOSS_ANNOTATION.sub(_replace_gloss, text)


def _repair_collapsed_markdown_links(text: str) -> str:
    """Remove redundant ``[[...]]`` shells around Markdown links.

    The inner link wins when two targets are present because it is the link
    reconstructed from the source inline element; the outer target is typically
    model-authored duplication. The transformation is deliberately narrow and
    idempotent.
    """
    text = _WIKI_LINK_WITH_OUTER_TARGET.sub(lambda match: match.group("link"), text)
    text = _WIKI_WRAPPED_MD_LINK.sub(lambda match: match.group("link"), text)
    return _DOUBLE_BRACKET_LINK_LABEL.sub(
        lambda match: f'[{match.group("label")}]{match.group("target")}',
        text,
    )


def normalize_cjk_ascii_spacing(text: str) -> str:
    """Insert missing halfwidth spaces between CJK and ASCII letters/digits.

    Shared by the markdown pipeline (phase 2e) and export title/filename
    normalisation (A-14: `meta.title_translation` used to skip this pass).
    """
    if not text:
        return text
    text = _CJK_LATIN_NO_SPACE.sub(r"\1 \2", text)
    text = _LATIN_CJK_NO_SPACE.sub(r"\1 \2", text)
    return text


# ---------------------------------------------------------------------------
# Core processor
# ---------------------------------------------------------------------------

def _desinicize_in_protected(text: str) -> str:
    """保护区（链接锚文本 / 表格单元）内的 token 去汉化。

    保护区跑不到 2e 的 CJK–ASCII 补空格，所以只对**确实发生了替换**的文本
    就地补一次空格；没有 token 汉化的内容一个字符都不动。
    """
    replaced = desinicize_token(text)
    if replaced == text:
        return text
    return normalize_cjk_ascii_spacing(replaced)


def _at_sentence_start(text: str, index: int) -> bool:
    """``index`` 处是否位于行首、标题/列表标记之后，或上一句句末之后。"""
    before = text[:index]
    return bool(
        _SENTENCE_START_BEFORE.search(before) or _SENTENCE_END_BEFORE.search(before)
    )


def postprocess_markdown(
    content: str,
    *,
    source: Optional[str] = None,
    latex_obsidian_normalize: Optional[bool] = None,
) -> str:
    """Apply all markdown-safety transformations to *content*.

    The function is idempotent — running it twice produces the same output.

    Transformations applied:
    1. Escape bare ``$`` signs (prevents accidental MathJax).
    2. Escape bare ``<`` (prevents accidental HTML interpretation).
    3. Normalise excessive blank lines.
    4. Inject CJK–Latin spacing where missing.
    5. Preserve LaTeX formulas, code blocks, inline code, images, links, and HTML tags.

    ``source`` 是对应的英文原文；给出时，token 去汉化（词元/令牌/代币 →
    token）只在原文确实出现 ``token`` 一词时才执行——否则译文里的「访问
    令牌」「代币」是正确译法，不得改写。``None``（默认）保持无条件改写，
    以免破坏拿不到原文的既有调用。

    ``latex_obsidian_normalize`` controls the Obsidian-oriented LaTeX delimiter
    rewrite (``\\( \\)`` → ``$ $``, ``\\[ \\]`` → ``$$``). Default (None) reads
    ``settings.latex_obsidian_normalize`` which is **off** — the exported file
    keeps the source delimiters verbatim (A-15, 与 en.md 保真).
    """
    if not content:
        return content

    should_desinicize = source is None or source_mentions_token(source)

    if latex_obsidian_normalize is None:
        latex_obsidian_normalize = getattr(
            settings, "latex_obsidian_normalize", False
        )

    # --- Phase 1: Extract protected regions to placeholders ---
    protected: List[str] = []

    def _protect_text(text: str) -> str:
        idx = len(protected)
        protected.append(text)
        return f"\x00PROTECTED_{idx}\x00"

    def _protect(match: re.Match[str]) -> str:
        return _protect_text(match.group(0))

    def _protect_latex(match: re.Match[str]) -> str:
        return _protect_text(
            _normalize_latex_math(
                match.group(0), obsidian=bool(latex_obsidian_normalize)
            )
        )

    def _protect_link(match: re.Match[str]) -> str:
        # `\&` inside a URL breaks the link once rendered; unescape it while
        # the link is being stashed so the fix survives protection.
        text = match.group(0).replace("\\&", "&")
        # 锚文本（`[...]` 内）属正文，token 去汉化必须在这里做——保护之后
        # 2d2 再也够不着它，否则会出现「QA 判死、fixer 修不掉」。URL 不动。
        if should_desinicize:
            text = re.sub(
                r"(?<=\[)[^\]]*(?=\])",
                lambda m: _desinicize_in_protected(m.group(0)),
                text,
                count=1,
            )
        return _protect_text(text)

    def _protect_table_row(match: re.Match[str]) -> str:
        # 表格单元同样是正文。先掩掉 inline code 再改写，避免动到单元格里的
        # 代码标识符。
        row = match.group(0)
        if should_desinicize:
            chunks: List[str] = []
            cursor = 0
            for code in _INLINE_CODE.finditer(row):
                chunks.append(_desinicize_in_protected(row[cursor:code.start()]))
                chunks.append(code.group(0))
                cursor = code.end()
            chunks.append(_desinicize_in_protected(row[cursor:]))
            row = "".join(chunks)
        return _protect_text(row)

    # Order matters: fenced code first (largest), then indented code blocks and
    # table rows (whole-line protection), then LaTeX, inline code, images, links, HTML.
    work = _FENCED_CODE_BLOCK.sub(_protect, content)
    work = _INDENTED_CODE_BLOCK.sub(_protect, work)
    work = _TABLE_ROW.sub(_protect_table_row, work)
    work = _LATEX_DISPLAY_MATH.sub(_protect_latex, work)
    work = _LATEX_INLINE_MATH.sub(_protect_latex, work)
    work = _INLINE_CODE.sub(_protect, work)
    # 代码、表格、公式和 inline code 已先保护；只修复正文中的链接外壳。
    work = _repair_collapsed_markdown_links(work)
    work = _MD_IMAGE.sub(_protect_link, work)
    work = _MD_LINK.sub(_protect_link, work)
    work = _HTML_COMMENT.sub(_protect, work)
    work = _HTML_TAG.sub(_protect, work)

    # --- Phase 2: Apply escaping / normalisation ---

    # 2a. Escape bare `$` → `\$`
    work = _BARE_DOLLAR.sub(lambda m: "\\$", work)

    # 2b. Escape bare `<` → `&lt;`
    work = _BARE_LT.sub("&lt;", work)

    # 2c. Escape mid-line `>` → `&gt;`  (preserve blockquote `>` at line start)
    work = _MID_LINE_GT.sub("&gt;", work)

    # 2d. Normalise excessive blank lines → max 2 newlines
    work = _EXCESSIVE_BLANK_LINES.sub("\n\n", work)

    # 2d2. token 严禁翻译：词元/令牌/代币 → token（令牌桶/令牌环 网络术语
    #      豁免）。置于 2e 之前，让替换出的 token 与相邻 CJK 之间补上空格。
    #      链接锚文本与表格单元已在 Phase 1 的保护回调里处理过。
    if should_desinicize:
        work = desinicize_token(work)

    # 2e. CJK–Latin spacing
    work = normalize_cjk_ascii_spacing(work)

    # 2f. Strip escape residue that has no meaning in prose (`\@`, `\&`)
    work = _USELESS_ESCAPES.sub(r"\1", work)

    # 2g. Halfwidth punctuation drift, thousands separators before 万/亿,
    #     doubled fullwidth punctuation
    work = _normalize_cjk_punctuation(work)

    # 2h. Quote style normalisation (straight quotes + CJK-adjacent spacing)
    work = _repair_quotes(work)

    # 2i. Standalone capitalized Token/Tokens → lowercase。复合专名
    #     （Tokenomics/TokenBudgeting）由词边界放过，带空格的专名
    #     （Token Ring/Token Factory）由 `(?!\s+[A-Z])` 放过，句首/标题首
    #     由位置判断放过。
    def _lower_token(match: re.Match[str]) -> str:
        if _at_sentence_start(work, match.start()):
            return match.group(0)
        return "token" + (match.group(1) or "")

    work = _CAPITALIZED_TOKEN_WORD.sub(_lower_token, work)

    # 2j. Strip exact repeated `中文（English）` annotations (annotation stacking)
    work = _dedupe_repeated_annotations(work)

    # --- Phase 3: Restore protected regions ---
    # A stashed value can itself contain a placeholder (e.g. an image nested
    # inside a link is protected first, so the link's stashed value embeds the
    # image placeholder). Restore repeatedly until no placeholder remains.
    while "\x00PROTECTED_" in work:
        changed = False
        for idx, original in enumerate(protected):
            token = f"\x00PROTECTED_{idx}\x00"
            if token in work:
                work = work.replace(token, original)
                changed = True
        if not changed:
            break

    return work


def _normalize_latex_math(math: str, *, obsidian: bool = False) -> str:
    """Normalize LaTeX math; optionally rewrite delimiters for Obsidian.

    With ``obsidian=False`` (default, per A-15) the source delimiters
    (``\\( \\)`` / ``\\[ \\]`` / ``$``) are preserved verbatim and only the
    harmful markdown escapes (``\\_``, ``\\*`` in environment names) inside
    the math body are repaired.
    """
    if not obsidian:
        return _normalize_latex_body(math)
    if math.startswith(r"\(") and math.endswith(r"\)"):
        body = _normalize_latex_body(math[2:-2].strip())
        return f"${body}$"
    if math.startswith(r"\[") and math.endswith(r"\]"):
        body = _normalize_latex_body(math[2:-2].strip())
        return f"$$\n{body}\n$$"
    return _normalize_latex_body(math)


def _repair_backslash_artifact(math: str) -> str:
    """还原被写成 ``\\backslash `` 的反斜杠。

    只在**明显是污染**时才动手：命中两处以上，或出现 ``\\backslash _`` 这种
    没有合法解释的形态。单独一处 ``\\backslash B`` 可能真是集合差，放过。
    """
    hits = _LATEX_BACKSLASH_ARTIFACT.findall(math)
    if not hits:
        return math
    if len(hits) < 2 and not _LATEX_BACKSLASH_CERTAIN.search(math):
        return math
    return _LATEX_BACKSLASH_ARTIFACT.sub("\\\\", math)


def normalize_math_fragment(math: str) -> str:
    """规范化一段公式正文（不含定界符），对外可用。

    导出链路走 :func:`postprocess_markdown` 时会自动做这件事，但公众号排版是
    另一条链路——用户往往直接把**已经存在**的译文粘进来，那里面的污染只能在
    排版时现修，否则公式照样渲染成字面的 ``\\mathbfq\\_l``。
    """
    return _normalize_latex_body(math)


def _normalize_latex_body(math: str) -> str:
    math = _repair_backslash_artifact(math)
    math = _LATEX_ESCAPED_STAR_ENV.sub(r"\1*\2", math)
    return _LATEX_ESCAPED_SUBSCRIPT.sub("_", math)
