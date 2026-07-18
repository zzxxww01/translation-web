"""Run-scoped LLM usage telemetry."""

from __future__ import annotations

from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Optional


_UNSCOPED_RUN_ID = "__unscoped__"


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
    recorded_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LLMRunUsage:
    run_id: str
    project_id: Optional[str]
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    calls: list[LLMCallMetric] = field(default_factory=list)


class LLMUsageMetrics:
    """Thread-safe metrics grouped by the current translation run.

    Context variables propagate through ``asyncio`` tasks and
    ``asyncio.to_thread``, which keeps concurrent projects isolated without
    changing every provider method signature.
    """

    _MAX_CALLS_PER_RUN = 5000
    _MAX_FINISHED_RUNS = 10000

    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, LLMRunUsage] = {}
        self._finished_runs: OrderedDict[str, None] = OrderedDict()
        self._current_run_id: ContextVar[Optional[str]] = ContextVar(
            "llm_usage_run_id",
            default=None,
        )
        self._current_phase: ContextVar[str] = ContextVar(
            "llm_usage_phase",
            default="unspecified",
        )

    def start_run(self, run_id: str, *, project_id: Optional[str] = None) -> None:
        if not run_id:
            raise ValueError("run_id is required")
        with self._lock:
            self._finished_runs.pop(run_id, None)
            self._runs[run_id] = LLMRunUsage(
                run_id=run_id,
                project_id=project_id,
            )
        self._current_run_id.set(run_id)
        self._current_phase.set("starting")

    def set_phase(self, phase: str) -> None:
        self._current_phase.set(phase.strip() or "unspecified")

    def current_run_id(self) -> Optional[str]:
        return self._current_run_id.get()

    def _resolve_run_id(self, run_id: Optional[str] = None) -> str:
        return run_id or self._current_run_id.get() or _UNSCOPED_RUN_ID

    def _ensure_run(self, run_id: str) -> LLMRunUsage:
        run = self._runs.get(run_id)
        if run is None:
            run = LLMRunUsage(run_id=run_id, project_id=None)
            self._runs[run_id] = run
        return run

    def reset(self, run_id: Optional[str] = None) -> None:
        resolved_run_id = self._resolve_run_id(run_id)
        with self._lock:
            self._runs.pop(resolved_run_id, None)
            self._finished_runs.pop(resolved_run_id, None)

    def finish_run(self, run_id: Optional[str] = None) -> dict[str, Any]:
        """Return the final summary and release per-call records from memory."""

        resolved_run_id = self._resolve_run_id(run_id)
        with self._lock:
            self._finished_runs[resolved_run_id] = None
            self._finished_runs.move_to_end(resolved_run_id)
            while len(self._finished_runs) > self._MAX_FINISHED_RUNS:
                self._finished_runs.popitem(last=False)
        summary = self.summary(resolved_run_id)
        with self._lock:
            self._runs.pop(resolved_run_id, None)
        if self._current_run_id.get() == resolved_run_id:
            self._current_run_id.set(None)
            self._current_phase.set("unspecified")
        return summary

    def record_call(
        self,
        *,
        provider: str,
        model: str,
        duration_seconds: float,
        success: bool,
        input_chars: int = 0,
        output_chars: int = 0,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        attempts: int = 1,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> int:
        resolved_run_id = self._resolve_run_id(run_id)
        metric = LLMCallMetric(
            provider=provider,
            model=model,
            phase=phase or self._current_phase.get(),
            duration_seconds=round(max(duration_seconds, 0.0), 4),
            success=success,
            input_chars=max(input_chars, 0),
            output_chars=max(output_chars, 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            attempts=max(attempts, 1),
            error_type=error_type,
        )
        with self._lock:
            if resolved_run_id in self._finished_runs:
                return 0
            run = self._ensure_run(resolved_run_id)
            if len(run.calls) < self._MAX_CALLS_PER_RUN:
                run.calls.append(metric)
            return len(run.calls)

    def increment_api_calls(self) -> int:
        """Backward-compatible counter for callers without detailed telemetry."""
        return self.record_call(
            provider="unknown",
            model="unknown",
            duration_seconds=0,
            success=True,
        )

    def api_call_count(self, run_id: Optional[str] = None) -> int:
        resolved_run_id = self._resolve_run_id(run_id)
        with self._lock:
            run = self._runs.get(resolved_run_id)
            return len(run.calls) if run else 0

    def summary(self, run_id: Optional[str] = None) -> dict[str, Any]:
        resolved_run_id = self._resolve_run_id(run_id)
        with self._lock:
            run = self._runs.get(resolved_run_id)
            if run is None:
                return {
                    "run_id": resolved_run_id,
                    "api_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "duration_seconds": 0.0,
                    "calls": [],
                }
            calls = list(run.calls)
            project_id = run.project_id
            started_at = run.started_at

        return {
            "run_id": resolved_run_id,
            "project_id": project_id,
            "started_at": started_at,
            "api_calls": len(calls),
            "successful_calls": sum(1 for call in calls if call.success),
            "failed_calls": sum(1 for call in calls if not call.success),
            "input_tokens": sum(call.input_tokens or 0 for call in calls),
            "output_tokens": sum(call.output_tokens or 0 for call in calls),
            "total_tokens": sum(call.total_tokens or 0 for call in calls),
            "input_chars": sum(call.input_chars for call in calls),
            "output_chars": sum(call.output_chars for call in calls),
            "duration_seconds": round(
                sum(call.duration_seconds for call in calls),
                4,
            ),
            "models": sorted({call.model for call in calls if call.model}),
            "phases": sorted({call.phase for call in calls if call.phase}),
            "calls": [asdict(call) for call in calls],
        }


llm_usage_metrics = LLMUsageMetrics()
