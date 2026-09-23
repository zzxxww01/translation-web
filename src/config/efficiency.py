"""Validated, explicit longform efficiency policy; no implicit model downgrade."""
from pydantic import BaseModel, Field, ConfigDict


class EfficiencyOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    resume_stages: bool = True
    prescan_concurrency: int = Field(3, ge=1, le=8)
    stage_timeout_seconds: int = Field(1800, ge=30, le=14400)
    max_stage_calls: int = Field(64, ge=1, le=2000)
    run_timeout_seconds: int = Field(14400, ge=60, le=86400)
    max_run_calls: int = Field(2000, ge=1, le=20000)
    compact_review: bool = False


from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_current: ContextVar[EfficiencyOptions | None] = ContextVar("efficiency_options", default=None)


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
