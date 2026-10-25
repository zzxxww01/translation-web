"""Section titles have a hard 20-codepoint limit: over-long ones get exactly one rewrite."""
import json
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from src.llm.base import LLMProvider, SECTION_TITLE_MAX_LENGTH, section_title_length

LONG = "劳动力自动化、RL 即服务、Anthropic 的下一步大棋与平台政治"
SECTIONS = [{"id": "s1", "title": "Will the Pretrain Matter?"},
            {"id": "s2", "title": "Worker Automation, RL as a Service, Anthropic's next big bet, Platform Politics"}]


def provider(*responses):
    stub = SimpleNamespace(generate=Mock(side_effect=[json.dumps({"translations": r}, ensure_ascii=False) for r in responses]))
    stub._shorten_section_titles = MethodType(LLMProvider._shorten_section_titles, stub)
    return stub


def test_spaces_do_not_count_toward_the_limit():
    # export inserts CJK–Latin spaces anyway; counting them would push the model to drop them
    assert section_title_length("SerDes 扩展见顶阻碍 NVLink 扩展") == section_title_length("SerDes扩展见顶阻碍NVLink扩展") == 20


def test_over_long_title_is_rewritten_once():
    assert section_title_length(LONG) > SECTION_TITLE_MAX_LENGTH
    stub = provider({"s1": "预训练还重要吗？", "s2": LONG}, {"s2": "劳动力自动化等五大议题"})
    result = LLMProvider.translate_all_section_titles(stub, SECTIONS)
    assert result == {"s1": "预训练还重要吗？", "s2": "劳动力自动化等五大议题"}
    assert stub.generate.call_count == 2
    rewrite_prompt = stub.generate.call_args.args[0]
    assert "长度纠错" in rewrite_prompt and LONG in rewrite_prompt
    assert "Will the Pretrain Matter?" not in rewrite_prompt  # only the over-long title is resent


def test_rewrite_that_is_not_shorter_is_ignored():
    stub = provider({"s1": "预训练还重要吗？", "s2": LONG}, {"s2": LONG + "补充"})
    assert LLMProvider.translate_all_section_titles(stub, SECTIONS)["s2"] == LONG


def test_titles_within_limit_need_no_extra_call():
    stub = provider({"s1": "预训练还重要吗？", "s2": "劳动力自动化与 RL 即服务"})
    LLMProvider.translate_all_section_titles(stub, SECTIONS)
    assert stub.generate.call_count == 1
