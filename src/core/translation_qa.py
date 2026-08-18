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

from .protected_terms import SINICIZED_TOKEN_RE, source_mentions_token


_MAX_SAMPLES_PER_CHECK = 5

_CJK_RE = re.compile(r"[一-鿿]")

# --- critical patterns -----------------------------------------------------

_PLACEHOLDER_RESIDUE = re.compile(r"\x00PROTECTED_\d+\x00|￰\d+￰")
# 放宽（A-2）：既抓 `[[LINK_n` 形近写法，也抓 `](LINK_1)`（token id 被当 URL）
# 等任意 `(`/`[`/`{` 后紧跟 token id 的畸形残留。
_FORMAT_TOKEN_RESIDUE = re.compile(
    r"[\(\[\{]\s*(?:LINK|STRONG|EM|CODE)_\d+", re.IGNORECASE
)
_LATEX_MANGLED = re.compile(
    r"(?<![\\A-Za-z])(?:ext\{|rac\{|egin\{|imes\b|cdot\b)"
)
_LINK_COLLAPSE = re.compile(r"\[[^\]\[]*\[[^\]]*\]\(")
_URL_ESCAPED_AMP = re.compile(r"\\&")
# token 严禁翻译（用户硬性要求）。定义源在 protected_terms，与
# markdown_postprocess 的确定性 fixer 共用同一套规则——只有「fixer 修得掉」
# 的东西才配判 critical，否则就是永久阻断导出。
_TOKEN_SINICIZED = SINICIZED_TOKEN_RE
# 功率单位被汉化：warning 而非 critical。中文功率单位不是工程残骸而是风格
# 偏好，且没有确定性 fixer（「兆瓦时 / 千瓦时 / 兆瓦日」在电力市场文章里
# 就是标准中文单位，机械回写会改坏），故以 `(?![时日])` 排除计量组合词。
_POWER_UNIT_SINICIZED = re.compile(r"(?:吉瓦|兆瓦|千瓦)(?![时日])")
# 英寸/机架尺寸记号（2.5" SSD、19" 机架）：统计引号配平前先掩掉，否则一个
# 尺寸标记就会让全文直引号数变奇数。
_INCH_MARK = re.compile(r"\d+(?:\.\d+)?\s*\"")

# --- warning patterns ------------------------------------------------------

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
# H2-H6 对照（导出 zh 固定带 `# 标题` H1，而 en 源文常无 H1，
# 用 H2+ 对照才能准确抓"zh 独有标题"，见 A-4/A-5）。
_SUBHEADING_MD = re.compile(r"^#{2,6}\s", re.MULTILINE)
_BLOCKQUOTE_LINE = re.compile(r"^\s*>", re.MULTILINE)
_LOCAL_IMAGE_PLACEHOLDER = re.compile(r"\]\(images/img_")
# 非图片 markdown 链接的 URL（`![...](...)` 由 image 检查负责）
_MD_LINK_URL = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(<?[^)\s]+>?)(?:\s+\"[^\"]*\")?\s*\)")
# 大写 Token/Tokens 独立词（词边界天然放过 Tokenomics/TokenBudgeting/
# Tokenmaxxing 等复合专名白名单）
_TOKEN_CAPITALIZED = re.compile(r"\bTokens?\b")
# `中文（English）` 首现括注
_CJK_EN_ANNOTATION = re.compile(
    r"(?<=[一-鿿])（\s*([A-Za-z][A-Za-z0-9 .&'/+-]{0,60}?)\s*）"
)
# 括注区段（术语残留扫描用）：`（English）` 内的英文属合法首现标注，
# 统计残留前整段掩掉。
_EN_ANNOTATION_SPAN = re.compile(r"（\s*[A-Za-z][A-Za-z0-9 .&'/+-]{0,60}\s*）")
# 词表英文原词的合法形态（用于构造词边界残留扫描 regex）
_GLOSSARY_TERM_SHAPE = re.compile(r"[A-Za-z][A-Za-z0-9 .&'/+-]*")
_GLOSSARY_RESIDUE_TOP_N = 10
# 金额量级抽验（A-6）：en 侧 $?数字+million/billion/trillion/M/B/T
# （单字母缩写只认大写，避免把 "3 m cable" 之类误当金额量级）
_EN_MONEY_MAGNITUDE = re.compile(
    r"\$?\s*(\d+(?:\.\d+)?)\s*([Mm]illion|[Bb]illion|[Tt]rillion|[MBT]\b)"
)
_ZH_MONEY_MAGNITUDE = re.compile(r"(\d+(?:\.\d+)?)\s*(万亿|亿|万)")
_EN_MAGNITUDE_MULTIPLIER = {
    "million": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "b": 1e9,
    "trillion": 1e12,
    "t": 1e12,
}
_ZH_MAGNITUDE_MULTIPLIER = {"万": 1e4, "亿": 1e8, "万亿": 1e12}

