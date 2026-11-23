import pytest

from src.llm.errors import LLMDeadlineExceededError, normalize_llm_transport_error
from src.llm.gemini import _transport_timeout_ms


def test_transport_timeout_uses_ratio_when_above_gemini_minimum():
    assert _transport_timeout_ms(60) == 54_000


def test_transport_timeout_is_raised_to_gemini_minimum_when_budget_allows():
    # 0.9 * 10.5s = 9.45s would be rejected by Gemini with 400 INVALID_ARGUMENT.
    assert _transport_timeout_ms(10.5) == 10_000
    assert _transport_timeout_ms(10) == 10_000


def test_transport_timeout_fails_fast_when_budget_is_below_gemini_minimum():
    with pytest.raises(LLMDeadlineExceededError) as caught:
        _transport_timeout_ms(7)

    normalized = normalize_llm_transport_error(caught.value, provider_name="Gemini")
    assert normalized is not None and normalized.retryable is False
