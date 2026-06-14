"""回归测试：tokenize_text 偏移一致性校验（finding 44）。

偏移漂移（start/end 与实际文本不符）时，不再静默把 token 插到错误位置导致译文错乱，
而是跳过该 token；正常偏移行为保持不变。
"""

from src.core.format_tokens import tokenize_text, strip_token_markup
from src.core.models import InlineElement


def _el(type_, text, start, end, span_id=None):
    return InlineElement(type=type_, text=text, start=start, end=end, span_id=span_id)


def test_normal_offsets_tokenized_correctly():
    text = "see foo and bar here"
    # "foo" at 4:7, "bar" at 12:15
    elements = [
        _el("link", "foo", 4, 7, "LINK_1"),
        _el("strong", "bar", 12, 15, "STRONG_1"),
    ]
    out = tokenize_text(text, elements)
    assert "[[[LINK_1|foo]]]" in out
    assert "[[[STRONG_1|bar]]]" in out
    # 去标记后还原为原文
    assert strip_token_markup(out) == text


def test_drifted_offset_is_skipped_not_corrupted():
    text = "see foo and bar here"
    # 第二个元素偏移错位：start/end 指向 "and"，但 text 期望 "bar"
    elements = [
        _el("link", "foo", 4, 7, "LINK_1"),
        _el("strong", "bar", 8, 11, "STRONG_1"),  # drift: text[8:11] == "and"
    ]
    out = tokenize_text(text, elements)
    # 正确偏移的 token 仍被插入
    assert "[[[LINK_1|foo]]]" in out
    # 漂移的 token 被跳过，不会把 "and" 错当 "bar" 包进 token
    assert "STRONG_1" not in out
    # 文本未被错位破坏：去标记后仍等于原文
    assert strip_token_markup(out) == text


def test_no_elements_returns_text_unchanged():
    assert tokenize_text("plain text", []) == "plain text"
    assert tokenize_text("plain text", None) == "plain text"
