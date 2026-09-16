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
        "全文主线", "段间：点明推进关系", "句内：交代措施与效果",
        "精简但不压缩逻辑", "不把时间先后擅自改成因果",
        "短评不强行扩成多段说明", "教学用虚构方案",
        "不补造原文没有的技术机制",
    ):
        assert requirement in prompt
    assert "译文不要比原文更长" not in prompt
