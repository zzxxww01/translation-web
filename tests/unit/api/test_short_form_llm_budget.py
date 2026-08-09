import asyncio
from unittest.mock import AsyncMock

import pytest

from src.api.routers import slack_refine, slack_refine_version
from src.api.utils import llm_factory


def test_short_form_budget_allows_fallback_before_browser_timeout() -> None:
    assert (
        llm_factory.SHORT_FORM_ATTEMPT_TIMEOUT_SECONDS
        < llm_factory.SHORT_FORM_TOTAL_TIMEOUT_SECONDS
        < 180
    )


def test_slack_refine_route_matches_frontend_and_keeps_legacy_path() -> None:
    assert any(route.path == "/slack/refine" for route in slack_refine.router.routes)
    assert any(route.path == "/refine" for route in slack_refine.router.routes)


@pytest.mark.asyncio
async def test_short_form_generation_uses_bounded_llm_executor(monkeypatch) -> None:
    observed = {}

    async def fake_run_llm_blocking(func, *args, **kwargs):
        observed.update({"func": func, "args": args, "kwargs": kwargs})
        return "result"

    monkeypatch.setattr(llm_factory, "run_llm_blocking", fake_run_llm_blocking)

    result = await llm_factory.generate_with_fallback_budget(
        "prompt",
        task_type="slack",
        attempt_timeout=7,
        total_timeout=1,
    )

    assert result == "result"
    assert observed["func"] is llm_factory.generate_with_fallback
    assert observed["args"] == ("prompt",)
    assert observed["kwargs"]["task_type"] == "slack"
    assert observed["kwargs"]["timeout"] == 7


@pytest.mark.asyncio
async def test_short_form_generation_enforces_total_budget(monkeypatch) -> None:
    async def never_finishes(*_args, **_kwargs):
        await asyncio.sleep(1)
        return "late"

    monkeypatch.setattr(llm_factory, "run_llm_blocking", never_finishes)

    with pytest.raises(asyncio.TimeoutError):
        await llm_factory.generate_with_fallback_budget(
            "prompt",
            task_type="slack",
            total_timeout=0.01,
        )


@pytest.mark.asyncio
async def test_refine_version_accepts_frontend_query_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        slack_refine_version.prompt_manager,
        "get",
        lambda *_args, **_kwargs: "rendered",
    )
    generate = AsyncMock(return_value="Refined English")
    monkeypatch.setattr(
        slack_refine_version,
        "generate_with_fallback_budget",
        generate,
    )

    result = await slack_refine_version.refine_version(
        version="B",
        chinese=" 更新后的中文 ",
        style="正式",
    )

    assert result.version == "B"
    assert result.chinese == "更新后的中文"
    assert result.english == "Refined English"
    assert result.style == "正式"
    generate.assert_awaited_once_with("rendered", task_type="slack")
