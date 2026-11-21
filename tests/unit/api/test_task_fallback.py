"""Task-level whole-request fallback (task_fallbacks) for default-model calls."""
import pytest

from src.api.utils import llm_factory
from src.llm.errors import LLMUpstreamUnavailableError


class FakeAdapter:
    def __init__(self, alias, calls, fail):
        self.alias, self.calls, self.fail = alias, calls, fail

    def generate_with_fallback(self, prompt, timeout, **kwargs):
        self.calls.append(self.alias)
        if self.fail:
            raise LLMUpstreamUnavailableError(f"{self.alias} down")
        kwargs["result_metadata"].update(model_used=self.alias, fallback_used=False)
        return f"from {self.alias}"


@pytest.fixture
def routes(monkeypatch):
    calls, failing = [], set()
    monkeypatch.setattr(llm_factory, "get_task_model_alias", lambda task: "gpt-6.2-sol")
    monkeypatch.setattr(llm_factory, "get_task_fallback_alias",
                        lambda task: "gemini-flash" if task == "post" else None)
    monkeypatch.setattr(llm_factory, "get_provider_adapter",
                        lambda alias: FakeAdapter(alias, calls, alias in failing))
    return calls, failing


def test_default_model_failure_falls_back_to_task_fallback(routes):
    calls, failing = routes
    failing.add("gpt-6.2-sol")
    meta = {}
    assert llm_factory.generate_with_fallback("p", task_type="post", result_metadata=meta) == "from gemini-flash"
    assert calls == ["gpt-6.2-sol", "gemini-flash"]
    assert meta == {"model_used": "gemini-flash", "fallback_used": True}


def test_default_model_success_skips_fallback(routes):
    calls, _ = routes
    assert llm_factory.generate_with_fallback("p", task_type="post", result_metadata={}) == "from gpt-6.2-sol"
    assert calls == ["gpt-6.2-sol"]


def test_explicit_model_never_uses_task_fallback(routes):
    calls, failing = routes
    failing.add("gpt-6.2-sol")
    with pytest.raises(LLMUpstreamUnavailableError):
        llm_factory.generate_with_fallback("p", task_type="post", model="gpt-6.2-sol", result_metadata={})
    assert calls == ["gpt-6.2-sol"]


def test_task_without_fallback_reraises(routes):
    calls, failing = routes
    failing.add("gpt-6.2-sol")
    with pytest.raises(LLMUpstreamUnavailableError):
        llm_factory.generate_with_fallback("p", task_type="slack", result_metadata={})
    assert calls == ["gpt-6.2-sol"]
