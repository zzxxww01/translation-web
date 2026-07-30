"""Shared helpers for keeping blocking work off the FastAPI event loop."""

from __future__ import annotations

import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from starlette.concurrency import run_in_threadpool


T = TypeVar("T")


def _resolve_llm_pool_size() -> int:
    raw = os.getenv("LLM_BLOCKING_POOL_WORKERS", "")
    try:
        size = int(raw)
    except (TypeError, ValueError):
        size = 0
    return size if size > 0 else 8


# 阻塞式 LLM 调用专用线程池。
#
# 这类调用会被外层 asyncio.wait_for 放弃，但**线程不会随之停止**——它要一直
# 跑到传输层超时。若走 asyncio.to_thread 的默认线程池（min(32, cpu+4)，与
# starlette 的请求线程池共享语义），几个挂死的翻译请求就能把池占满，连
# /health 都排不进去。隔离到有界专用池后，最坏情况只是翻译类请求排队。
_llm_executor = ThreadPoolExecutor(
    max_workers=_resolve_llm_pool_size(),
    thread_name_prefix="llm-blocking",
)


async def run_blocking(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    return await run_in_threadpool(func, *args, **kwargs)


async def run_llm_blocking(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """在专用有界线程池里执行阻塞式 LLM 调用。

    调用方仍需自己用 ``asyncio.wait_for`` 设整体预算——本函数只保证超时后
    滞留的线程不会污染通用请求线程池。
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _llm_executor, functools.partial(func, *args, **kwargs)
    )
