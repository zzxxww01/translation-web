"""Conservative recovery of control characters in LLM JSON objects."""

import json

import pytest

from src.api.utils.json_utils import parse_title_json_response as parse_llm_json_response


@pytest.mark.parametrize("control", [chr(code) for code in range(32)])
def test_unescaped_control_character_is_preserved(control):
    response = '{"title":"第一行' + control + '第二行","body":"  原文  "}'
    assert parse_llm_json_response(response) == {
        "title": "第一行" + control + "第二行", "body": "  原文  "
    }


def test_valid_escapes_and_content_are_unchanged():
    expected = {
        "title": "第一行\n第二行",
        "body": '  space\tCR\r\nquote" slash\\ literal\\n ```json\n{}\n```  ',
        "nested": {"items": [True, None, 3]},
    }
    assert parse_llm_json_response(json.dumps(expected)) == expected


@pytest.mark.parametrize("fence", ["```json", "```"])
@pytest.mark.parametrize("raw_newline", [False, True])
def test_complete_markdown_fence(fence, raw_newline):
    text = '{"title":"first\\nsecond"}'
    if raw_newline:
        text = text.replace("\\n", "\n")
    assert parse_llm_json_response(f"{fence}\n{text}\n```") == {
        "title": "first\nsecond"
    }


@pytest.mark.parametrize("text", [
    '[]', '[1]', '[{"title":"not an object response"}]',
    '"plain text"', '"{}"', '42', 'true', 'false', 'null',
])
def test_non_object_returns_empty_dict(text):
    assert parse_llm_json_response(text) == {}


@pytest.mark.parametrize("text", [
    '', '{"title":"unfinished', '{"title":"first\nsecond',
    '{"nested":{"ok":true}',
    '{"title":"complete"}, "body":"unfinished',
    '```json\n{"title":"complete"}',
    '{"title":"bad",}', "{'title':'bad'}",
    '{"title":"bad\\q"}', '{"title":"bad\\u123"}',
    '{"title":"bad\nvalue",}', '{"title":"unescaped "quote""}',
    '{"title":\x00"bad"}', '{"title":"ok"} {"extra":1}',
    '{"title":"ok"} trailing',
])
def test_truncated_or_other_invalid_syntax_is_not_repaired(text):
    assert parse_llm_json_response(text) == {}
