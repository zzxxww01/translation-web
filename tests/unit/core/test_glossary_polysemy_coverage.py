# -*- coding: utf-8 -*-
"""多义术语必须带**可迁移的判据**，且判据不能被注入上限截断。

这些词条原先是从单一题材的文章里就地取值的单义定义：transformer 只登记了
深度学习架构、Alignment 只登记了 AI 安全、Breakdown 只登记了标题语境。
换到 SemiAnalysis 的另一个常规题材（数据中心供电、共封装光学、器件可靠性、
财报分析）就会系统性误译，而 preserve 分支甚至根本不看【词义】栏。
"""

import json
from pathlib import Path

import pytest

from src.core.glossary_prompt import (
    MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT,
    render_glossary_prompt_block,
    select_prompt_terms_for_text,
)
from src.core.models import GlossaryTerm

GLOSSARY_PATH = Path(__file__).resolve().parents[3] / "glossary" / "global_glossary_semi.json"

# 这些词在 SemiAnalysis 的多个常规题材里都有完全不同的义项
POLYSEMOUS = [
    "transformer",
    "Alignment",
    "Breakdown",
    "harness",
    "rollout",
    "the street",
    "benchmark",
    "Grounding",
    "Embedding",
    "unwind",
]


@pytest.fixture(scope="module")
def terms():
    raw = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    return [GlossaryTerm(**item) for item in raw["terms"]]


@pytest.fixture(scope="module")
def by_original(terms):
    return {term.original: term for term in terms}


@pytest.mark.parametrize("original", POLYSEMOUS)
def test_polysemous_term_offers_candidates(by_original, original):
    term = by_original.get(original)
    assert term is not None, f"{original} 不在全局词表里"
    assert term.translation and "/" in term.translation, (
        f"{original} 仍是单义写法，换题材会被一刀切"
    )


@pytest.mark.parametrize("original", POLYSEMOUS)
def test_polysemous_term_is_not_preserve(by_original, original):
    # preserve 分支直接返回「保留英文原文，不加注释」，根本不看【词义】栏，
    # 判据写得再好也送不到模型。
    term = by_original.get(original)
    assert term.strategy.value if hasattr(term.strategy, "value") else term.strategy
    strategy = getattr(term.strategy, "value", term.strategy)
    assert strategy != "preserve", f"{original} 是 preserve，判据不会被注入"


@pytest.mark.parametrize("original", POLYSEMOUS)
def test_polysemous_term_has_actionable_criteria(by_original, original):
    note = by_original[original].note or ""
    assert note, f"{original} 没有词义说明"
    assert "依语境选择" not in note, (
        f"{original} 的说明是自我循环的「依语境选择」，等于没有判据"
    )
    # 判据要能落到具体线索上，而不是空泛描述
    assert "→" in note or "判据" in note, f"{original} 的说明缺少可执行判据"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("A medium-voltage transformer feeds each row from the 230kV substation.", "transformer"),
        ("Passive alignment of the fiber lowers the cost of the optical connector.", "Alignment"),
        ("GaN devices have a higher breakdown voltage than silicon.", "Breakdown"),
        ("Each rack ships with a copper cable harness.", "harness"),
        ("Traders had to unwind positions after the print.", "unwind"),
    ],
)
def test_new_domain_text_gets_polysemous_guidance(terms, text, expected):
    selected = select_prompt_terms_for_text(terms, text)
    assert expected in [item.original for item in selected], f"{expected} 未命中"
    block = render_glossary_prompt_block(selected) or ""
    line = next(line for line in block.split("\n") if expected in line)
    assert "多义词" in line, f"{expected} 没有触发判义指令：{line}"


def test_note_cap_keeps_criteria_intact(by_original):
    # 判据被从中间截断后，模型看到的是半句映射表加省略号，等价于没有判据
    for original in POLYSEMOUS:
        note = by_original[original].note or ""
        assert len(note) <= MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT, (
            f"{original} 的判据 {len(note)} 字，超过注入上限 "
            f"{MAX_GLOSSARY_NOTE_CHARS_IN_PROMPT} 会被截断"
        )
