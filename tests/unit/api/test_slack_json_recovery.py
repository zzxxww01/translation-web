"""Slack 回复接口对"中转把 JSON 换行写进字符串/键名"的回归测试。

真实故障：relay 返回的 JSON 里字符串内含未转义换行，键名也被拆断
（``"english\\n"``、``"\\nversion"``）。旧解析器严格解析失败返回 {}，
接口仍回 200 + 空字段，CLI 侧表现为"未返回有效的英文回复"。
"""
from unittest.mock import AsyncMock

import pytest

from src.api.routers import slack_compose, slack_process, slack_sync_optimize
from src.api.routers.slack_models import (
    SlackComposeRequest,
    SlackOptimizeRequest,
    SlackProcessRequest,
)
from src.api.utils.json_utils import (
    normalize_control_keys,
    parse_llm_json_response,
    unwrap_relay_lines,
)

# 与真实中转响应同形状：换行落在字符串内部，并拆开若干键名。
RELAY_WRAPPED = '''{
  "translation": "你能看一下最新的
报告，告诉我里面的数据和我们讨论的是否一致吗？",
  "suggested_replies": [

    {
      "version": "A",
      "english": "Sure, I'll take a
 look now and ping you if anything looks off.",
      "chinese": "没问题，我现在就看。"
    },
    {
      "version": "B",
      "english
": "Will do. I'll check the numbers and get back to you."
    },
    {
      "
version": "C",
      "english": "I'll review the report today and confirm if the numbers match
 our discussion."
    }
  ]
}
'''

REPLY_KEYS = ("translation", "suggested_replies", "version", "english", "chinese", "style")


def test_wrapped_json_is_recovered_without_inventing_content():
    data = normalize_control_keys(parse_llm_json_response(RELAY_WRAPPED), REPLY_KEYS)

    assert data["translation"].startswith("你能看一下最新的")
    replies = data["suggested_replies"]
    assert [item["version"] for item in replies] == ["A", "B", "C"]
    assert all(item["english"].strip() for item in replies)
    # 只做键名修复与容错解析，正文内容原样保留。
    assert "look now and ping you" in replies[0]["english"]


def test_unknown_keys_are_left_untouched():
    assert normalize_control_keys({"custom\nkey": 1}, REPLY_KEYS) == {"custom\nkey": 1}


def test_relay_line_breaks_are_joined_without_inventing_spaces():
    assert unwrap_relay_lines("I'll take\n a look") == "I'll take a look"
    assert unwrap_relay_lines("你可以看\n，然后回我") == "你可以看，然后回我"
    assert unwrap_relay_lines("with you\n.") == "with you."
    assert unwrap_relay_lines("单行内容") == "单行内容"


def test_broken_json_is_still_rejected():
    assert parse_llm_json_response('{"translation": "x", "suggested_replies": [') == {}
    assert parse_llm_json_response("this is not json") == {}


@pytest.mark.asyncio
async def test_slack_process_recovers_wrapped_response(monkeypatch):
    monkeypatch.setattr(slack_process.prompt_manager, "get", lambda *_a, **_k: "rendered")
    monkeypatch.setattr(
        slack_process, "generate_with_fallback_budget", AsyncMock(return_value=RELAY_WRAPPED)
    )

    response = await slack_process.process_slack_message.__wrapped__(None, SlackProcessRequest(message="hi"))  # type: ignore[attr-defined]

    assert response.translation
    assert all(variant.english.strip() for variant in response.suggested_replies)
    # 折行拼接后不应再有裸换行
    assert "\n" not in response.translation
    assert all("\n" not in variant.english for variant in response.suggested_replies)


@pytest.mark.asyncio
async def test_slack_process_fails_loudly_on_unusable_response(monkeypatch):
    monkeypatch.setattr(slack_process.prompt_manager, "get", lambda *_a, **_k: "rendered")
    monkeypatch.setattr(
        slack_process, "generate_with_fallback_budget", AsyncMock(return_value="plain text, no json")
    )

    with pytest.raises(Exception) as excinfo:
        await slack_process.process_slack_message.__wrapped__(None, SlackProcessRequest(message="hi"))  # type: ignore[attr-defined]

    assert getattr(excinfo.value, "error_code", None) == "LLM_EMPTY_RESPONSE"


@pytest.mark.asyncio
async def test_slack_compose_fails_loudly_on_unusable_response(monkeypatch):
    monkeypatch.setattr(slack_compose.prompt_manager, "get", lambda *_a, **_k: "rendered")
    monkeypatch.setattr(
        slack_compose, "generate_with_fallback_budget", AsyncMock(return_value="{}")
    )

    with pytest.raises(Exception) as excinfo:
        await slack_compose.compose_slack_message.__wrapped__(None, SlackComposeRequest(content="今晚发给你"))  # type: ignore[attr-defined]

    assert getattr(excinfo.value, "error_code", None) == "LLM_EMPTY_RESPONSE"


@pytest.mark.asyncio
async def test_slack_optimize_does_not_pass_original_text_as_result(monkeypatch):
    monkeypatch.setattr(slack_sync_optimize.prompt_manager, "get", lambda *_a, **_k: "rendered")
    monkeypatch.setattr(
        slack_sync_optimize, "generate_with_fallback_budget", AsyncMock(return_value="not json")
    )

    with pytest.raises(Exception) as excinfo:
        await slack_sync_optimize.optimize_text(
            SlackOptimizeRequest(
                content="Original text", target_language="en", context_type="tone"
            )
        )

    assert getattr(excinfo.value, "error_code", None) == "LLM_EMPTY_RESPONSE"
    assert "Original text" not in str(excinfo.value)
