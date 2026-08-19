# -*- coding: utf-8 -*-
"""词表必须覆盖 SemiAnalysis 的全部常规题材，而不只是已翻过的那十几篇。

此前 245 条全局词表是「翻过的文章的残留物」：光互连 0/45、光刻设备 0/37、
供电散热 1/40、财报 0/36 全空——一篇 CPO 或电力文章拿到的术语约束里全是
NVIDIA/GPU/AI 这类模型本来就不会错的词，真正有理解门槛的一条都不在。

用**语料外**的题材段落做端到端命中检查，防止覆盖面再退回去。
"""

import json
from pathlib import Path

import pytest

from src.core.glossary_prompt import select_prompt_terms_for_text
from src.core.models import GlossaryTerm

GLOSSARY_PATH = Path(__file__).resolve().parents[3] / "glossary" / "global_glossary_semi.json"


@pytest.fixture(scope="module")
def terms():
    raw = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    return [GlossaryTerm(**item) for item in raw["terms"]]


# 每段都是语料里没有的、SemiAnalysis 风格的新题材原文
DOMAIN_SAMPLES = {
    "光互连": (
        "Co-packaged optics moves the optical engine next to the switch ASIC. "
        "Linear drive removes the DSP, and OSFP transceivers give way to CPO. "
        "SerDes lanes run 224G PAM4 over silicon photonics; retimers handle reach."
    ),
    "光刻设备": (
        "High-NA EUV needs new pellicles and a smaller reticle field. Overlay budgets "
        "tighten as GAA nanosheet replaces FinFET. WFE spending and metrology rise; "
        "photoresist suppliers benefit."
    ),
    "供电散热": (
        "The substation feeds a busbar through switchgear; UPS and BBU carry the "
        "ride-through until the genset starts. Cold plates and CDUs cut PUE. The "
        "interconnection queue and capacity auction set the timeline."
    ),
    "财报": (
        "Guidance implies gross margin expands 240 basis points, and operating leverage "
        "lifts FCF. RPO grew while book-to-bill stayed above one. Non-GAAP excludes SBC; "
        "management targets a 20% CAGR."
    ),
    "推理经济学": (
        "MoE routing plus expert parallel and tensor parallel shrinks TTFT, while "
        "speculative decoding cuts TPOT. FP8 and FP4 halve the KV cache, letting batch "
        "size and context length grow."
    ),
    "先进封装": (
        "Hybrid bonding replaces microbumps; TSVs and RDLs route onto an ABF substrate. "
        "SoIC, EMIB and Foveros compete, UCIe standardizes the die-to-die link. Warpage "
        "and underfill limit yield; backside power delivery arrives next node."
    ),
    "存储": (
        "HBM4 stacks lift layer count. LPDDR6 and DDR5 ASPs rise as bit growth outpaces "
        "wafer starts; 3D NAND shifts from TLC to QLC. JEDEC timing and CXL pooling "
        "reshape demand."
    ),
}

MIN_HITS = 8


@pytest.mark.parametrize("domain", sorted(DOMAIN_SAMPLES))
def test_domain_sample_gets_enough_terminology(terms, domain):
    hits = select_prompt_terms_for_text(terms, DOMAIN_SAMPLES[domain])
    assert len(hits) >= MIN_HITS, (
        f"{domain} 只命中 {len(hits)} 条术语（要求 ≥{MIN_HITS}）："
        f"{[item.original for item in hits]}"
    )


def test_no_duplicate_originals(terms):
    seen = {}
    for term in terms:
        key = term.original.strip().lower()
        assert key not in seen, f"重复词条：{term.original}"
        seen[key] = term


def test_non_preserve_terms_have_translation(terms):
    for term in terms:
        strategy = getattr(term.strategy, "value", term.strategy)
        if strategy != "preserve":
            assert (term.translation or "").strip(), (
                f"{term.original} 策略是 {strategy} 却没有译文"
            )


def test_domain_tags_are_balanced(terms):
    # 覆盖面偏斜会让某些题材的文章拿不到任何有用约束
    counts = {}
    for term in terms:
        for tag in term.tags or []:
            counts[tag] = counts.get(tag, 0) + 1
    for tag in ("optics", "packaging", "memory", "power", "litho", "finance"):
        assert counts.get(tag, 0) >= 10, f"题材 {tag} 只有 {counts.get(tag, 0)} 条"
