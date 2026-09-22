"""Whole rendered request sizing; estimates are explicitly not billable tokens."""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import math
from typing import Callable, Sequence, TypeVar

from .errors import LLMError

T = TypeVar("T")


class RequestTooLargeError(LLMError):
    """Split a multi-item task, never truncate an individual item's contents."""


def estimate_tokens(text: str) -> int:
    # Conservative heuristic: ASCII ~3 chars/token, other UTF-8 ~2 bytes/token.
    # Hidden protocol framing gets an additional fixed allowance. Not exact.
    ascii_chars = sum(ord(c) < 128 for c in text)
    other_bytes = len(text.encode("utf-8")) - ascii_chars
    return math.ceil(ascii_chars / 3 + other_bytes / 2) + 128


@dataclass(frozen=True)
class RequestBudget:
    max_input: int = 24000
    reserved_output: int = 8192
    context_window: int | None = None

    def check(self, prompt: str, *, output_limit: int | None = None,
              exact_counter: Callable[[str], int] | None = None) -> int:
        size = estimate_tokens(prompt)
        ceiling = self.max_input
        if self.context_window is not None:
            ceiling = min(ceiling, self.context_window - (output_limit or self.reserved_output))
        # Provider-specific counters may be used close to the boundary only.
        if exact_counter is not None and size >= ceiling * 0.8:
            size = exact_counter(prompt)
            if type(size) is not int or size < 0:
                raise ValueError("Token counter must return a nonnegative integer")
        if size > ceiling:
            raise RequestTooLargeError("Complete request exceeds configured input/context budget; split or configure a larger window")
        return size


_budget: ContextVar[RequestBudget | None] = ContextVar("request_size_budget", default=None)


@contextmanager
def request_size_scope(budget: RequestBudget):
    token = _budget.set(budget)
    try:
        yield
    finally:
        _budget.reset(token)


def check_request(prompt: str, output_limit: int | None = None) -> int:
    budget = _budget.get()
    return budget.check(prompt, output_limit=output_limit) if budget else estimate_tokens(prompt)


def sized_batches(items: Sequence[T], render: Callable[[list[T]], str],
                  budget: RequestBudget, max_items: int) -> list[list[T]]:
    if type(max_items) is not int or max_items < 1:
        raise ValueError("max_items must be positive")
    batches: list[list[T]] = []
    current: list[T] = []
    for item in items:
        candidate = current + [item]
        try:
            if len(candidate) > max_items:
                raise RequestTooLargeError("Item count limit")
            budget.check(render(candidate))
        except RequestTooLargeError:
            if not current:
                raise
            batches.append(current)
            current = [item]
            budget.check(render(current))  # single item is never truncated
        else:
            current = candidate
    if current:
        batches.append(current)
    return batches
