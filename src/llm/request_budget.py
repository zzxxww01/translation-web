"""Budget the rendered text request, including rules, examples and context.

Fallback estimation uses UTF-8 bytes with a safety margin. It is deliberately
conservative, not a universal tokenizer proof. Optional exact counters are
local callables and cached; this module never adds a remote API request.
"""
from __future__ import annotations
import hashlib
import math
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Callable
from .errors import LLMError


class RequestBudgetExceeded(LLMError):
    pass


@dataclass(frozen=True)
class RequestLimits:
    input_tokens: int | None = None
    output_tokens: int | None = None
    context_tokens: int | None = None
    reserve_output_tokens: int = 8192

    def __post_init__(self):
        for value in (self.input_tokens, self.output_tokens, self.context_tokens, self.reserve_output_tokens):
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError("Request limits must be positive integers")


_counter_lock = Lock()
_counts: OrderedDict[tuple, int] = OrderedDict()


def count_request(prompt: str, *, model: str = "", counter: Callable[[str], int] | None = None) -> tuple[int, str]:
    if not isinstance(prompt, str):
        raise TypeError("Rendered prompt must be text")
    if counter is None:
        return math.ceil(len(prompt.encode("utf-8")) * 1.1) + 128, "utf8_conservative_estimate"
    key = (model, counter, hashlib.sha256(prompt.encode()).hexdigest())
    with _counter_lock:
        if key in _counts:
            _counts.move_to_end(key)
            return _counts[key], "exact_local_counter"
    value = counter(prompt)
    if type(value) is not int or value < 0:
        raise ValueError("Invalid tokenizer count")
    with _counter_lock:
        _counts[key] = value
        while len(_counts) > 256:
            _counts.popitem(last=False)
    return value, "exact_local_counter"


def check_request(prompt: str, limits: RequestLimits, *, model: str = "", counter=None) -> dict:
    count, method = count_request(prompt, model=model, counter=counter)
    reserve = limits.reserve_output_tokens
    if limits.input_tokens is not None and count > limits.input_tokens:
        raise RequestBudgetExceeded("Rendered input exceeds configured input budget; split the task without truncation")
    if limits.output_tokens is not None and reserve > limits.output_tokens:
        raise RequestBudgetExceeded("Output reservation exceeds configured model output limit")
    if limits.context_tokens is not None and count + reserve > limits.context_tokens:
        raise RequestBudgetExceeded("Rendered input plus reserved output exceeds configured shared context window")
    return {"input_tokens": count, "reserved_output_tokens": reserve, "count_method": method}


def limits_for_provider(provider) -> RequestLimits | None:
    config = getattr(provider, "_request_budget_config", {})
    if not isinstance(config, dict) or not any(config.get(k) for k in ("input_token_limit", "context_window_tokens", "output_token_limit")):
        return None
    return RequestLimits(input_tokens=config.get("input_token_limit"), output_tokens=config.get("output_token_limit"),
                         context_tokens=config.get("context_window_tokens"),
                         reserve_output_tokens=config.get("max_tokens", getattr(provider, "max_tokens", None) or 8192))


def check_provider_request(provider, prompt: str):
    limits = limits_for_provider(provider)
    if limits is None:
        return None
    return check_request(prompt, limits, model=str(getattr(provider, "model_name", "")),
                         counter=getattr(provider, "local_token_counter", None))
