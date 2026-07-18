"""Shared helpers for keeping blocking work off the FastAPI event loop."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from starlette.concurrency import run_in_threadpool


T = TypeVar("T")


async def run_blocking(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    return await run_in_threadpool(func, *args, **kwargs)
