"""Deterministic post-translation QA checks for exported markdown.

Codifies the recurring engineering defects found in the 15-article
SemiAnalysis pipeline audit (占位符残留、LaTeX 脱杠、链接塌缩、加粗/公式
配平、引号方向、token 汉化、千分位+万/亿 etc.) as pure-regex checks that
never depend on model judgement.

Notes on intentional pipeline conventions (NOT flagged here):
- ``&lt;`` / ``&gt;`` / ``\\$`` are inserted on purpose by
  :mod:`markdown_postprocess` to keep bare ``<``/``$`` from breaking
  rendering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


_MAX_SAMPLES_PER_CHECK = 5

_CJK_RE = re.compile(r"[一-鿿]")

# --- critical patterns -----------------------------------------------------

_PLACEHOLDER_RESIDUE = re.compile(r"\x00PROTECTED_\d+\x00|￰\d+￰")
_FORMAT_TOKEN_RESIDUE = re.compile(
    r"\[{2,}\s*(?:LINK|STRONG|EM|CODE)_\d+", re.IGNORECASE
)
_LATEX_MANGLED = re.compile(
    r"(?<![\\A-Za-z])(?:ext\{|rac\{|egin\{|imes\b|cdot\b)"
)
_LINK_COLLAPSE = re.compile(r"\[[^\]\[]*\[[^\]]*\]\(")
_URL_ESCAPED_AMP = re.compile(r"\\&")
_TOKEN_SINICIZED = re.compile(r"词元|代币经济学")

# --- warning patterns ------------------------------------------------------

_TOKEN_AS_LINGPAI = re.compile(r"令牌")
_DAY_SINICIZED = re.compile(r"第\s?[零0一]\s?[天日]")
_FAN_LIANG_FAN = re.compile(r"翻两番")
_THOUSANDS_MAGNITUDE = re.compile(r"\d,\d{3}\s?[万亿]")
_CJK_HALFWIDTH_RESIDUE = re.compile(
    r"[一-鿿][,;:!?](?=[一-鿿\s）】「」『』]|$)", re.MULTILINE
)
_DOUBLED_PUNCT = re.compile(r"(?:，，|。。|：：|、、|；；)")
_STACKED_CHARS = re.compile(r"(?<!实)在在|(?<!的)的的|(?<!了)了了")
_HEADING_LINE = re.compile(r"^#{2,6}\s")
_IMAGE_MD = re.compile(r"!\[[^\]]*\]\(")
_HEADING_MD = re.compile(r"^#{1,6}\s", re.MULTILINE)
_LOCAL_IMAGE_PLACEHOLDER = re.compile(r"\]\(images/img_")

_INLINE_CODE_MASK = re.compile(r"`[^`]*`")
_URL_MASK = re.compile(r"\(https?://[^)]*\)|https?://\S+")
_FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")


@dataclass(frozen=True)
class QAIssue:
    """A single deterministic QA finding."""

    code: str
    severity: str  # "critical" | "warning"
    message: str
    line: int = 0  # 1-based; 0 = document-level
    sample: str = ""

    def to_dict(self) -> dict:
        payload = {
            "type": f"qa_{self.code}",
            "severity": "error" if self.severity == "critical" else "warning",
            "message": self.message,
        }
        if self.line:
            payload["line"] = self.line
        if self.sample:
            payload["sample"] = self.sample
        return payload


def _iter_prose_lines(lines: List[str]) -> Iterable[tuple[int, str]]:
    """Yield (lineno, line) outside fenced code, with inline code/URLs masked."""
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        masked = _INLINE_CODE_MASK.sub("`X`", line)
        masked = _URL_MASK.sub("(URL)", masked)
        yield lineno, masked


def _collect(
    issues: List[QAIssue],
    pattern: re.Pattern[str],
    pairs: Iterable[tuple[int, str]],
    code: str,
    severity: str,
    message: str,
) -> None:
    hits = 0
    for lineno, line in pairs:
        if pattern.search(line):
            if hits < _MAX_SAMPLES_PER_CHECK:
                issues.append(
                    QAIssue(
                        code=code,
                        severity=severity,
                        message=message,
                        line=lineno,
                        sample=line.strip()[:120],
                    )
                )
            hits += 1
    if hits > _MAX_SAMPLES_PER_CHECK:
        issues.append(
            QAIssue(
                code=code,
                severity=severity,
                message=f"{message}（另有 {hits - _MAX_SAMPLES_PER_CHECK} 行未逐条列出）",
            )
        )


def run_deterministic_qa(
    content: str, source: Optional[str] = None
) -> List[QAIssue]:
    """Run all deterministic checks against final translated markdown.

    ``source`` (the English markdown) is optional; when given, structural
    counts (headings/images) are compared as warnings.
    """
    issues: List[QAIssue] = []
    if not content:
        return issues

    lines = content.split("\n")
    raw_pairs = list(enumerate(lines, 1))
    prose_pairs = list(_iter_prose_lines(lines))

    # --- 工程残留（critical）---
    _collect(issues, _PLACEHOLDER_RESIDUE, raw_pairs, "placeholder_residue",
             "critical", "占位符残留（PROTECTED_n / ￰n￰）")
    _collect(issues, _FORMAT_TOKEN_RESIDUE, raw_pairs, "format_token_residue",
             "critical", "隐藏格式 token 残留（[[[LINK_n|...]]] 类）")
    _collect(issues, _LATEX_MANGLED, raw_pairs, "latex_mangled",
             "critical", "LaTeX 脱杠残骸（ext{ / rac{ / egin{ / imes）")
    _collect(issues, _LINK_COLLAPSE, raw_pairs, "link_collapse",
             "critical", "markdown 链接嵌套塌缩（[ 内含 [...](）")
    _collect(issues, _URL_ESCAPED_AMP, raw_pairs, "url_escaped_amp",
             "critical", "残留 \\&（URL 内会破坏链接）")
    _collect(issues, _TOKEN_SINICIZED, prose_pairs, "token_sinicized",
             "critical", "token 被汉化（词元）或 Tokenomics 误译为代币经济学")
    _collect(issues, _LOCAL_IMAGE_PLACEHOLDER, raw_pairs, "local_image_placeholder",
             "critical", "本地图片占位链接（images/img_），导出后必成死链")

    # 全文配平检查（document-level）
    bold_marks = len(re.findall(r"\*\*", content))
    if bold_marks % 2:
        issues.append(QAIssue(
            code="bold_parity", severity="critical",
            message=f"加粗标记 ** 全文共 {bold_marks} 个（奇数，存在未闭合）",
        ))
    math_fences = len(re.findall(r"^\s*\$\$\s*$", content, re.MULTILINE))
    if math_fences % 2:
        issues.append(QAIssue(
            code="mathblock_parity", severity="critical",
            message=f"$$ 公式块定界符共 {math_fences} 个（奇数，存在未闭合）",
        ))
    n_open, n_close = content.count("“"), content.count("”")
    if n_open != n_close:
        issues.append(QAIssue(
            code="quote_imbalance", severity="critical",
            message=f"双引号方向不配平：开引号={n_open} 闭引号={n_close}",
        ))

    # --- 惯例与排版（warning）---
    _collect(issues, _TOKEN_AS_LINGPAI, prose_pairs, "token_as_lingpai",
             "warning", "出现「令牌」——若源文是 AI 语境的 token 应保留英文")
    _collect(issues, _DAY_SINICIZED, prose_pairs, "day_sinicized",
             "warning", "Day 0/Day N 疑似被汉化（第零天/第一日）")
    _collect(issues, _FAN_LIANG_FAN, prose_pairs, "fan_liang_fan",
             "warning", "「翻两番」=4 倍——若源文是 triple/tripling 应为「三倍」")
    _collect(issues, _THOUSANDS_MAGNITUDE, prose_pairs, "thousands_magnitude",
             "warning", "数字+万/亿仍带千分位逗号（如 2,600 万）")
    _collect(issues, _CJK_HALFWIDTH_RESIDUE, prose_pairs, "halfwidth_punct",
             "warning", "中文语境残留半角标点")
    _collect(issues, _DOUBLED_PUNCT, prose_pairs, "doubled_punct",
             "warning", "叠写标点（：： ，， 。。）")
    _collect(issues, _STACKED_CHARS, prose_pairs, "stacked_chars",
             "warning", "疑似拼接叠字（在在/的的/了了）")

    odd_quote_lines = [
        (lineno, line) for lineno, line in prose_pairs
        if line.count('"') % 2
    ]
    for lineno, line in odd_quote_lines[:_MAX_SAMPLES_PER_CHECK]:
        issues.append(QAIssue(
            code="straight_quote_odd", severity="warning",
            message="行内直引号 \" 数量为奇数，无法自动配对，需人工确认",
            line=lineno, sample=line.strip()[:120],
        ))

    english_headings = [
        (lineno, line) for lineno, line in raw_pairs
        if _HEADING_LINE.match(line) and not _CJK_RE.search(line)
    ]
    for lineno, line in english_headings[:_MAX_SAMPLES_PER_CHECK]:
        issues.append(QAIssue(
            code="english_heading", severity="warning",
            message="标题行无任何中文（疑似漏译；型号/代号标题可忽略）",
            line=lineno, sample=line.strip()[:120],
        ))

    # --- 与英文原文对照（可选，warning）---
    if source:
        src_imgs = len(_IMAGE_MD.findall(source))
        dst_imgs = len(_IMAGE_MD.findall(content))
        if src_imgs != dst_imgs:
            issues.append(QAIssue(
                code="image_count_mismatch", severity="warning",
                message=f"图片数量与原文不一致：en={src_imgs} zh={dst_imgs}",
            ))
        src_heads = len(_HEADING_MD.findall(source))
        dst_heads = len(_HEADING_MD.findall(content))
        if src_heads != dst_heads:
            issues.append(QAIssue(
                code="heading_count_mismatch", severity="warning",
                message=f"标题数量与原文不一致：en={src_heads} zh={dst_heads}"
                        "（检查是否自造或漏译标题）",
            ))

    return issues


def has_critical(issues: Iterable[QAIssue]) -> bool:
    return any(issue.severity == "critical" for issue in issues)


def format_qa_report(issues: Iterable[QAIssue]) -> str:
    lines = []
    for issue in issues:
        tag = "CRITICAL" if issue.severity == "critical" else "WARN"
        location = f" L{issue.line}" if issue.line else ""
        sample = f" | {issue.sample}" if issue.sample else ""
        lines.append(f"[{tag}]{location} {issue.code}: {issue.message}{sample}")
    return "\n".join(lines)
