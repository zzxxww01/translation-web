"""Compatibility API over the unified budget engine.

Older callers explicitly budget logical generations. The production pipeline
budgets transport admissions, including retries. Both use the same atomic
ancestor reservation and monotonic deadline machinery; units are never mixed.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from src.config.efficiency import EfficiencyOptions, active_options, efficiency_scope
from .work_budget import (
    WorkBudgetExceeded as BusinessBudgetExceeded,
    check_work_active as check_business_budgets,
    admit_logical_generation, request_reservation, work_budget_scope,
)

_quality_policy: ContextVar[str] = ContextVar("quality_policy", default="")


def set_quality_policy(value: str):
    _quality_policy.set(value)


def current_quality_policy() -> str:
    return _quality_policy.get()


def reserve_generation(prompt: str, max_output: int | None):
    options = active_options()
    output = max_output if max_output is not None else (options.reserved_output_tokens if options else 8192)
    with request_reservation(prompt, output):
        admit_logical_generation()


@contextmanager
def run_budget(options: EfficiencyOptions):
    quality = _quality_policy.set("")
    try:
        with efficiency_scope(options), work_budget_scope(
            "run", options.run_timeout_seconds, options.max_run_calls,
            unit="logical", max_tokens=options.max_run_estimated_tokens,
        ) as budget:
            yield budget
    finally:
        _quality_policy.reset(quality)


@contextmanager
def stage_budget(name: str):
    options = active_options()
    if options is None:
        yield
        return
    with work_budget_scope(name, options.stage_timeout_seconds, options.max_stage_calls, unit="logical") as budget:
        yield budget
