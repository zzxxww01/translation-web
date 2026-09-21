"""Malformed input must fail visibly rather than look like successful work."""
import json
from unittest.mock import Mock

import pytest

from src.api.middleware.upload_limit import LimitUploadSize
from src.api.utils.json_utils import parse_title_json_response
from src.core.file_utils import atomic_write_with_retry
from src.prompts.contracts import PromptContractError, parse_json


@pytest.mark.parametrize('response', [
    '{"issues":[]}}', '{"issues":[]} ]', '{"issues":[]}, "score":',
    '```json\n{"issues": []}', '[{"issues":[]}],',
])
def test_incomplete_or_extra_json_delimiters_are_not_a_complete_review(response):
    with pytest.raises(PromptContractError):
        parse_json(response)


def test_valid_prose_wrapped_json_still_supported():
    assert parse_json('结果如下：\n{"issues":[]}\n以上。') == {'issues': []}
    assert parse_json('note: {"text":"literal } brace"} done') == {'text': 'literal } brace'}


@pytest.mark.parametrize('response', [
    '{"minimal":"A", "minimal":"B"}',
    '{"minimal":"A", "score":NaN}',
    '{"minimal":"A", "score":1e9999}',
])
def test_title_compatibility_does_not_accept_duplicate_or_nonfinite_json(response):
    assert parse_title_json_response(response) == {}


@pytest.mark.parametrize('attempts', [0, -1, True, 1.5])
def test_invalid_atomic_retry_budget_never_reports_success(tmp_path, attempts):
    path = tmp_path / 'record.json'
    path.write_text('original')
    write = Mock(side_effect=lambda p: p.write_text('new'))
    with pytest.raises(ValueError):
        atomic_write_with_retry(path, write, max_attempts=attempts)
    assert path.read_text() == 'original'
    write.assert_not_called()


@pytest.mark.parametrize('delay', [-1, float('nan'), float('inf')])
def test_invalid_atomic_retry_delay_is_rejected_before_writing(tmp_path, delay):
    write = Mock()
    with pytest.raises(ValueError):
        atomic_write_with_retry(tmp_path / 'file', write, retry_delay_base=delay)
    write.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('digits, expected', [(b'9'*5000, 413), (b'0'*5000+b'1', 200)], ids=['huge-number', 'leading-zeroes'])
async def test_large_decimal_content_length_does_not_raise_int_conversion_error(digits, expected):
    sent = []
    async def endpoint(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'ok'})
    async def receive():
        return {'type':'http.request','body':b'x','more_body':False}
    async def send(message):
        sent.append(message)
    scope = {'type':'http', 'method':'POST', 'path':'/upload', 'headers': [(b'content-length',digits)]}
    await LimitUploadSize(endpoint, max_request_size=10)(scope, receive, send)
    assert sent[0]['status'] == expected
