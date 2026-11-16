"""Logical-generation budget scopes for tests.

The production pipeline budgets transport admissions (see ``src.llm.work_budget``).
These helpers open the same budget engine in ``unit="logical"`` mode so tests can
count generations per run/stage without going through a provider. They used to
live in ``src/llm/business_budget.py``, which no production code imported.
"""
from contextlib import contextmanager

from src.config.efficiency import EfficiencyOptions, active_options, efficiency_scope
from src.llm.work_budget import work_budget_scope


@contextmanager
def run_budget(options: EfficiencyOptions):
    with efficiency_scope(options), work_budget_scope(
        "run", options.run_timeout_seconds, options.max_run_calls,
        unit="logical", max_tokens=options.max_run_estimated_tokens,
    ) as budget:
        yield budget


@contextmanager
def stage_budget(name: str):
    options = active_options()
    if options is None:
        yield
        return
    with work_budget_scope(name, options.stage_timeout_seconds, options.max_stage_calls, unit="logical") as budget:
        yield budget