_INLINE_CODE_MASK = re.compile(r"`[^`]*`")
_URL_MASK = re.compile(r"\(https?://[^)]*\)|https?://\S+")
_FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")
_TABLE_ROW_LINE = re.compile(r"^[ \t]*\|")


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


def _iter_prose_lines(
    lines: List[str], *, skip_tables: bool = False, mask_urls: bool = True
) -> Iterable[tuple[int, str]]:
    """Yield (lineno, line) outside fenced code, with inline code/URLs masked.

    ``skip_tables`` 额外跳过表格行。语义类检查（token 汉化、标点、单位）要
    看表格单元，因为那里同样是译文；而工程残留类检查（``ext{``、``LINK_n``）
    不能看表格——表格单元里的这些字符往往是合法内容。

    ``mask_urls=False`` 保留 URL 原文，供 ``url_escaped_amp`` 这类**专查 URL
    内部**的检查使用（掩掉 URL 会让它永远查不到东西）。
    """
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if skip_tables and _TABLE_ROW_LINE.match(line):
            continue
        masked = _INLINE_CODE_MASK.sub("`X`", line)
        if mask_urls:
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


# 公式对照（与英文原文逐一比对）。公式是语言无关的，除了 `\text{}` 里可能被翻译
# 的文字，译文里的每一条都应当与原文完全相同。
_MATH_BLOCK_MD = re.compile(r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]")
_MATH_INLINE_MD = re.compile(r"(?<!\$)\$(?!\s)[^$\n]+?(?<!\s)\$(?!\$)|\\\([\s\S]*?\\\)")
# 撇号/引号在译文里会被规范化（弯 → 直），公式里的 `f_l’` → `f_l'` 属正常，
# 不归一会让每篇都误报。
_MATH_QUOTE_VARIANTS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "`": "'"})


