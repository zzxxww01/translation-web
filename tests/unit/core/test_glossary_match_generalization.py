# -*- coding: utf-8 -*-
"""术语命中匹配的泛化性。

这些规则原先是照着手头十几篇文章调出来的，换一篇题材不同的文章就会失效或误伤。
每条都用**语料外**的输入钉死，避免以后又退回到只对现有语料成立的写法。
"""

from src.core.glossary_prompt import (
    _count_term_occurrences,
    _prose_only,
    select_prompt_terms_for_text,
)


def _terms(*pairs):
    return [
        {"original": original, "translation": translation, "strategy": "translate"}
        for original, translation in pairs
    ]


# --- 全大写术语大小写敏感 ---------------------------------------------------


def test_all_caps_term_does_not_match_lowercase_common_word():
    # BEST 是一家公司；小写 best 是普通英文词。大小写不敏感会让每篇文章都误命中。
    assert _count_term_occurrences("which cloud gives the best value", "BEST") == 0
    assert _count_term_occurrences("BEST acquired the fab", "BEST") == 1


def test_all_caps_acronym_still_matches_itself():
    assert _count_term_occurrences("the GPU and the CPU", "GPU") == 1


def test_mixed_case_term_stays_case_insensitive():
    # CoWoS / Neocloud 这类混合大小写词条仍应容忍原文的大小写差异
    assert _count_term_occurrences("cowos capacity is tight", "CoWoS") == 1


# --- 词形变化（复数） -------------------------------------------------------


def test_plural_forms_match():
    assert _count_term_occurrences("hyperscalers are buying wafers", "hyperscaler") == 1
    assert _count_term_occurrences("hyperscalers are buying wafers", "wafer") == 1


def test_es_plural_matches():
    assert _count_term_occurrences("the foundries expanded", "foundry") == 0  # 变形不还原
    assert _count_term_occurrences("the processes improved", "process") == 1


def test_plural_does_not_bleed_into_longer_word():
    # wafer + s 不得命中 wafersomething
    assert _count_term_occurrences("wafersort is a step", "wafer") == 0


# --- 单位/短缩写紧贴数字 ----------------------------------------------------


def test_unit_adjacent_to_digit_matches():
    text = "The 200MW campus and a 1.2GW cluster with 1400W parts in a 132kW rack."
    assert _count_term_occurrences(text, "MW") == 1
    assert _count_term_occurrences(text, "GW") == 1
    assert _count_term_occurrences(text, "kW") == 1


def test_short_acronym_adjacent_to_digit_matches():
    assert _count_term_occurrences("an 8GPU node", "GPU") == 1


def test_long_term_not_matched_inside_alphanumeric_run():
    # 只对 ≤4 字符的纯字母术语放开数字前瞻，长词仍需完整词边界
    assert _count_term_occurrences("5nanosheet", "nanosheet") == 0


# --- 非正文区掩码 -----------------------------------------------------------


def test_image_url_params_do_not_count_as_hits():
    url = "![](https://cdn.example.com/fetch/$s_!a!,w_1456,c_limit/x.png)"
    assert _count_term_occurrences(_prose_only(url), "W") == 0


def test_inline_code_and_fenced_code_are_masked():
    assert _count_term_occurrences(_prose_only("run `nvidia-smi -W`"), "W") == 0
    assert _count_term_occurrences(_prose_only("```\nW = 5\n```"), "W") == 0


def test_link_anchor_text_is_prose_but_target_is_not():
    masked = _prose_only("see [the HBM report](https://x.com/hbm-w-1456)")
    assert _count_term_occurrences(masked, "HBM") == 1


def test_masking_preserves_offsets():
    text = "![](https://x.com/a.png) tail"
    assert len(_prose_only(text)) == len(text)


# --- 选词的兜底语义 ---------------------------------------------------------


def test_image_only_paragraph_injects_nothing():
    # 掩码后为空 != 调用方没给原文。图片段不该被塞进任意 N 条术语。
    selected = select_prompt_terms_for_text(
        _terms(("HBM", "HBM"), ("wafer", "晶圆")),
        "![](https://cdn.example.com/a.png?w_1456)",
    )
    assert selected == []


def test_missing_source_still_falls_back_to_leading_terms():
    terms = _terms(("HBM", "HBM"), ("wafer", "晶圆"))
    assert len(select_prompt_terms_for_text(terms, None)) == 2
    assert len(select_prompt_terms_for_text(terms, "")) == 2


def test_prose_beside_image_only_matches_prose():
    selected = select_prompt_terms_for_text(
        _terms(("MW", "MW"), ("HBM", "HBM")),
        "The 200MW campus.\n\n![](https://cdn.example.com/a.png?w_1456)",
    )
    assert [item["original"] for item in selected] == ["MW"]
