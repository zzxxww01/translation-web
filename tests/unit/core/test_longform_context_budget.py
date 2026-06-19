"""回归测试：上下文预算从纯条数收口扩展到字符量（finding 40）。"""

from src.core.longform_context import (
    build_translation_guidelines,
    limit_non_empty_strings,
)


def test_backward_compatible_count_only():
    items = ["a", "b", "c", "d"]
    assert limit_non_empty_strings(items, 2) == ["a", "b"]


def test_skips_empty_and_strips():
    assert limit_non_empty_strings(["  x  ", "", "   ", "y"], 10) == ["x", "y"]


def test_per_item_char_cap_truncates():
    long_item = "甲" * 500
    out = limit_non_empty_strings([long_item], 10, max_chars_per_item=100)
    assert len(out) == 1
    assert len(out[0]) == 100  # 99 chars + 省略号
    assert out[0].endswith("…")


def test_total_char_cap_stops_accumulation():
    items = ["x" * 300, "y" * 300, "z" * 300]
    out = limit_non_empty_strings(items, 10, max_total_chars=650)
    # 300 + 300 = 600 <= 650 ok；再加 300 -> 900 > 650 停止
    assert out == [items[0], items[1]]


def test_build_guidelines_applies_caps():
    huge = "指南" * 1000
    out = build_translation_guidelines([huge, "短指南"])
    # 单条被截断到上限以内
    assert all(len(g) <= 240 for g in out)
