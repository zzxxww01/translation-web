from __future__ import annotations

from threading import Lock


class LLMUsageMetrics:
    """Process-local counters for lightweight LLM run diagnostics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._api_call_count = 0

    def reset(self) -> None:
        with self._lock:
            self._api_call_count = 0

    def increment_api_calls(self) -> int:
        with self._lock:
            self._api_call_count += 1
            return self._api_call_count

    def api_call_count(self) -> int:
        with self._lock:
            return self._api_call_count


llm_usage_metrics = LLMUsageMetrics()
