# -*- coding: utf-8 -*-
"""确定性 QA gate 单元测试（translation_qa）。"""

import pytest

from src.core import translation_qa
from src.core.translation_qa import (
    QAIssue,
    format_qa_report,
    has_critical,
    run_deterministic_qa,
)


def _codes(issues):
    return {issue.code for issue in issues}


def test_clean_content_has_no_issues():
    content = (
        "# 英伟达（Nvidia）发布新品\n\n"
        "## 市场影响\n\n"
        '黄仁勋表示，token 消耗量增长了三倍，"前所未有"。\n\n'
        "估值达到 2600 万美元。\n"
    )
    assert run_deterministic_qa(content) == []


def test_placeholder_residue_is_critical():
    issues = run_deterministic_qa("正文 \x00PROTECTED_3\x00 继续，另有 ￰4￰ 残留")
    assert "placeholder_residue" in _codes(issues)
    assert has_critical(issues)


def test_format_token_residue_detected():
    issues = run_deterministic_qa("这里 [[[LINK_2|SemiAnalysis]]] 没被还原")
    assert "format_token_residue" in _codes(issues)
    assert has_critical(issues)


def test_latex_mangled_detected():
    issues = run_deterministic_qa("公式 ext{GPU-hr} 与 rac{a}{b} 已碎裂")
    assert "latex_mangled" in _codes(issues)


def test_link_collapse_detected():
    issues = run_deterministic_qa("[外层文字[内层](https://a.com)塌缩了")
    assert "link_collapse" in _codes(issues)


def test_url_escaped_amp_detected():
    issues = run_deterministic_qa(r"链接 https://x.com/?a=1\&b=2 坏了")
    assert "url_escaped_amp" in _codes(issues)


def test_token_sinicized_is_critical():
    issues = run_deterministic_qa("模型每秒生成 500 个词元")
    assert "token_sinicized" in _codes(issues)
    assert has_critical(issues)


def test_lingpai_is_critical():
    # token 严禁翻译（用户硬性要求）：「令牌」从 warning 升级为 critical。
    issues = run_deterministic_qa("每秒 500 个令牌")
    assert "token_sinicized" in _codes(issues)
    assert has_critical(issues)


def test_daibi_is_critical():
    issues = run_deterministic_qa("该模型的代币定价上调了")
    assert "token_sinicized" in _codes(issues)
    assert has_critical(issues)


def test_token_bucket_and_ring_exempted():
    # 令牌桶/令牌环是网络术语 token bucket / token ring 的既定译法，豁免。
    issues = run_deterministic_qa("限流采用令牌桶算法，旧局域网用令牌环拓扑")
    assert "token_sinicized" not in _codes(issues)


def test_isolated_lingpai_next_to_exempt_compound_still_flagged():
    issues = run_deterministic_qa("令牌桶里的令牌会定期补充")
    assert "token_sinicized" in _codes(issues)
    assert has_critical(issues)


def test_bold_parity_detected():
    issues = run_deterministic_qa("**加粗** 后面还有一个 ** 落单")
    assert "bold_parity" in _codes(issues)


def test_quote_imbalance_detected():
    # A-12：直引号计数配平。奇数报 warning——单段漏一个闭引号不该让整篇
    # 不可导出，定位由行级 straight_quote_odd 承担。
    issues = run_deterministic_qa('他说"话没关上就走了')
    assert "quote_imbalance" in _codes(issues)
    assert "straight_quote_odd" in _codes(issues)
    assert not has_critical(issues)


def test_fan_liang_fan_is_warning():
    issues = run_deterministic_qa("出货量翻两番")
    assert "fan_liang_fan" in _codes(issues)
    assert not has_critical(issues)


def test_thousands_magnitude_is_warning():
    issues = run_deterministic_qa("营收 2,600 万美元")
    assert "thousands_magnitude" in _codes(issues)


def test_halfwidth_punct_residue_is_warning():
    issues = run_deterministic_qa("前半句正常,后半句失守")
    assert "halfwidth_punct" in _codes(issues)


def test_english_heading_is_warning():
    issues = run_deterministic_qa("## Nvidia versus AMD Disagg Prefill\n\n正文。\n")
    assert "english_heading" in _codes(issues)
    assert not has_critical(issues)