def _math_signature(math: str) -> str:
    r"""公式的比较指纹：抹掉定界符、空白、`\text{}` 内容与引号变体。

    定界符不参与比较——`\(x\)` 和 `$x$` 是同一条公式，译文换写法不算问题。
    """
    body = math.strip()
    for opening, closing in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if body.startswith(opening) and body.endswith(closing):
            body = body[len(opening) : -len(closing)]
            break
    else:
        if len(body) >= 2 and body.startswith("$") and body.endswith("$"):
            body = body[1:-1]
    body = re.sub(r"\\text\{[^{}]*\}", r"\\text{}", body)
    body = body.translate(_MATH_QUOTE_VARIANTS)
    return re.sub(r"\s+", "", body)


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
    # 工程残留类检查用的窄口径：额外跳过表格行。
    strict_pairs = list(_iter_prose_lines(lines, skip_tables=True))
    # url_escaped_amp 专查 URL 内部，必须保留 URL 原文。
    url_pairs = list(_iter_prose_lines(lines, skip_tables=True, mask_urls=False))
    prose_text = "\n".join(line for _, line in prose_pairs)

    # --- 工程残留（critical）---
    # 占位符残留用 raw：PROTECTED_n 出现在代码块里同样是真 bug。
    _collect(issues, _PLACEHOLDER_RESIDUE, raw_pairs, "placeholder_residue",
             "critical", "占位符残留（PROTECTED_n / ￰n￰）")
    # 其余四项只看散文：fenced code 里的 `fetch(link_1)`、`int \& x`、
    # `\begin{}` 都是合法代码，表格单元同理。
    _collect(issues, _FORMAT_TOKEN_RESIDUE, strict_pairs, "format_token_residue",
             "critical", "隐藏格式 token 残留（[[[LINK_n|...]]] 类）")
    _collect(issues, _LATEX_MANGLED, strict_pairs, "latex_mangled",
             "critical", "LaTeX 脱杠残骸（ext{ / rac{ / egin{ / imes）")
    _collect(issues, _LINK_COLLAPSE, strict_pairs, "link_collapse",
             "critical", "markdown 链接嵌套塌缩（[ 内含 [...](）")
    _collect(issues, _URL_ESCAPED_AMP, url_pairs, "url_escaped_amp",
             "critical", "残留 \\&（URL 内会破坏链接）")
    # token 汉化：与 markdown_postprocess 的 fixer 同口径——原文没提 token
    # 时，「访问令牌」「代币」是正确译法，不报。
    if source is None or source_mentions_token(source):
        _collect(issues, _TOKEN_SINICIZED, prose_pairs, "token_sinicized",
                 "critical", "token 被汉化（词元/令牌/代币）——严禁翻译，应保留英文 "
                             "token（令牌桶/令牌环 等网络术语除外）")
    _collect(issues, _LOCAL_IMAGE_PLACEHOLDER, raw_pairs, "local_image_placeholder",
             "critical", "本地图片占位链接（images/img_），导出后必成死链")

    # 全文配平检查（document-level）。统计基于散文文本，代码块里的
    # `**kwargs` / `$$` 不参与配平。
    bold_marks = len(re.findall(r"\*\*", prose_text))
    if bold_marks % 2:
        issues.append(QAIssue(
            code="bold_parity", severity="critical",
            message=f"加粗标记 ** 全文共 {bold_marks} 个（奇数，存在未闭合）",
        ))
    math_fences = len(re.findall(r"^\s*\$\$\s*$", prose_text, re.MULTILINE))
    if math_fences % 2:
        issues.append(QAIssue(
            code="mathblock_parity", severity="critical",
            message=f"$$ 公式块定界符共 {math_fences} 个（奇数，存在未闭合）",
        ))

    # --- 惯例与排版（warning）---
    _collect(issues, _POWER_UNIT_SINICIZED, prose_pairs, "power_unit_sinicized",
             "warning", "功率单位被译（吉瓦/兆瓦/千瓦），建议保留 GW/MW/kW 原形"
                        "（兆瓦时/千瓦时 等计量组合词不计）")
    # 目标风格为英文直引号（A-12）：按直引号总数配平（散文区，掩码后统计）。
    # 单段漏一个闭引号不该让整篇不可导出——定位交给行级 straight_quote_odd。
    straight_quotes = sum(
        _INCH_MARK.sub("", line).count('"') for _, line in prose_pairs
    )
    if straight_quotes % 2:
        issues.append(QAIssue(
            code="quote_imbalance", severity="warning",
            message=f"直引号 \" 全文共 {straight_quotes} 个（奇数，存在未闭合）",
        ))

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
    _collect(issues, _TOKEN_CAPITALIZED, prose_pairs, "token_capitalized",
             "warning", "独立词大写 Token/Tokens（应小写；Tokenomics 等复合专名除外）")

    # 词表 translate/first_annotate 术语的英文原词残留扫描（warning）
    residue_issue = _check_glossary_term_residue(prose_pairs)
    if residue_issue is not None:
        issues.append(residue_issue)

    # 同一英文词的 `中文（English）` 括注出现 >= 2 次（括注堆叠，A-11）
    annotation_counts: dict[str, int] = {}
    for _, line in prose_pairs:
        for term in _CJK_EN_ANNOTATION.findall(line):
            key = term.strip()
            annotation_counts[key] = annotation_counts.get(key, 0) + 1
    repeated_annotations = sorted(
        term for term, count in annotation_counts.items() if count >= 2
    )
    if repeated_annotations:
        issues.append(QAIssue(
            code="annotation_repeated", severity="warning",
            message="同一英文词的“中文（English）”括注出现 ≥2 次（首现之后应只用中文名）",
            sample="、".join(repeated_annotations[:_MAX_SAMPLES_PER_CHECK]),
        ))

    odd_quote_lines = [
        (lineno, line) for lineno, line in prose_pairs
        if _INCH_MARK.sub("", line).count('"') % 2
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

    # --- 与英文原文对照（可选）---
    if source:
        src_imgs = len(_IMAGE_MD.findall(source))
        dst_imgs = len(_IMAGE_MD.findall(content))
        if src_imgs != dst_imgs:
            issues.append(QAIssue(
                code="image_count_mismatch", severity="warning",
                message=f"图片数量与原文不一致：en={src_imgs} zh={dst_imgs}",
            ))

        # 公式对照（A-5 同款口径）。翻译环节改写公式是真实发生过的事故：
        # `\mathbf{q}_l` 被写成 `\backslash mathbf{q}\backslash _l`，渲染出来是
        # 字面的 `\mathbfq\_l`。postprocess 已能自动还原这一类，这里是兜底报警，
        # 也能抓到自动修不了的（公式被改写、整条漏译）。
        # warning 而非 critical，理由同 image_count_mismatch。
        for kind, pattern, label in (
            ("block", _MATH_BLOCK_MD, "块级"),
            ("inline", _MATH_INLINE_MD, "行内"),
        ):
            src_math = pattern.findall(source)
            dst_math = pattern.findall(content)
            if len(src_math) != len(dst_math):
                issues.append(QAIssue(
                    code=f"math_{kind}_count_mismatch", severity="warning",
                    message=f"{label}公式数量与原文不一致："
                            f"en={len(src_math)} zh={len(dst_math)}（检查漏译或被改写）",
                ))
                continue
            altered = [
                (index, src_item, dst_item)
                for index, (src_item, dst_item) in enumerate(zip(src_math, dst_math), 1)
                if _math_signature(src_item) != _math_signature(dst_item)
            ]
            if altered:
                samples = [
                    f"第{index}条 en={_math_signature(src_item)[:60]} "
                    f"zh={_math_signature(dst_item)[:60]}"
                    for index, src_item, dst_item in altered[:_MAX_SAMPLES_PER_CHECK]
                ]
                issues.append(QAIssue(
                    code=f"math_{kind}_altered", severity="warning",
                    message=f"{label}公式有 {len(altered)} 条与原文不一致"
                            "（公式不该被翻译改写）",
                    sample=" | ".join(samples)[:300],
                ))

        # zh 独有标题（A-4/A-5）：按 H2-H6 对照——导出 zh 固定带 `# 标题` H1，
        # 而 en 源文常无 H1，全级别对照会造成常态误报。
        # warning 而非 critical：源文页尾促销/署名段常不纳入翻译，数量对不上
        # 是常态，硬阻断会让现存文章全部导不出。
        src_subheads = len(_SUBHEADING_MD.findall(source))
        dst_subheads = len(_SUBHEADING_MD.findall(content))
        if dst_subheads > src_subheads:
            issues.append(QAIssue(
                code="extra_heading", severity="warning",
                message=f"译文标题数多于原文：en={src_subheads} zh={dst_subheads}"
                        "（疑似自造“引言”类标题）",
            ))
        elif src_subheads != dst_subheads:
            issues.append(QAIssue(
                code="heading_count_mismatch", severity="warning",
                message=f"标题数量与原文不一致：en={src_subheads} zh={dst_subheads}"
                        "（检查是否漏译标题）",
            ))

        # 链接数对照 + URL 集合 diff（A-5）。两侧口径先归一：zh 已过
        # postprocess（URL 里的 `\&` 被还原成 `&`），en 是原始源文。
        # warning 而非 critical，理由同 extra_heading。
        src_urls = [
            url.strip("<>").replace("\\&", "&") for url in _MD_LINK_URL.findall(source)
        ]
        dst_urls = [
            url.strip("<>").replace("\\&", "&") for url in _MD_LINK_URL.findall(content)
        ]
        if len(src_urls) != len(dst_urls):
            issues.append(QAIssue(
                code="link_count_mismatch", severity="warning",
                message=f"链接数量与原文不一致：en={len(src_urls)} zh={len(dst_urls)}",
            ))
        missing_urls = sorted(set(src_urls) - set(dst_urls))
        extra_urls = sorted(set(dst_urls) - set(src_urls))
        if missing_urls or extra_urls:
            samples = []
            if missing_urls:
                samples.append("缺失: " + " ".join(missing_urls[:3]))
            if extra_urls:
                samples.append("多出: " + " ".join(extra_urls[:3]))
            issues.append(QAIssue(
                code="url_set_diff", severity="warning",
                message=f"URL 集合与原文不一致：缺失 {len(missing_urls)} 条、"
                        f"多出 {len(extra_urls)} 条（防漏链/错链）",
                sample=" | ".join(samples)[:200],
            ))

        # blockquote `>` 行数对照（warning，防引用块合并/拆分）
        src_quotes = len(_BLOCKQUOTE_LINE.findall(source))
        dst_quotes = len(_BLOCKQUOTE_LINE.findall(content))
        if src_quotes != dst_quotes:
            issues.append(QAIssue(
                code="blockquote_count_mismatch", severity="warning",
                message=f"blockquote `>` 行数与原文不一致：en={src_quotes} "
                        f"zh={dst_quotes}（禁合并/拆分引用块）",
            ))

        issues.extend(_check_money_magnitude(source, content))

    return issues


def _check_money_magnitude(source: str, content: str) -> List[QAIssue]:
    """金额量级抽验（A-6，warning）：抓 en↔zh 之间疑似 10 倍量级换算错。

    en 侧提取 `$X million/billion/trillion|M/B/T`，zh 侧提取 `Y 万/亿/万亿`，
    数值做货币无关的等值比对；某个 en 金额在 zh 中找不到等值数（±18%），
    却存在 ~10 倍/0.1 倍的数（±15%），即报 warning。不求全，抓 top 案例。
    """
    issues: List[QAIssue] = []
    zh_values = [
        float(number) * _ZH_MAGNITUDE_MULTIPLIER[unit]
        for number, unit in _ZH_MONEY_MAGNITUDE.findall(content)
    ]
    if not zh_values:
        return issues

    seen: set = set()
    flagged = 0
    for number, unit in _EN_MONEY_MAGNITUDE.findall(source):
        value = float(number) * _EN_MAGNITUDE_MULTIPLIER[unit.lower()]
        if value in seen or value <= 0:
            continue
        seen.add(value)

        has_equivalent = any(0.82 <= zh / value <= 1.18 for zh in zh_values)
        if has_equivalent:
            continue
        near_tenfold = [
            zh for zh in zh_values
            if 8.5 <= zh / value <= 11.5 or 8.5 <= value / zh <= 11.5
        ]
        if not near_tenfold:
            continue
        if flagged < _MAX_SAMPLES_PER_CHECK:
            issues.append(QAIssue(
                code="money_magnitude", severity="warning",
                message="金额量级疑似 10 倍换算错误（原文已是万/亿量级时禁止再乘 10）",
                sample=f"en: {number} {unit} ≈ {value:g} ↔ zh 侧最近值 "
                       f"{near_tenfold[0]:g}",
            ))
        flagged += 1
    return issues


def _load_translate_strategy_terms() -> List[str]:
    """加载全局词表中 strategy 为 translate/first_annotate 的英文原词。

    复用项目现有 Glossary 加载方式（GlossaryManager.load_global）；任何加载
    异常（缺文件/坏 JSON/依赖问题）一律静默跳过——本检查是 best-effort
    warning，不得因词表不可用而阻断 QA。
    """
    try:
        from .glossary import GlossaryManager
        from .models import TranslationStrategy

        glossary = GlossaryManager().load_global()
    except Exception:
        return []

    terms: List[str] = []
    for term in glossary.terms:
        if getattr(term, "status", "active") != "active":
            continue
        if term.strategy not in (
            TranslationStrategy.TRANSLATE,
            TranslationStrategy.FIRST_ANNOTATE,
        ):
            continue
        original = (term.original or "").strip()
        if original and _GLOSSARY_TERM_SHAPE.fullmatch(original):
            terms.append(original)
    return terms


def _check_glossary_term_residue(
    prose_pairs: List[tuple[int, str]]
) -> Optional[QAIssue]:
    """词表要求翻译的术语在译文正文中的英文原词残留扫描（warning）。

    词边界、大小写不敏感、含简单复数 s；`中文（English）` 首现括注内的
    英文属合法出现，先掩掉括注区段再统计。报 top 10。
    """
    terms = _load_translate_strategy_terms()
    if not terms:
        return None

    masked_lines = [
        _EN_ANNOTATION_SPAN.sub("（）", line) for _, line in prose_pairs
    ]
    counts: dict[str, int] = {}
    for term in terms:
        pattern = re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(term) + r"s?(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        total = sum(len(pattern.findall(line)) for line in masked_lines)
        if total:
            counts[term] = total
    if not counts:
        return None

    top = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    top = top[:_GLOSSARY_RESIDUE_TOP_N]
    return QAIssue(
        code="glossary_term_residue",
        severity="warning",
        message=f"词表 translate/first_annotate 术语英文原词残留 {len(counts)} 种"
                f"（top {len(top)}；“中文（English）”首现括注内不计）",
        sample="、".join(f"{term}×{count}" for term, count in top),
    )


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
