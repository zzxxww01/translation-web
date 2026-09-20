import json
import pytest
from src.api.routers.translate_posts import _extract_titles

@pytest.mark.parametrize('text,expected', [
    ('工具调用偏\n好','工具调用偏好'),
    ('平均1\n.94次','平均1.94次'),
    ('平均1.\n94次','平均1.94次'),
    ('Google\nCloud工具调用','Google Cloud工具调用'),
    ('6\n1万条对话','61万条对话'),
    ('数字6 1保持空格','数字6 1保持空格'),
])
def test_title_line_wrap_does_not_split_words_or_decimal(text, expected):
    assert _extract_titles(json.dumps({'minimal':text})) == [expected]
