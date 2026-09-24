"""Shared work admission across generated requests, business phases and a run.

Budgets count actual transport admissions, including retries. They are not a
currency invoice. No model quality checks are skipped on exhaustion.
"""
from __future__ import annotations

import math
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable

from .errors import LLMError, LLMConfigurationError, LLMRequestCancelledError


class WorkBudgetExceeded(LLMError):
    """A resumable pause; never convert this into a successful translation."""


@dataclass
class WorkBudget:
    name: str
    seconds: float
    max_calls: int
    should_cancel: Callable[[], bool] | None = None
    calls: int = 0
    unit: str = "transport"
    max_tokens: int | None = None
    estimated_tokens: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)
    deadline: float = field(init=False)

    def __post_init__(self):
        if isinstance(self.seconds, bool) or not isinstance(self.seconds, (int, float)) or not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Work budget duration must be finite and positive")
        if type(self.max_calls) is not int or self.max_calls <= 0:
            raise ValueError("Work budget call count must be a positive integer")
        if self.unit not in {"transport", "logical"}:
            raise ValueError("Unknown budget counting unit")
        if self.max_tokens is not None and (type(self.max_tokens) is not int or self.max_tokens <= 0):
            raise ValueError("Estimated token limit must be positive")
        self.deadline = time.monotonic() + self.seconds

    def check(self):
        if self.should_cancel is not None and self.should_cancel():
            raise LLMRequestCancelledError("Translation cancelled by user")
        if time.monotonic() >= self.deadline:
            raise WorkBudgetExceeded(f"{self.name} time budget exhausted; resume from checkpoints")
        if self.calls >= self.max_calls:
            raise WorkBudgetExceeded(f"{self.name} call budget exhausted; resume from checkpoints")


_budgets: ContextVar[tuple[WorkBudget, ...]] = ContextVar("work_budgets", default=())
_generation_defaults: ContextVar[dict] = ContextVar("phase_generation_defaults", default={})
_admission_lock = Lock()


def current_generation_defaults() -> dict:
    return dict(_generation_defaults.get())


@contextmanager
def generation_defaults(values: dict):
    token = _generation_defaults.set(dict(values))
    try:
        yield
    finally:
        _generation_defaults.reset(token)


@contextmanager
def work_budget_scope(name: str, seconds: float, max_calls: int, *, should_cancel=None, unit="transport", max_tokens=None):
    from .execution_context import deadline_scope
    budget = WorkBudget(name, seconds, max_calls, should_cancel, unit=unit, max_tokens=max_tokens)
    token = _budgets.set((*_budgets.get(), budget))
    try:
        with deadline_scope(seconds):
            yield budget
    finally:
        _budgets.reset(token)


def check_work_active():
    # Already-admitted work may finish when calls == max_calls. Only new
    # admissions test the count; otherwise the last paid response is discarded.
    for budget in _budgets.get():
        if budget.should_cancel is not None and budget.should_cancel():
            raise LLMRequestCancelledError("Translation cancelled by user")
        if time.monotonic() >= budget.deadline:
            raise WorkBudgetExceeded(f"{budget.name} time budget exhausted; resume from checkpoints")


_request_estimate: ContextVar[int] = ContextVar("request_token_reservation", default=0)


@contextmanager
def request_reservation(prompt: str, output: int | None):
    from .request_sizing import estimate_tokens
    token = _request_estimate.set(estimate_tokens(prompt) + (output if output is not None else 8192))
    try:
        yield
    finally:
        _request_estimate.reset(token)


def _reserve(unit: str):
    # Validate every ancestor before changing any counter. A retry is a new
    # transport admission, not a new logical generation.
    with _admission_lock:
        check_work_active()
        scopes = [budget for budget in _budgets.get() if budget.unit == unit]
        tokens = _request_estimate.get()
        for budget in scopes:
            budget.check()
            if budget.max_tokens is not None and budget.estimated_tokens + tokens > budget.max_tokens:
                raise WorkBudgetExceeded(f"{budget.name} estimated token budget exhausted; resume from checkpoints")
        for budget in scopes:
            budget.calls += 1
            budget.estimated_tokens += tokens


def admit_transport():
    _reserve("transport")


def admit_logical_generation():
    _reserve("logical")


def retry_action(error: Exception) -> str:
    """Classify recovery without changing input for an unrelated network failure."""
    from .errors import LLMDeadlineExceededError, LLMOutputTruncatedError, normalize_llm_transport_error
    from .request_budget import RequestBudgetExceeded
    from src.prompts.contracts import PromptContractError
    if isinstance(error, (WorkBudgetExceeded, LLMDeadlineExceededError, LLMRequestCancelledError, LLMConfigurationError)):
        return "stop"
    if isinstance(error, (RequestBudgetExceeded, LLMOutputTruncatedError)):
        return "resize"
    if isinstance(error, PromptContractError) or (isinstance(error, ValueError) and "json" in str(error).lower()):
        return "format"
    normalized = normalize_llm_transport_error(error, provider_name="analysis")
    if normalized is not None and normalized.retryable:
        return "retry"
    return "stop"
