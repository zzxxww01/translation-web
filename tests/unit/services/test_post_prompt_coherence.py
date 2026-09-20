"""Structural guards; live translation quality still requires human review."""
from src.prompts import PromptManager


def test_post_prompt_renders_source_and_glossary():
    prompt = PromptManager().get(
        "post_translation", text="SOURCE {literal}", dynamic_sections="GLOSSARY_SENTINEL"
    )
    assert "SOURCE {literal}" in prompt
    assert "GLOSSARY_SENTINEL" in prompt
    assert "{dynamic_sections}" not in prompt
    assert "{text}" not in prompt


def test_post_prompt_prioritizes_discourse_without_inventing_relations():
    prompt = PromptManager().get("post_translation")
    for requirement in (
        "不规定每句字数", "不强制一句一事", "连接词就删", "普通动作或变化",
        "不能把并列或时间先后写成因果", "不是为短而短", "不能补造机制",
        "真正表达处置", "同一复句", "按完整语义单位决定拆合",
    ):
        assert requirement in prompt
    assert "译文不要比原文更长" not in prompt
