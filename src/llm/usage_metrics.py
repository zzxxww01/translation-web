"""Bounded call records with exact run aggregates and provider billing dimensions."""
from __future__ import annotations

import time
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Optional

from .execution_context import current_route

_UNSCOPED_RUN_ID = "__unscoped__"
_TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "reasoning_tokens", "billable_output_tokens")


@dataclass
class LLMCallMetric:
    provider: str
    model: str
    phase: str
    duration_seconds: float
    success: bool
    input_chars: int = 0
    output_chars: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    attempts: int = 1
    error_type: Optional[str] = None
    provider_id: Optional[str] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    billable_output_tokens: Optional[int] = None
    recorded_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UsageTotals:
    api_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    billable_output_tokens: int = 0
    input_chars: int = 0
    output_chars: int = 0
    duration_seconds: float = 0.0
    unknown_input_calls: int = 0
    unknown_output_calls: int = 0
    unknown_cached_input_calls: int = 0
    unknown_billable_output_calls: int = 0
    failed_input_tokens: int = 0
    failed_billable_output_tokens: int = 0

    def add(self, metric: LLMCallMetric):
        self.api_calls += 1
        self.successful_calls += int(metric.success)
        self.failed_calls += int(not metric.success)
        for name in _TOKEN_FIELDS:
            setattr(self, name, getattr(self, name) + (getattr(metric, name) or 0))
        self.input_chars += metric.input_chars
        self.output_chars += metric.output_chars
        self.duration_seconds += metric.duration_seconds
        self.unknown_input_calls += int(metric.input_tokens is None)
        self.unknown_output_calls += int(metric.output_tokens is None)
        self.unknown_cached_input_calls += int(metric.cached_input_tokens is None)
        self.unknown_billable_output_calls += int(metric.billable_output_tokens is None)
        if not metric.success:
            self.failed_input_tokens += metric.input_tokens or 0
            self.failed_billable_output_tokens += metric.billable_output_tokens or 0

    def payload(self):
        result = asdict(self)
        result["duration_seconds"] = round(self.duration_seconds, 4)
        result["service_seconds"] = result["duration_seconds"]
        result["token_usage_complete"] = not (self.unknown_input_calls or self.unknown_billable_output_calls)
        return result


@dataclass
class LLMRunUsage:
    run_id: str
    project_id: Optional[str]
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_monotonic: float = field(default_factory=time.monotonic)
    calls: list[LLMCallMetric] = field(default_factory=list)
    totals: UsageTotals = field(default_factory=UsageTotals)
    groups: dict[tuple[str, str, str, str], UsageTotals] = field(default_factory=dict)


