from src.llm.usage_metrics import LLMUsageMetrics


def test_usage_metrics_reset_and_increment() -> None:
    metrics = LLMUsageMetrics()

    assert metrics.api_call_count() == 0
    assert metrics.increment_api_calls() == 1
    assert metrics.increment_api_calls() == 2

    metrics.reset()
    assert metrics.api_call_count() == 0


def test_usage_metrics_are_isolated_by_run() -> None:
    metrics = LLMUsageMetrics()

    metrics.start_run("run-a", project_id="project-a")
    metrics.set_phase("phase1_draft")
    metrics.record_call(
        provider="vectorengine",
        model="model-a",
        duration_seconds=1.25,
        success=True,
        input_chars=100,
        output_chars=50,
        input_tokens=25,
        output_tokens=12,
        total_tokens=37,
    )

    metrics.start_run("run-b", project_id="project-b")
    metrics.record_call(
        provider="gemini",
        model="model-b",
        duration_seconds=0.5,
        success=False,
        error_type="TimeoutError",
    )

    assert metrics.api_call_count("run-a") == 1
    assert metrics.api_call_count("run-b") == 1
    assert metrics.summary("run-a")["total_tokens"] == 37
    assert metrics.summary("run-a")["phases"] == ["phase1_draft"]
    assert metrics.summary("run-b")["failed_calls"] == 1


def test_finish_run_returns_summary_and_releases_call_records() -> None:
    metrics = LLMUsageMetrics()
    metrics.start_run("run-finished", project_id="project-a")
    metrics.record_call(
        provider="gemini",
        model="model-a",
        duration_seconds=0.25,
        success=True,
        total_tokens=12,
    )

    summary = metrics.finish_run("run-finished")

    assert summary["api_calls"] == 1
    assert summary["total_tokens"] == 12
    assert metrics.api_call_count("run-finished") == 0


def test_late_background_call_does_not_recreate_finished_run() -> None:
    metrics = LLMUsageMetrics()
    metrics.start_run("run-finished", project_id="project-a")
    metrics.finish_run("run-finished")

    recorded_count = metrics.record_call(
        provider="late-worker",
        model="background-model",
        duration_seconds=0.1,
        success=True,
        run_id="run-finished",
    )

    assert recorded_count == 0
    assert metrics.api_call_count("run-finished") == 0
    assert metrics.summary("run-finished")["api_calls"] == 0
    assert metrics.current_run_id() is None
