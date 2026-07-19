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
        "黄仁勋表示，token 消耗量增长了三倍，“前所未有”。\n\n"
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
    issues = run_deterministic_qa("他说“话没关上就走了")
    assert "quote_imbalance" in _codes(issues)


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