class LLMUsageMetrics:
    """Constant-time per-call accumulation; compact polling never scans call logs.

    Detailed records are bounded, totals are not. A finished run is closed to
    late worker writes; these observations are not an authoritative invoice.
    Unknown usage (including failed network responses) is explicitly counted.
    """
    _MAX_CALLS_PER_RUN = 5000
    _MAX_FINISHED_RUNS = 10000

    def __init__(self):
        self._lock = Lock()
        self._runs: dict[str, LLMRunUsage] = {}
        self._finished_runs: OrderedDict[str, None] = OrderedDict()
        self._current_run_id: ContextVar[Optional[str]] = ContextVar("llm_usage_run_id", default=None)
        self._current_phase: ContextVar[str] = ContextVar("llm_usage_phase", default="unspecified")

    def start_run(self, run_id: str, *, project_id: Optional[str] = None):
        if not run_id:
            raise ValueError("run_id is required")
        with self._lock:
            self._finished_runs.pop(run_id, None)
            self._runs[run_id] = LLMRunUsage(run_id=run_id, project_id=project_id)
        self._current_run_id.set(run_id)
        self._current_phase.set("starting")

    def set_phase(self, phase: str):
        self._current_phase.set(phase.strip() or "unspecified")

    def current_run_id(self) -> Optional[str]:
        return self._current_run_id.get()

    def _resolve_run_id(self, run_id=None):
        return run_id or self._current_run_id.get() or _UNSCOPED_RUN_ID

    def reset(self, run_id=None):
        with self._lock:
            resolved = self._resolve_run_id(run_id)
            self._runs.pop(resolved, None)
            self._finished_runs.pop(resolved, None)

    def finish_run(self, run_id=None):
        resolved = self._resolve_run_id(run_id)
        # Summarize and close under one lock so records cannot land between them.
        with self._lock:
            result = self._summary_locked(resolved, include_calls=True)
            self._finished_runs[resolved] = None
            self._finished_runs.move_to_end(resolved)
            while len(self._finished_runs) > self._MAX_FINISHED_RUNS:
                self._finished_runs.popitem(last=False)
            self._runs.pop(resolved, None)
        if self._current_run_id.get() == resolved:
            self._current_run_id.set(None)
            self._current_phase.set("unspecified")
        return result

    def record_call(self, *, provider, model, duration_seconds, success,
                    input_chars=0, output_chars=0, input_tokens=None,
                    output_tokens=None, total_tokens=None, attempts=1,
                    error_type=None, phase=None, run_id=None, provider_id=None,
                    cached_input_tokens=None, reasoning_tokens=None,
                    billable_output_tokens=None):
        resolved = self._resolve_run_id(run_id)
        tokens = {name: value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
                  for name, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens),
                  ("total_tokens", total_tokens), ("cached_input_tokens", cached_input_tokens),
                  ("reasoning_tokens", reasoning_tokens), ("billable_output_tokens", billable_output_tokens))}
        metric = LLMCallMetric(provider=provider, model=model, phase=phase or self._current_phase.get(),
            duration_seconds=round(max(duration_seconds, 0.0), 4), success=success,
            input_chars=max(input_chars, 0), output_chars=max(output_chars, 0),
            attempts=max(attempts, 1), error_type=error_type,
            provider_id=provider_id or current_route().get("provider_id") or provider, **tokens)
        with self._lock:
            if resolved in self._finished_runs:
                return 0
            run = self._runs.get(resolved)
            if run is None:
                run = self._runs[resolved] = LLMRunUsage(run_id=resolved, project_id=None)
            run.totals.add(metric)
            key = (metric.provider_id, metric.provider, model, metric.phase)
            run.groups.setdefault(key, UsageTotals()).add(metric)
            if len(run.calls) < self._MAX_CALLS_PER_RUN:
                run.calls.append(metric)
            return run.totals.api_calls

    def increment_api_calls(self):
        return self.record_call(provider="unknown", model="unknown", duration_seconds=0, success=True)

    def api_call_count(self, run_id=None):
        with self._lock:
            run = self._runs.get(self._resolve_run_id(run_id))
            return run.totals.api_calls if run else 0

    def _summary_locked(self, resolved, *, include_calls):
        run = self._runs.get(resolved)
        result = {"run_id": resolved, **(run.totals if run else UsageTotals()).payload()}
        if run:
            result.update(project_id=run.project_id, started_at=run.started_at,
                wall_elapsed_seconds=round(max(time.monotonic() - run.started_monotonic, 0), 4),
                models=sorted({key[2] for key in run.groups if key[2]}),
                phases=sorted({key[3] for key in run.groups if key[3]}),
                groups=[dict(provider_id=key[0], provider=key[1], model=key[2], phase=key[3], **totals.payload())
                        for key, totals in sorted(run.groups.items())],
                retained_call_records=len(run.calls), dropped_call_records=run.totals.api_calls-len(run.calls))
        result["accounting_scope"] = "observed_completed_attempts; excludes unknown charges and responses arriving after run closure"
        if include_calls:
            result["calls"] = [asdict(call) for call in run.calls] if run else []
        return result

    def summary(self, run_id=None, *, include_calls=True):
        with self._lock:
            return self._summary_locked(self._resolve_run_id(run_id), include_calls=include_calls)


llm_usage_metrics = LLMUsageMetrics()
