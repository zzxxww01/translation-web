# -*- coding: utf-8 -*-
"""A-1 双标题文件名 bug 回归测试（title_guard 前缀回插收紧）。"""

from src.core.title_guard import (
    enforce_translated_title,
    extract_title_requirements,
    find_missing_title_terms,
)


def test_long_colon_prefix_is_not_preserved():
    # 2026-07 实测翻车：前缀 "Anthropic 3Q26 Profit Over $1B" 被误判为
    # 产品代号并整段回插，产出双标题文件名。
    source = "Anthropic 3Q26 Profit Over $1B: X"
    translated = "Anthropic 2026 年第三季度利润超 10 亿美元：X 分析"

    assert extract_title_requirements(source).required_prefix is None
    assert enforce_translated_title(source, translated) == translated
    assert find_missing_title_terms(source, translated) == []


def test_camelcase_prefix_over_12_chars_not_preserved():
    # "TokenBudgeting"（14 字符）命中 INTERNAL_CAP_RE，但超出短代号长度上限。
    source = "TokenBudgeting: X"
    translated = "Token 预算：全新监控方案"

    assert extract_title_requirements(source).required_prefix is None
    assert enforce_translated_title(source, translated) == translated
    assert find_missing_title_terms(source, translated) == []


def test_title_without_colon_has_no_prefix():
    source = "Cerebras — Faster Tokens Please"
    translated = "Cerebras：更快的 token 供给"

    assert extract_title_requirements(source).required_prefix is None
    assert enforce_translated_title(source, translated) == translated


def test_short_product_code_prefix_still_reinserted_when_lost():
    # 收紧后仍保留原能力：短产品代号（<=12 字符、空格 <2）在译文确实
    # 丢失（译文比代号还短）时回插。
    source = "GPT-5: The Next Step"
    translated = "下一步"

    requirements = extract_title_requirements(source)
    assert requirements.required_prefix == "GPT-5"
    assert enforce_translated_title(source, translated) == "GPT-5：下一步"


def test_full_retranslation_longer_than_prefix_never_reinserted():
    # 译文长度 >= 原前缀说明是完整重译而非丢失，一律不回插。
    source = "GPT-5: The Next Step"
    translated = "迈向下一步的完整重译标题"

    assert enforce_translated_title(source, translated) == translated
    assert find_missing_title_terms(source, translated) == []


def test_prefix_with_two_spaces_not_preserved():
    source = "Nvidia GB300 NVL72: Deep Dive"
    assert extract_title_requirements(source).required_prefix is None
