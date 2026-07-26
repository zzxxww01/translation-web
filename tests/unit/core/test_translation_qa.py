# -*- coding: utf-8 -*-
"""确定性 QA gate 单元测试（translation_qa）。"""

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


def test_lingpai_is_warning_only():
    issues = run_deterministic_qa("每秒 500 个令牌")
    assert "token_as_lingpai" in _codes(issues)
    assert not has_critical(issues)


def test_bold_parity_detected():
    issues = run_deterministic_qa("**加粗** 后面还有一个 ** 落单")
    assert "bold_parity" in _codes(issues)


def test_quote_imbalance_detected():
    # A-12：改为直引号计数配平（奇数即 critical）
    issues = run_deterministic_qa('他说"话没关上就走了')
    assert "quote_imbalance" in _codes(issues)
    assert has_critical(issues)


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


def test_power_unit_sinicized_is_critical():
    issues = run_deterministic_qa("园区容量达 5 吉瓦，另有 300 兆瓦备用")
    assert "power_unit_sinicized" in _codes(issues)
    assert has_critical(issues)


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


def test_link_count_and_url_set_diff_are_critical():
    source = "见 [A](https://a.com) 与 [B](https://b.com)。"
    content = "见 [甲](https://a.com)。"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "link_count_mismatch" in codes
    assert "url_set_diff" in codes
    assert has_critical(issues)


def test_matching_links_not_flagged():
    source = "See [A](https://a.com) and ![img](https://i.com/x.png)."
    content = "见 [甲](https://a.com) 与 ![图](https://i.com/x.png)。"
    issues = run_deterministic_qa(content, source=source)
    codes = _codes(issues)
    assert "link_count_mismatch" not in codes
    assert "url_set_diff" not in codes


def test_extra_zh_heading_is_critical():
    source = "## A\n\n正文。\n"
    content = "## 引言\n\n导语。\n\n## 甲\n\n正文。\n"
    issues = run_deterministic_qa(content, source=source)
    assert "extra_heading" in _codes(issues)
    assert has_critical(issues)


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
