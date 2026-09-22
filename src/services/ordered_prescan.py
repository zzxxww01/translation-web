"""Bounded pure workers, deterministic source-order application, safe cancellation."""
import asyncio
from collections import deque


async def ordered_map(items, scan, commit, *, concurrency=1, should_cancel=lambda: False):
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError("concurrency must be positive")
    source = iter(items)
    pending = deque()
    results = []

    def enqueue():
        try:
            item = next(source)
        except StopIteration:
            return
        pending.append((item, asyncio.create_task(scan(item))))

    try:
        for _ in range(concurrency):
            enqueue()
        while pending:
            if should_cancel():
                break
            item, task = pending[0]
            result = await task  # completion order never changes commit order
            pending.popleft()
            if should_cancel():
                break
            await commit(item, result)
            results.append(result)
            enqueue()
    finally:
        for _, task in pending:
            task.cancel()
        await asyncio.gather(*(task for _, task in pending), return_exceptions=True)
    return results
