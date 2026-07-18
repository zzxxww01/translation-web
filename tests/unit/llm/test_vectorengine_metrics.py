from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.llm.usage_metrics import LLMUsageMetrics
from src.llm.vectorengine import VectorEngineProvider


def _provider_with_response(response):
    provider = object.__new__(VectorEngineProvider)
    provider.default_model = "test-model"
    provider.temperature = 0.5
    provider.max_tokens = 1024
    provider.timeout = 30
    provider.max_retries = 0
    provider.client = Mock()
    provider.client.with_options.return_value.chat.completions.create.return_value = response
    return provider


def test_generate_records_successful_vectorengine_call(monkeypatch) -> None:
    metrics = LLMUsageMetrics()
    monkeypatch.setattr("src.llm.vectorengine.llm_usage_metrics", metrics)
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="translated"))],
        usage=SimpleNamespace(
            prompt_tokens=4,
            completion_tokens=2,
            total_tokens=6,
        ),
    )
    provider = _provider_with_response(response)

    assert provider.generate("source") == "translated"

    summary = metrics.summary()
    assert summary["api_calls"] == 1
    assert summary["failed_calls"] == 0
    assert summary["total_tokens"] == 6


def test_generate_records_failed_vectorengine_call(monkeypatch) -> None:
    metrics = LLMUsageMetrics()
    monkeypatch.setattr("src.llm.vectorengine.llm_usage_metrics", metrics)
    provider = _provider_with_response(None)
    provider.client.with_options.return_value.chat.completions.create.side_effect = RuntimeError(
        "upstream failed"
    )

    with pytest.raises(RuntimeError, match="upstream failed"):
        provider.generate("source")

    summary = metrics.summary()
    assert summary["api_calls"] == 1
    assert summary["failed_calls"] == 1