def test_code_blocks_are_skipped():
    content = "说明文字。\n\n```\nx = tokens 词元 ,test\next{abc}\n```\n"
    issues = run_deterministic_qa(content)
    assert "token_sinicized" not in _codes(issues)
    assert "halfwidth_punct" not in _codes(issues)
    # 关键断言：代码块内的任何内容都不得产生 critical。旧版只断言上面两个
    # code「不在」结果里，于是 `ext{abc}` 触发的 latex_mangled critical 一直
    # 绿灯通过，掩盖了整类误报。
    assert not has_critical(issues)


@pytest.mark.parametrize(
    "snippet",
    [
        "def f(**kwargs):\n    pass",  # ** 不参与全文加粗配平
        "void f(int \\& x);",  # C++ 引用不是 URL 转义残留
        "result = fetch(link_1)",  # 小写 link_1 不是格式 token 残留
        "$$\nE = mc^2",  # 代码块里的 $$ 不参与公式块配平
    ],
)
def test_fenced_code_never_blocks_export(snippet):
    content = f"说明文字。\n\n```\n{snippet}\n```\n"
    assert not has_critical(run_deterministic_qa(content))


def test_table_cells_are_exempt_from_engineering_residue():
    # 表格单元里的 `\&` 是合法内容，不该被当成 URL 转义残留而阻断导出。
    content = "| 参数 | 说明 |\n|---|---|\n| a \\& b | 位与 |\n"
    assert not has_critical(run_deterministic_qa(content))


def test_inch_mark_does_not_break_quote_parity():
    # 2.5" / 19" 是尺寸记号，不参与直引号配平。
    issues = run_deterministic_qa('机架采用 2.5" 硬盘位。')
    assert not has_critical(issues)
    assert "quote_imbalance" not in _codes(issues)


def test_quote_imbalance_is_warning_not_blocking():
    issues = run_deterministic_qa('他称之为 "最后一公里问题。')
    assert "quote_imbalance" in _codes(issues)
    assert not has_critical(issues)


def test_token_check_respects_source_without_token():
    # 原文没提 token 时，「访问令牌」「代币」是正确译法，不得判 critical。
    issues = run_deterministic_qa(
        "访问令牌会过期。", source="The access ticket expires."
    )
    assert "token_sinicized" not in _codes(issues)
    issues = run_deterministic_qa(
        "访问令牌会过期。", source="The access token expires."
    )
    assert "token_sinicized" in _codes(issues)


def test_source_structure_comparison():
    source = "# T\n\n## A\n\n![a](u1)\n\n![b](u2)\n"
    content = "# 标题\n\n## 甲\n\n![a](u1)\n"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "image_count_mismatch" in codes
    assert "heading_count_mismatch" not in codes  # 数量相同（各 2 个）


def test_issue_to_dict_shape():
    issue = QAIssue(code="x", severity="critical", message="m", line=3, sample="s")
    payload = issue.to_dict()
    assert payload["type"] == "qa_x"
    assert payload["severity"] == "error"
    assert payload["line"] == 3
    assert payload["sample"] == "s"


def test_format_report_contains_tags():
    issues = run_deterministic_qa("每秒 500 个词元")
    report = format_qa_report(issues)
    assert "CRITICAL" in report
    assert "token_sinicized" in report

# --- 2026-07 新增检查项（A-2 / A-5 / A-6 / A-12）---


def test_malformed_link_token_residue_detected():
    # A-2：`](LINK_1)`（token id 被当 URL 写入）也必须命中 critical。
    issues = run_deterministic_qa("残留 [**报告**](LINK_1)外](https://x.com)")
    assert "format_token_residue" in _codes(issues)
    assert has_critical(issues)


def test_power_unit_sinicized_is_warning():
    # warning 而非 critical：没有确定性 fixer 的 critical 等于永久阻断导出。
    issues = run_deterministic_qa("园区容量达 5 吉瓦，另有 300 兆瓦备用")
    assert "power_unit_sinicized" in _codes(issues)
    assert not has_critical(issues)


def test_power_unit_measure_words_are_not_flagged():
    # 「兆瓦时 / 千瓦时 / 兆瓦日」在电力市场文章里就是标准中文计量单位。
    issues = run_deterministic_qa("电价为 29 美元/兆瓦时，居民电价 0.15 美元/千瓦时")
    assert "power_unit_sinicized" not in _codes(issues)


