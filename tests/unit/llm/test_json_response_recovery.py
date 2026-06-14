"""回归测试：_parse_json_response 容错恢复。

此前解析失败静默返回 {}，把被 max_output_tokens 截断或含赘述的输出悄悄丢弃。
现在先尝试从文本中提取平衡的 JSON 子串恢复，仍失败才返回 {}（并记 warning）。
"""

from src.llm.base import LLMProvider


class _Parser(LLMProvider):
    """仅用于测试基类解析逻辑的最小实现（实现全部抽象方法占位）。"""

    def __init__(self):
        # 跳过基类 __init__（其依赖 prompt manager），仅测试纯解析方法
        pass

    def translate(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    def analyze(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    def deep_analyze_document(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    def verify_high_frequency_terms(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    def check_consistency(self, *a, **k):  # pragma: no cover
        raise NotImplementedError

    def generate(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def test_plain_json():
    p = _Parser()
    assert p._parse_json_response('{"a": 1}') == {"a": 1}


def test_fenced_json():
    p = _Parser()
    assert p._parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_recovers_from_leading_and_trailing_prose():
    p = _Parser()
    text = '好的，结果如下：\n{"theme": "x", "terms": [1, 2]}\n以上。'
    assert p._parse_json_response(text) == {"theme": "x", "terms": [1, 2]}


def test_recovers_balanced_object_ignoring_trailing_garbage():
    p = _Parser()
    # 末尾被截断的第二个对象应被忽略，首个完整对象被恢复
    text = '{"a": {"b": 1}} {"c": '
    assert p._parse_json_response(text) == {"a": {"b": 1}}


def test_brace_inside_string_not_miscounted():
    p = _Parser()
    text = 'note: {"k": "value with } brace"} done'
    assert p._parse_json_response(text) == {"k": "value with } brace"}


def test_unrecoverable_returns_empty_dict():
    p = _Parser()
    assert p._parse_json_response("completely not json at all") == {}
    assert p._parse_json_response("") == {}
