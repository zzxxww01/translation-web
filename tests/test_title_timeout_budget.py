"""Exercise title -> factory -> real adapter budgets with a virtual clock only."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from src.api.middleware.error_handlers import ServiceUnavailableException
from src.api.routers import translate_posts as posts
from src.api.routers.translate_models import GenerateTitleRequest
from src.api.utils import llm_factory
from src.llm import execution_context as ec
from src.llm.errors import LLMTimeoutError
from src.llm.provider_adapter import ProviderAdapter


@pytest.fixture
def title_harness(monkeypatch):
    now = [1000.0]
    # Replace module references, not process-wide time / the running event loop.
    clock = NS(monotonic=lambda: now[0], sleep=lambda seconds: now.__setitem__(0, now[0] + seconds))
    monkeypatch.setattr(ec, "time", clock)
    monkeypatch.setattr(posts, "asyncio", NS(
        get_running_loop=lambda: NS(time=clock.monotonic),
        wait_for=asyncio.wait_for, TimeoutError=asyncio.TimeoutError,
    ))
    async def inline(func, *args, **kwargs):
        return func(*args, **kwargs)
    monkeypatch.setattr(posts, "run_llm_blocking", inline)
    monkeypatch.setattr(posts.limiter, "enabled", False)
    monkeypatch.setattr(posts.prompt_manager, "get", lambda *a, **kw: "source prompt")
    obj = ProviderAdapter.__new__(ProviderAdapter)
    obj.model_alias = "test-title"
    obj.attempt_plan = [NS(
        provider=NS(provider_id="test-title", type="vectorengine"),
        model=NS(alias="test-title", real_model="test-real", config={"timeout": 120}),
        api_key=NS(name="fixture", key="fixture"),
    )]
    transport = Mock()
    obj.create_provider = Mock(return_value=transport)
    monkeypatch.setattr(llm_factory, "get_provider_adapter", lambda alias: obj)
    request = Request({"type": "http", "method": "POST", "path": "/api/generate/title",
                       "headers": [], "client": ("budget-test", 50000)})
    async def call():
        return await posts.generate_title(request, GenerateTitleRequest(content="source", model="test-title"))
    return now, transport, call


async def test_full_attempt_timeout_leaves_budget_for_fallback_and_rewrite(title_harness):
    now, transport, call = title_harness
    timeouts = []
    def generate(**kwargs):
        assert "total_timeout" not in kwargs  # local budget, never a transport option
        timeouts.append(kwargs["timeout"])
        if len(timeouts) == 1:
            now[0] += kwargs["timeout"]
            raise LLMTimeoutError("fixture timeout")
        if len(timeouts) == 2:
            now[0] += 20
            return '{"minimal":"' + '长' * 21 + '"}'
        now[0] += 5
        return '{"minimal":"品牌良率超过80%"}'
    transport.generate.side_effect = generate
    response = await call()
    assert response.title == "品牌良率超过80%"
    assert timeouts == [80, 80, 69.5]
    assert now[0] == 1105.5
    assert ec.remaining_timeout() is None


async def test_adapter_exhaustion_never_resets_title_deadline(title_harness):
    now, transport, call = title_harness
    timeouts = []
    def generate(**kwargs):
        timeouts.append(kwargs["timeout"])
        now[0] += kwargs["timeout"]
        if len(timeouts) == 1:
            raise LLMTimeoutError("fixture timeout")
        return '{"minimal":"' + '长' * 21 + '"}'
    transport.generate.side_effect = generate
    with pytest.raises(ServiceUnavailableException) as caught:
        await call()
    assert "after 170s" in caught.value.detail
    # Two adapter attempts; one semantic rewrite receives only the remainder.
    assert timeouts == [80, 80, 9.5]
    assert now[0] == 1170


@pytest.mark.parametrize("error", [LLMTimeoutError("private"), TimeoutError("private")])
async def test_early_upstream_timeout_does_not_claim_total_elapsed(title_harness, error):
    _, transport, call = title_harness
    transport.generate.side_effect = error
    with pytest.raises(ServiceUnavailableException) as caught:
        await call()
    assert "timed out" in caught.value.detail
    assert "after 170s" not in caught.value.detail
    assert "after 120s" not in caught.value.detail
    assert "private" not in caught.value.detail


def test_title_budget_is_below_browser_without_changing_hashtags():
    assert posts._resolve_timeouts("title_generate") == (80, 170)
    assert posts._resolve_timeouts("hashtag_generate") == (45, 120)
    assert posts._resolve_timeouts("title_generate")[1] < 180