def test_capitalized_token_word_is_warning():
    issues = run_deterministic_qa("每个 Token 都要计费")
    assert "token_capitalized" in _codes(issues)
    assert not has_critical(issues)


def test_compound_token_proper_nouns_whitelisted():
    issues = run_deterministic_qa("Tokenomics 与 TokenBudgeting 是专名，Tokenmaxxing 也是")
    assert "token_capitalized" not in _codes(issues)


def test_repeated_annotation_is_warning():
    content = (
        "德州电力可靠性委员会（ERCOT）负责调度。"
        "德州电力可靠性委员会（ERCOT）再次表态。"
    )
    issues = run_deterministic_qa(content)
    assert "annotation_repeated" in _codes(issues)
    assert not has_critical(issues)


def test_single_annotation_not_flagged():
    issues = run_deterministic_qa("英伟达（Nvidia）发布，台积电（TSMC）代工。")
    assert "annotation_repeated" not in _codes(issues)


def test_link_count_and_url_set_diff_are_warnings():
    # 与源文的结构对照降为 warning：源文页尾促销/署名段常不纳入翻译，
    # 数量对不上是常态，硬阻断会让现存文章全部导不出。
    source = "见 [A](https://a.com) 与 [B](https://b.com)。"
    content = "见 [甲](https://a.com)。"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "link_count_mismatch" in codes
    assert "url_set_diff" in codes
    assert not has_critical(issues)


def test_url_set_diff_normalises_escaped_amp():
    # zh 侧经 postprocess 已把 URL 里的 `\&` 还原成 `&`，两侧需同口径。
    source = r"见 [A](https://a.com/?x=1\&y=2)。"
    content = "见 [甲](https://a.com/?x=1&y=2)。"
    assert "url_set_diff" not in _codes(run_deterministic_qa(content, source=source))


def test_matching_links_not_flagged():
    source = "See [A](https://a.com) and ![img](https://i.com/x.png)."
    content = "见 [甲](https://a.com) 与 ![图](https://i.com/x.png)。"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "link_count_mismatch" not in codes
    assert "url_set_diff" not in codes


def test_extra_zh_heading_is_warning():
    source = "## A\n\n正文。\n"
    content = "## 引言\n\n导语。\n\n## 甲\n\n正文。\n"
    issues = run_deterministic_qa(content, source=source)
    assert "extra_heading" in _codes(issues)
    assert not has_critical(issues)


def test_missing_zh_heading_is_warning():
    source = "## A\n\n## B\n\n正文。\n"
    content = "## 甲\n\n正文。\n"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "heading_count_mismatch" in codes
    assert "extra_heading" not in codes


def test_blockquote_count_mismatch_is_warning():
    source = "> a\n\n> b\n\n> c\n\n> d\n"
    content = "> 甲\n\n> 乙\n"
    issues = run_deterministic_qa(content, source=source)
    assert "blockquote_count_mismatch" in _codes(issues)
    assert not has_critical(issues)


def test_money_magnitude_tenfold_error_flagged():
    # CXMT 实测：KRW 14.8 billion 被译成 1480 亿（10 倍错）。
    source = "Revenue reached KRW 14.8 billion this quarter."
    content = "本季度营收达 1480 亿韩元。"
    issues = run_deterministic_qa(content, source=source)
    assert "money_magnitude" in _codes(issues)
    assert not has_critical(issues)


def test_money_magnitude_correct_conversion_not_flagged():
    source = "Revenue reached $1.2B and capex was $500 million."
    content = "营收达 12 亿美元，资本支出为 5 亿美元。"
    issues = run_deterministic_qa(content, source=source)
    assert "money_magnitude" not in _codes(issues)


# --- 词表术语英文残留扫描（glossary_term_residue，warning）---


def test_glossary_term_residue_reports_top_counts(monkeypatch):
    monkeypatch.setattr(
        translation_qa, "_load_translate_strategy_terms",
        lambda: ["wafer", "foundry"],
    )
    content = "这批 wafer 良率不错，Wafers 供应仍紧张，foundry 产能已满载。"
    issues = run_deterministic_qa(content)
    issue = next(i for i in issues if i.code == "glossary_term_residue")
    assert issue.severity == "warning"
    assert "wafer×2" in issue.sample  # 大小写不敏感 + 简单复数 s
    assert "foundry×1" in issue.sample
    assert not has_critical(issues)


