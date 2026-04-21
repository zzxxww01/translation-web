from src.llm.usage_metrics import LLMUsageMetrics


def test_usage_metrics_reset_and_increment() -> None:
    metrics = LLMUsageMetrics()

    assert metrics.api_call_count() == 0
    assert metrics.increment_api_calls() == 1
    assert metrics.increment_api_calls() == 2

    metrics.reset()
    assert metrics.api_call_count() == 0
