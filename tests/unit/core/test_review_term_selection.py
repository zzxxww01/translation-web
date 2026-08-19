# -*- coding: utf-8 -*-
"""反思/精修阶段的选词必须按出错风险排序，而不是按词频。

直接复用 select_prompt_terms_for_text 时排序是「出现次数降序」，截断后留下的是
AI／GPU／NVIDIA 这类高频词——恰恰是模型绝不会译错的。真正需要审校盯住的是低频
难词：多义词有没有选对义项、preserve 词条有没有被硬译、首现括注纪律有没有守住。
实测 306 个章节里 51.3% 命中数超过上限，最多一章命中 51 条。
"""

import pytest

from src.core.glossary_prompt import (
    select_prompt_terms_for_text,
    select_review_terms_for_text,
)


def _t(original, translation, strategy="translate", note=""):
    return {
        "original": original,
        "translation": translation,
        "strategy": strategy,
        "note": note,
    }


# 高频单义词 vs 低频高风险词
TERMS = [
    _t("GPU", "GPU", "preserve"),                                  # 高频，preserve
    _t("bandwidth", "带宽"),                                        # 高频单义
    _t("performance", "性能"),                                      # 高频单义
    _t("memory", "显存/内存/存储", note="判据：这块 memory 在卡上还是在主机上"),  # 低频多义
    _t("yield", "良率(制造)/收益率(金融)", note="制造=良率；金融=收益率"),        # 低频多义
    _t("Trainium", "Trainium", "preserve"),                        # 低频 preserve
    _t("co-packaged optics", "共封装光学", "first_annotate"),        # 低频括注
]

# 高频词各出现多次，多义词只出现一次
TEXT = (
    "The GPU bandwidth and GPU performance dominate. GPU bandwidth again, "
    "performance again, bandwidth again. "
    "Memory placement matters, yield improved, Trainium shipped, "
    "and co-packaged optics arrived."
)


def test_frequency_ranking_drops_the_hard_terms():
    # 这是修复前的行为，作为对照钉住：按词频取前 3 全是高频单义词
    picked = [t["original"] for t in select_prompt_terms_for_text(TERMS, TEXT, max_terms=3)]
    assert "memory" not in picked
    assert "yield" not in picked


def test_review_ranking_puts_polysemous_first():
    picked = [t["original"] for t in select_review_terms_for_text(TERMS, TEXT, max_terms=3)]
    assert "memory" in picked, f"多义词没被优先：{picked}"
    assert "yield" in picked, f"多义词没被优先：{picked}"


def test_preserve_outranks_plain_single_sense():
    # 不设上限时看相对顺序：preserve 词条排在高频单义词之前
    picked = [t["original"] for t in select_review_terms_for_text(TERMS, TEXT, max_terms=99)]
    assert picked.index("Trainium") < picked.index("bandwidth")


def test_low_frequency_risk_terms_survive_a_tight_cap():
    # 名额紧张时，让位的应该是高频单义词而不是低频难词
    picked = [t["original"] for t in select_review_terms_for_text(TERMS, TEXT, max_terms=5)]
    assert "bandwidth" not in picked and "performance" not in picked
    assert {"memory", "yield", "Trainium"} <= set(picked)


def test_annotate_strategy_outranks_plain_single_sense():
    picked = [t["original"] for t in select_review_terms_for_text(TERMS, TEXT, max_terms=99)]
    assert picked.index("co-packaged optics") < picked.index("bandwidth")


def test_same_risk_class_keeps_frequency_order():
    # 同档内不打乱原有的词频顺序
    picked = [t["original"] for t in select_review_terms_for_text(TERMS, TEXT, max_terms=99)]
    assert picked.index("bandwidth") < picked.index("performance") or \
        picked.index("performance") < picked.index("bandwidth")
    # 两个多义词都排在所有单义词之前
    plain = [p for p in picked if p in ("bandwidth", "performance")]
    poly = [p for p in picked if p in ("memory", "yield")]
    assert max(picked.index(x) for x in poly) < min(picked.index(x) for x in plain)


def test_cap_is_respected():
    assert len(select_review_terms_for_text(TERMS, TEXT, max_terms=2)) == 2
    assert len(select_review_terms_for_text(TERMS, TEXT, max_terms=0)) == 0


def test_no_hits_returns_empty():
    assert select_review_terms_for_text(TERMS, "完全无关的中文段落。", max_terms=10) == []


def test_missing_source_falls_back_without_crashing():
    assert isinstance(select_review_terms_for_text(TERMS, None, max_terms=5), list)
