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

# Inline code spans (`...`) — must NOT be touched.
_INLINE_CODE = re.compile(r"`[^`]+`")

# Markdown images: ![alt](url) or ![alt](url "title")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

# Markdown links: [text](url) or [text](url "title")
_MD_LINK = re.compile(r"\[[^\]]*\]\([^)]+\)")

# HTML tags (including self-closing) — preserve as-is.
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")

# HTML comments <!-- ... -->
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# Bare `$` that would trigger MathJax/KaTeX rendering.
# We escape standalone `$` but NOT already-escaped `\$`.
# Also skip `$$` pairs which are intentional math blocks.
_BARE_DOLLAR = re.compile(r"(?<!\\)(?<![$])[$](?![$])")

# Bare `<` that is NOT part of an HTML tag or comment.
# Lookahead checks it's not followed by a tag-name pattern or `!--`.
_BARE_LT = re.compile(r"<(?![a-zA-Z/!])")

# Bare `>` at start of line that is NOT a blockquote (we only escape mid-line `>`).
_MID_LINE_GT = re.compile(r"(?<=\S)>")

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

    # Order matters: fenced code first, then LaTeX, inline code, images, links, HTML.
    work = _FENCED_CODE_BLOCK.sub(_protect, content)
    work = _LATEX_DISPLAY_MATH.sub(_protect_latex, work)
    work = _LATEX_INLINE_MATH.sub(_protect_latex, work)
    work = _INLINE_CODE.sub(_protect, work)
    work = _MD_IMAGE.sub(_protect, work)
    work = _MD_LINK.sub(_protect, work)
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

    # --- Phase 3: Restore protected regions ---
    for idx, original in enumerate(protected):
        work = work.replace(f"\x00PROTECTED_{idx}\x00", original)

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