def test_glossary_term_residue_annotation_exempt(monkeypatch):
    # `中文（English）` 首现括注内的英文属合法出现，不计入残留。
    monkeypatch.setattr(
        translation_qa, "_load_translate_strategy_terms", lambda: ["wafer"]
    )
    issues = run_deterministic_qa("晶圆（wafer）产线扩建，此后全文均用中文晶圆。")
    assert "glossary_term_residue" not in _codes(issues)


def test_glossary_term_residue_word_boundary(monkeypatch):
    monkeypatch.setattr(
        translation_qa, "_load_translate_strategy_terms", lambda: ["node"]
    )
    issues = run_deterministic_qa("内部代号 nodex 不算残留，nodes 才算。")
    issue = next(i for i in issues if i.code == "glossary_term_residue")
    assert "node×1" in issue.sample


def test_glossary_residue_only_translate_strategies_scanned(monkeypatch):
    from src.core.glossary import GlossaryManager
    from src.core.models import Glossary, GlossaryTerm, TranslationStrategy

    glossary = Glossary(terms=[
        GlossaryTerm(
            original="wafer", translation="晶圆",
            strategy=TranslationStrategy.TRANSLATE,
        ),
        GlossaryTerm(
            original="EUV", translation="EUV",
            strategy=TranslationStrategy.PRESERVE,
        ),
    ])
    monkeypatch.setattr(GlossaryManager, "load_global", lambda self: glossary)
    issues = run_deterministic_qa("EUV 光刻配套的 wafer 产线。")
    issue = next(i for i in issues if i.code == "glossary_term_residue")
    assert "wafer×1" in issue.sample
    assert "EUV" not in issue.sample  # preserve 策略不参与残留扫描


def test_glossary_residue_loader_failure_is_silent(monkeypatch):
    from src.core.glossary import GlossaryManager

    def _boom(self):
        raise RuntimeError("glossary unavailable")

    monkeypatch.setattr(GlossaryManager, "load_global", _boom)
    issues = run_deterministic_qa("这批 wafer 良率不错。")
    assert "glossary_term_residue" not in _codes(issues)


# --- 公式对照（与英文原文逐一比对）-----------------------------------------
# 翻译改写公式是真实发生过的事故：`\mathbf{q}_l` 被写成
# `\backslash mathbf{q}\backslash _l`，渲染出来是字面的 `\mathbfq\_l`。


def test_math_altered_by_translation_reported():
    source = r"Each layer learns $\mathbf{q}_l=\mathbf{w}_l$ directly."
    content = r"每层直接学习 $\backslash mathbf{q}\backslash _l=\backslash mathbf{w}\backslash _l$。"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert "math_inline_altered" in codes


def test_math_block_dropped_reported():
    source = "A $$x=1$$ and B $$y=2$$."
    content = "甲 $$x=1$$，乙漏了。"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert "math_block_count_mismatch" in codes


def test_identical_math_not_reported():
    source = r"Formula $$\frac{a}{b}$$ and inline $x^2$."
    content = r"公式 $$\frac{a}{b}$$，行内 $x^2$。"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert not [code for code in codes if code.startswith("math_")]


def test_math_delimiter_rewrite_not_reported():
    r"""`\(x\)` 与 `$x$` 是同一条公式，译文换写法不算问题。"""
    source = r"Inline \(x^2\) here."
    content = r"行内 $x^2$ 如下。"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert not [code for code in codes if code.startswith("math_")]


def test_math_curly_apostrophe_normalization_not_reported():
    """撇号弯直归一（f_l’ → f_l'）是正常的规范化，不该每篇都误报。"""
    source = "Inline \\(f_l\u2019(x_l)\\) here."
    content = "行内 \\(f_l'(x_l)\\) 如下。"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert not [code for code in codes if code.startswith("math_")]


def test_math_text_content_may_be_translated():
    r"""`\text{}` 里的文字允许被翻译，不算公式被改写。"""
    source = r"$$E=\text{energy}$$"
    content = r"$$E=\text{能量}$$"
    codes = _codes(run_deterministic_qa(content, source=source))
    assert not [code for code in codes if code.startswith("math_")]
