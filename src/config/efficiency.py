"""One validated policy shared by both efficiency APIs.

Legacy spellings remain accepted, but contradictory aliases are rejected.
Defaults retain serial scanning and full evidence-based review.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class EfficiencyOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    resume_stages: bool = True
    prescan_concurrency: int = Field(1, ge=1, le=8)
    stage_timeout_seconds: float = Field(1800.0, gt=0, le=86400, allow_inf_nan=False)
    max_stage_calls: int = Field(64, ge=1, le=10000)
    run_timeout_seconds: float = Field(14400.0, gt=0, le=604800, allow_inf_nan=False)
    max_run_calls: int = Field(2000, ge=1, le=100000)
    compact_review: bool = False
    model_scope: Literal["all", "draft"] = "all"
    profile: Literal["default", "fast", "premium"] = "default"
    max_run_estimated_tokens: int | None = Field(None, ge=1)
    # Optional operator limits are distinct from verified physical model limits.
    max_request_input_tokens: int | None = Field(None, ge=512, le=2000000)
    reserved_output_tokens: int = Field(8192, ge=256, le=200000)
    max_context_tokens: int | None = Field(None, ge=1024, le=4000000)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value):
        if not isinstance(value, dict):
            return value
        value = dict(value)
        for old, new in (("stage_resume", "resume_stages"),
                         ("max_stage_seconds", "stage_timeout_seconds"),
                         ("max_run_seconds", "run_timeout_seconds")):
            if old in value:
                if new in value and (value[old] != value[new] or type(value[old]) is bool):
                    raise ValueError(f"Conflicting efficiency options: {old} and {new}")
                value[new] = value.pop(old)
        return value

    @property
    def stage_resume(self):
        return self.resume_stages

    @property
    def max_stage_seconds(self):
        return self.stage_timeout_seconds

    @property
    def max_run_seconds(self):
        return self.run_timeout_seconds


_current: ContextVar[EfficiencyOptions | None] = ContextVar("efficiency_options", default=None)


def active_options():
    return _current.get()


@contextmanager
def efficiency_scope(options: EfficiencyOptions):
    token = _current.set(options)
    try:
        yield
    finally:
        _current.reset(token)


@contextmanager
def stage_scope(name: str):
    options = _current.get()
    if options is None:
        yield
        return
    from src.llm.work_budget import work_budget_scope
    with work_budget_scope(name, options.stage_timeout_seconds, options.max_stage_calls):
        yield


def bounded_stage(name: str):
    def decorator(function):
        @wraps(function)
        def invoke(*args, **kwargs):
            with stage_scope(name):
                return function(*args, **kwargs)
        return invoke
    return decorator
