"""Thread-safe business-stage and run budgets, inherited by nested generation.

Limits count logical generations; adapter transport retries remain bounded by
its attempt plan. Estimated tokens reserve input + configured maximum output,
not actual charges. Exhaustion pauses work, never approves an unchecked draft.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import RLock
import time

from src.core.efficiency import EfficiencyOptions
from .errors import LLMError
from .request_sizing import estimate_tokens


class BusinessBudgetExceeded(LLMError):
    pass


@dataclass
class Budget:
    name: str
    deadline: float
    max_calls: int
    max_tokens: int | None = None
    calls: int = 0
    estimated_tokens: int = 0
    lock: RLock = field(default_factory=RLock)

    def check(self, calls=0, tokens=0):
        if time.monotonic() >= self.deadline:
            raise BusinessBudgetExceeded(f"{self.name}: time budget exhausted; resume from checkpoint")
        if self.calls + calls > self.max_calls:
            raise BusinessBudgetExceeded(f"{self.name}: generation budget exhausted; resume from checkpoint")
        if self.max_tokens is not None and self.estimated_tokens + tokens > self.max_tokens:
            raise BusinessBudgetExceeded(f"{self.name}: estimated token budget exhausted; resume from checkpoint")


_stack: ContextVar[tuple[Budget, ...]] = ContextVar("business_budgets", default=())
_quality_policy: ContextVar[str] = ContextVar("quality_policy", default="")
_options: ContextVar[EfficiencyOptions | None] = ContextVar("efficiency_options", default=None)


def set_quality_policy(value: str):
    _quality_policy.set(value)


def current_quality_policy() -> str:
    return _quality_policy.get()


def active_options() -> EfficiencyOptions | None:
    return _options.get()


def check_business_budgets():
    for budget in _stack.get():
        with budget.lock:
            budget.check()


def reserve_generation(prompt: str, max_output: int | None):
    budgets = _stack.get()
    if not budgets:
        return
    options = _options.get()
    tokens = estimate_tokens(prompt) + (max_output or (options.reserved_output_tokens if options else 8192))
    # All threads lock ancestors first. Either every budget accepts, or none do.
    from contextlib import ExitStack
    with ExitStack() as locks:
        for budget in budgets:
            locks.enter_context(budget.lock)
        for budget in budgets:
            budget.check(1, tokens)
        for budget in budgets:
            budget.calls += 1
            budget.estimated_tokens += tokens


@contextmanager
def run_budget(options: EfficiencyOptions):
    budget = Budget("run", time.monotonic() + options.max_run_seconds,
                    options.max_run_calls, options.max_run_estimated_tokens)
    token = _stack.set((budget,))
    opt = _options.set(options)
    quality = _quality_policy.set("")
    try:
        from .execution_context import deadline_scope
        with deadline_scope(options.max_run_seconds):
            yield budget
    finally:
        _quality_policy.reset(quality)
        _options.reset(opt)
        _stack.reset(token)


@contextmanager
def stage_budget(name: str):
    options = _options.get()
    if options is None:
        yield
        return
    from .execution_context import deadline_scope
    budget = Budget(name, time.monotonic() + options.max_stage_seconds, options.max_stage_calls)
    token = _stack.set((*_stack.get(), budget))
    try:
        with deadline_scope(options.max_stage_seconds):
            yield budget
    finally:
        _stack.reset(token)
