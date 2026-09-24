"""Process-wide, provider-scoped admission control for actual transport calls.

The permit remains held until the synchronous network operation really ends,
including after its caller times out. RPM counts starts, not successful results.
Multiple server processes need an external/distributed quota coordinator.
"""
from __future__ import annotations

import time
from collections import deque
from contextlib import contextmanager
from threading import Condition, Lock

from .execution_context import check_active, current_route, remaining_timeout


class ProviderLimiter:
    def __init__(self, max_concurrent: int, requests_per_minute: int):
        self.max_concurrent = max_concurrent
        self.requests_per_minute = requests_per_minute
        self.condition = Condition()
        self.running = 0
        self.starts: deque[float] = deque()

    @contextmanager
    def acquire(self):
        with self.condition:
            while True:
                check_active()
                now = time.monotonic()
                while self.starts and self.starts[0] <= now - 60.0:
                    self.starts.popleft()
                if self.running < self.max_concurrent and len(self.starts) < self.requests_per_minute:
                    self.running += 1
                    self.starts.append(now)
                    break
                quota_wait = max(0.001, self.starts[0] + 60.0 - now) if len(self.starts) >= self.requests_per_minute else 0.1
                budget = remaining_timeout()
                self.condition.wait(min(quota_wait, 0.1, budget if budget is not None else 0.1))
        try:
            yield
        finally:
            with self.condition:
                self.running -= 1
                self.condition.notify_all()


_lock = Lock()
_limiters: dict[str, ProviderLimiter] = {}


@contextmanager
def transport_slot():
    route = current_route()
    config = route.get("rate_limit")
    check_active()
    if config is None:
        from .work_budget import admit_transport
        admit_transport()
        yield
        return
    key = route["provider_id"]
    with _lock:
        limiter = _limiters.get(key)
        if limiter is None:
            limiter = _limiters[key] = ProviderLimiter(config.max_concurrent, config.requests_per_minute)
        elif (limiter.max_concurrent, limiter.requests_per_minute) != (config.max_concurrent, config.requests_per_minute):
            # Config changes take effect on restart; never split one quota into
            # two independent buckets while old requests are still in flight.
            raise ValueError("Provider rate_limit changed; restart workers to apply it")
    with limiter.acquire():
        check_active()
        from .work_budget import admit_transport
        admit_transport()
        yield
