from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from src.core.efficiency import EfficiencyOptions
from src.llm.business_budget import run_budget, stage_budget, BusinessBudgetExceeded
from src.llm.execution_context import generation_budget, remaining_timeout
from src.llm.request_sizing import RequestBudget, RequestTooLargeError, estimate_tokens, sized_batches, request_size_scope
from src.services.stage_checkpoints import StageCheckpoints, checkpoint_scope, cached_stage
from src.agents.deep_analyzer import DeepAnalyzer
from src.llm.errors import LLMDeadlineExceededError, LLMConfigurationError, LLMOutputTruncatedError, LLMTimeoutError


class Concrete:
    timeout = 20
    def __init__(self): self.sent = 0
    @generation_budget
    def generate(self, prompt, timeout=None, **kwargs):
        self.sent += 1
        return remaining_timeout()


class Adapter:
    timeout = 20
    def __init__(self, concrete): self.concrete = concrete
    @generation_budget
    def generate(self, prompt, timeout=None, **kwargs):
        return self.concrete.generate(prompt, timeout=timeout, **kwargs)


def test_nested_transport_wrappers_reserve_one_generation():
    concrete = Concrete()
    options = EfficiencyOptions(max_stage_calls=1, max_run_calls=3)
    with run_budget(options) as run:
        with stage_budget("draft") as stage:
            assert Adapter(concrete).generate("hello") > 0
            with pytest.raises(BusinessBudgetExceeded): Adapter(concrete).generate("again")
            assert stage.calls == run.calls == concrete.sent == 1
        with stage_budget("review"):
            Adapter(concrete).generate("review")
            assert run.calls == 2


def test_rejected_reservation_changes_no_parent_counters():
    options = EfficiencyOptions(max_run_calls=1)
    p = Concrete()
    with run_budget(options) as run:
        p.generate("one")
        with stage_budget("two") as stage:
            with pytest.raises(BusinessBudgetExceeded): p.generate("no")
            assert run.calls == 1 and stage.calls == 0
            assert stage.estimated_tokens == 0


def test_remaining_transport_timeout_cannot_outlive_stage_or_run():
    p = Concrete()
    with run_budget(EfficiencyOptions(max_run_seconds=4.0, max_stage_seconds=0.5)):
        with stage_budget("short"):
            assert 0 < p.generate("hello", timeout=100) <= 0.5
        assert 0 < p.generate("next", timeout=100) <= 4.0


def test_estimated_token_limit_is_not_billed_and_blocks_before_call():
    p = Concrete()
    with run_budget(EfficiencyOptions(max_run_estimated_tokens=1)) as run:
        with pytest.raises(BusinessBudgetExceeded): p.generate("hello")
        assert p.sent == run.calls == run.estimated_tokens == 0


def test_checkpoint_hits_do_not_reserve_generation_budget(tmp_path):
    p = Concrete()
    with checkpoint_scope(StageCheckpoints(tmp_path, "v1")), run_budget(EfficiencyOptions(max_run_calls=1)) as run:
        a = cached_stage("one", {}, lambda: p.generate("hello"))
        assert cached_stage("one", {}, lambda: p.generate("hello")) == a
        assert p.sent == run.calls == 1


def test_whole_prompt_overhead_not_only_source_controls_batches():
    items = ["a" * 500, "b" * 500, "c" * 500]
    render = lambda parts: "rules and glossary " * 80 + "\n".join(parts)
    budget = RequestBudget(max_input=900)
    batches = sized_batches(items, render, budget, 8)
    assert len(batches) > 1
    assert [p for batch in batches for p in batch] == items
    for batch in batches: assert budget.check(render(batch)) <= 900
    with pytest.raises(RequestTooLargeError): sized_batches(["x" * 8000], render, budget, 8)


def test_output_reservation_and_later_route_limit_are_checked():
    p = Concrete()
    with request_size_scope(RequestBudget(max_input=2000, reserved_output=100, context_window=600)):
        assert p.generate("small", max_tokens=100)
        with pytest.raises(RequestTooLargeError): Adapter(p).generate("small", max_tokens=600)
    assert p.sent == 1


def test_exact_counter_called_only_near_boundary():
    counts = []
    def count(prompt): counts.append(prompt); return 200
    budget = RequestBudget(1000)
    assert budget.check("small", exact_counter=count) < 1000 and not counts
    assert budget.check("x" * 3000, exact_counter=count) == 200
    assert len(counts) == 1
    with pytest.raises(ValueError): budget.check("x" * 3000, exact_counter=lambda _: True)


@pytest.mark.parametrize("values", [{"max_stage_calls": 0}, {"prescan_concurrency": 0}, {"max_run_seconds": float('inf')}, {"max_run_calls": True}, {"compact_review": "false"}, {"unknown_option": 1}])
def test_efficiency_options_fail_closed(values):
    with pytest.raises(ValidationError): EfficiencyOptions(**values)


@pytest.mark.parametrize("error,action", [
    (LLMDeadlineExceededError("timeout"), "stop"),
    (LLMConfigurationError("invalid"), "stop"),
    (BusinessBudgetExceeded("limit"), "stop"),
    (LLMTimeoutError("network"), "retry_same_input"),
    (RuntimeError("deadline exceeded"), "retry_same_input"),
    (RequestTooLargeError("window"), "reduce_input"),
    (LLMOutputTruncatedError("limit"), "reduce_input"),
    (ValueError("invalid json"), "format_retry"),
])
def test_recovery_matches_failure_kind(error, action):
    assert DeepAnalyzer.recovery_action(error) == action
