# -*- coding: utf-8 -*-
"""短帖（社媒）词表注入：只统一用词写法，不灌长文括注规则。"""

from src.core.glossary_prompt import (
    SHORT_FORM_GLOSSARY_PROMPT_TITLE,
    render_glossary_prompt_block,
)


def _block(terms):
    return render_glossary_prompt_block(
        terms, title=SHORT_FORM_GLOSSARY_PROMPT_TITLE, short_form=True
    )


def test_first_annotate_does_not_demand_parenthetical_in_short_form():
    # 长文规则是「首次出现写"英伟达（NVIDIA）"」，一条 80 字的帖子里
    # 塞四五个英文括注会直接违背帖子提示词的"注释克制"。
    block = _block(
        [
            {"original": "NVIDIA", "translation": "英伟达", "strategy": "first_annotate"},
            {"original": "TSMC", "translation": "台积电", "strategy": "first_annotate"},
        ]
    )
    assert "（NVIDIA）" not in block
    assert "（TSMC）" not in block
    assert "首次出现写" not in block
    assert "直接使用该写法“英伟达”" in block
    assert "直接使用该写法“台积电”" in block


def test_short_form_title_does_not_claim_priority_over_prompt_rules():
    block = _block([{"original": "NVIDIA", "translation": "英伟达", "strategy": "translate"}])
    assert "必须优先遵守" not in block
    assert block.startswith(SHORT_FORM_GLOSSARY_PROMPT_TITLE)


def test_preserve_allows_first_use_expansion_when_note_has_chinese_name():
    block = _block(
        [
            {
                "original": "HBM",
                "translation": "HBM",
                "strategy": "preserve",
                "note": "高带宽内存 (High Bandwidth Memory)",
            }
        ]
    )
    # 允许首现展开，但用中文全称、不带英文全称。
    assert "高带宽内存（HBM）" in block
    assert "High Bandwidth Memory（HBM）" not in block
    assert "不加注释" not in block


def test_preserve_gives_no_expansion_hint_when_note_is_english_only():
    block = _block(
        [
            {
                "original": "CoWoS",
                "translation": "CoWoS",
                "strategy": "preserve",
                "note": "Chip on Wafer on Substrate",
            }
        ]
    )
    assert "Chip on Wafer on Substrate（CoWoS）" not in block
    assert "保留英文写法“CoWoS”" in block


def test_already_used_longform_wording_never_leaks_into_short_form():
    # already_used 分支说的"该术语已在前文完成首现括注"在单条帖子里毫无意义。
    block = render_glossary_prompt_block(
        [{"original": "NVIDIA", "translation": "英伟达", "strategy": "first_annotate"}],
        title=SHORT_FORM_GLOSSARY_PROMPT_TITLE,
        short_form=True,
        term_usage={"NVIDIA": ["s1"]},
    )
    assert "前文" not in block


def test_longform_rendering_is_unchanged():
    # 长文链路必须保持原样——short_form 默认关闭。
    block = render_glossary_prompt_block(
        [{"original": "NVIDIA", "translation": "英伟达", "strategy": "first_annotate"}]
    )
    assert "首次出现写“英伟达（NVIDIA）”" in block
    assert "必须优先遵守" in block
