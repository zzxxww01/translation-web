"""Markdown safety post-processor for translated content.

Escapes special characters that interfere with markdown rendering
(e.g., bare `$` triggering MathJax, `<` being interpreted as HTML)
while preserving intentional markdown syntax and embedded images/links.
"""

from __future__ import annotations

import re
from typing import List


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
_LATEX_INLINE_MATH = re.compile(
    r"(\\\(.*?\\\)|\$[^\$\n]+\$)"
)

# Markdown escaping that is harmful inside LaTeX math.
_LATEX_ESCAPED_SUBSCRIPT = re.compile(r"\\_")
_LATEX_ESCAPED_STAR_ENV = re.compile(r"(\\(?:begin|end)\{[^{}\n]*?)\\\*([^{}\n]*\})")

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
_CJK_LATIN_NO_SPACE = re.compile(
    r"([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff])"
    r"([A-Za-z0-9])"
)
_LATIN_CJK_NO_SPACE = re.compile(
    r"([A-Za-z0-9])"
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

# Thousands separators inside numbers followed by a Chinese magnitude word:
# 2,600 \u4e07 \u2192 2600 \u4e07 (the comma reads as a decimal-scale error in Chinese).
_THOUSANDS_BEFORE_CJK_MAGNITUDE = re.compile(
    r"(\d),(?=\d{3}(?:,\d{3})*\s*[\u4e07\u4ebf])"
)

# Doubled fullwidth punctuation left behind by chunk stitching (\uff1a\uff1a \u3002\u3002 \uff0c\uff0c).
_DOUBLED_FULLWIDTH_PUNCT = re.compile(r"([\uff0c\u3002\uff1a\uff1b\u3001])\1+")

# Escape residue that is never meaningful in markdown prose (`\@`, `\&`).
_USELESS_ESCAPES = re.compile(r"\\([@&])")


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
    text = _THOUSANDS_BEFORE_CJK_MAGNITUDE.sub(r"\1", text)
    text = _DOUBLED_FULLWIDTH_PUNCT.sub(r"\1", text)
    return text


def _pair_quotes_in_line(line: str) -> str:
    """Repair quote direction line by line.

    Two failure modes from batch translation are handled deterministically:
    straight double quotes left unpaired (`"x"`), and fullwidth quotes
    flattened to a single direction (`\u201dx\u201d` with zero opening quotes).
    Lines with an odd quote count are left untouched for the QA gate to flag.
    """
    n_straight = line.count('"')
    if n_straight and n_straight % 2 == 0:
        parts = []
        open_next = True
        for ch in line:
            if ch == '"':
                parts.append("\u201c" if open_next else "\u201d")
                open_next = not open_next
            else:
                parts.append(ch)
        line = "".join(parts)

    n_open, n_close = line.count("\u201c"), line.count("\u201d")
    if (
        (n_open == 0) != (n_close == 0)
        and (n_open + n_close) % 2 == 0
        and n_open + n_close >= 2
    ):
        parts = []
        open_next = True
        for ch in line:
            if ch in "\u201c\u201d":
                parts.append("\u201c" if open_next else "\u201d")
                open_next = not open_next
            else:
                parts.append(ch)
        line = "".join(parts)
    return line


def _repair_quotes(text: str) -> str:
    return "\n".join(_pair_quotes_in_line(line) for line in text.split("\n"))


# ---------------------------------------------------------------------------
# Core processor
# ---------------------------------------------------------------------------

def postprocess_markdown(content: str) -> str:
    """Apply all markdown-safety transformations to *content*.

    The function is idempotent — running it twice produces the same output.

    Transformations applied:
    1. Escape bare ``$`` signs (prevents accidental MathJax).
    2. Escape bare ``<`` (prevents accidental HTML interpretation).
    3. Normalise excessive blank lines.
    4. Inject CJK–Latin spacing where missing.
    5. Preserve LaTeX formulas, code blocks, inline code, images, links, and HTML tags.
    """
    if not content:
        return content

    # --- Phase 1: Extract protected regions to placeholders ---
    protected: List[str] = []

    def _protect_text(text: str) -> str:
        idx = len(protected)
        protected.append(text)
        return f"\x00PROTECTED_{idx}\x00"

    def _protect(match: re.Match[str]) -> str:
        return _protect_text(match.group(0))

    def _protect_latex(match: re.Match[str]) -> str:
        return _protect_text(_normalize_latex_math(match.group(0)))

    def _protect_link(match: re.Match[str]) -> str:
        # `\&` inside a URL breaks the link once rendered; unescape it while
        # the link is being stashed so the fix survives protection.
        return _protect_text(match.group(0).replace("\\&", "&"))

    # Order matters: fenced code first (largest), then indented code blocks and
    # table rows (whole-line protection), then LaTeX, inline code, images, links, HTML.
    work = _FENCED_CODE_BLOCK.sub(_protect, content)
    work = _INDENTED_CODE_BLOCK.sub(_protect, work)
    work = _TABLE_ROW.sub(_protect, work)
    work = _LATEX_DISPLAY_MATH.sub(_protect_latex, work)
    work = _LATEX_INLINE_MATH.sub(_protect_latex, work)
    work = _INLINE_CODE.sub(_protect, work)
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

    # 2e. CJK–Latin spacing
    work = _CJK_LATIN_NO_SPACE.sub(r"\1 \2", work)
    work = _LATIN_CJK_NO_SPACE.sub(r"\1 \2", work)

    # 2f. Strip escape residue that has no meaning in prose (`\@`, `\&`)
    work = _USELESS_ESCAPES.sub(r"\1", work)

    # 2g. Halfwidth punctuation drift, thousands separators before 万/亿,
    #     doubled fullwidth punctuation
    work = _normalize_cjk_punctuation(work)

    # 2h. Quote-direction repair (straight quotes / single-direction bug)
    work = _repair_quotes(work)

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


def _normalize_latex_math(math: str) -> str:
    """Normalize LaTeX math for Obsidian-compatible Markdown export."""
    if math.startswith(r"\(") and math.endswith(r"\)"):
        body = _normalize_latex_body(math[2:-2].strip())
        return f"${body}$"
    if math.startswith(r"\[") and math.endswith(r"\]"):
        body = _normalize_latex_body(math[2:-2].strip())
        return f"$$\n{body}\n$$"
    return _normalize_latex_body(math)


def _normalize_latex_body(math: str) -> str:
    math = _LATEX_ESCAPED_STAR_ENV.sub(r"\1*\2", math)
    return _LATEX_ESCAPED_SUBSCRIPT.sub("_", math)
