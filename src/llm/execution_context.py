"""One monotonic budget across retries and cooperative request abandonment.

A cancelled HTTP waiter cannot undo a request already sent to an upstream. It
can, however, prevent a queued request, backoff, or fallback from sending more.
No credentials or prompt bodies are stored in these execution scopes.
"""
from __future__ import annotations

import inspect
import math
import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from threading import Event
from typing import Any

from .errors import LLMDeadlineExceededError, LLMRequestCancelledError

_deadline: ContextVar[float | None] = ContextVar("llm_deadline", default=None)
_cancel: ContextVar[Event | None] = ContextVar("llm_cancel", default=None)
_route: ContextVar[dict[str, Any]] = ContextVar("llm_route", default={})
_output_limit: ContextVar[int | None] = ContextVar("llm_output_limit", default=None)


def positive_timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError("LLM timeout must be a finite positive number")
    return float(value)


def positive_token_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("max_tokens must be a positive integer")
    return value


def check_active() -> None:
    event = _cancel.get()
    if event is not None and event.is_set():
        raise LLMRequestCancelledError("LLM request was abandoned; no further attempts will be sent")
    deadline = _deadline.get()
    if deadline is not None and time.monotonic() >= deadline:
        raise LLMDeadlineExceededError("LLM generation deadline exhausted")


def remaining_timeout(cap: float | None = None) -> float | None:
    check_active()
    deadline = _deadline.get()
    remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
    if cap is not None:
        cap = positive_timeout(cap)
        return cap if remaining is None else min(cap, remaining)
    return remaining


def bounded_sleep(seconds: float) -> None:
    check_active()
    left = remaining_timeout()
    if left is not None and seconds >= left:
        raise LLMDeadlineExceededError("Not enough generation budget for another retry")
    event = _cancel.get()
    if event is None:
        time.sleep(seconds)
    else:
        event.wait(seconds)
    check_active()


@contextmanager
def cancellation_scope(event: Event):
    token = _cancel.set(event)
    try:
        yield
    finally:
        _cancel.reset(token)


@contextmanager
def route_scope(provider_id: str, rate_limit=None):
    token = _route.set({"provider_id": provider_id, "rate_limit": rate_limit})
    try:
        yield
    finally:
        _route.reset(token)


def current_route() -> dict[str, Any]:
    return _route.get()


def output_limit() -> int | None:
    return _output_limit.get()


def generation_budget(fn):
    """Keep compatible public signatures; also guard direct/legacy providers."""
    signature = inspect.signature(fn)
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        bound = signature.bind(self, *args, **kwargs).arguments
        options = {**bound.get("kwargs", {}), **bound.get("_kwargs", {})}
        timeout = bound.get("timeout", options.get("timeout"))
        if timeout is None:
            timeout = getattr(self, "request_timeout", None) or getattr(self, "timeout", None)
        if timeout is None:
            plans = getattr(self, "attempt_plan", [])
            config = getattr(plans[0].model, "config", {}) if plans else {}
            timeout = config.get("timeout", 120) if isinstance(config, dict) else 120
        seconds = positive_timeout(timeout)
        check_active()
        parent = _deadline.get()
        deadline = time.monotonic() + seconds
        token = _deadline.set(min(parent, deadline) if parent is not None else deadline)
        limit_token = None
        try:
            limit = options.get("max_tokens")
            if limit is not None:
                limit_token = _output_limit.set(positive_token_limit(limit))
            result = fn(self, *args, **kwargs)
            check_active()
            return result
        finally:
            if limit_token is not None:
                _output_limit.reset(limit_token)
            _deadline.reset(token)
    return wrapped
