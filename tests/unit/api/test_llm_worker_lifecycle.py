import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import BoundedSemaphore, Event

import pytest

from src.api.utils import concurrency as workers
from src.llm.errors import LLMCapacityError

@pytest.fixture
def pool(monkeypatch):
    executor = ThreadPoolExecutor(max_workers=1)
    monkeypatch.setattr(workers, '_llm_executor', executor)
    monkeypatch.setattr(workers, '_llm_capacity', BoundedSemaphore(2))
    yield
    executor.shutdown(wait=True)

@pytest.mark.asyncio
async def test_request_context_is_copied_and_isolated(pool):
    variable = ContextVar('request_test', default='missing')
    async def call(value):
        token = variable.set(value)
        try:
            return await workers.run_llm_blocking(variable.get)
        finally:
            variable.reset(token)
    assert await asyncio.gather(call('A'), call('B')) == ['A', 'B']
    assert variable.get() == 'missing'

@pytest.mark.asyncio
async def test_cancelled_running_and_queued_work_retains_capacity(pool):
    entered, release, queued_called = Event(), Event(), Event()
    def blocking():
        entered.set()
        assert release.wait(3)
    first = asyncio.create_task(workers.run_llm_blocking(blocking))
    try:
        while not entered.is_set():
            await asyncio.sleep(.001)
        queued = asyncio.create_task(workers.run_llm_blocking(queued_called.set))
        await asyncio.sleep(0)
        first.cancel(); queued.cancel()
        await asyncio.gather(first, queued, return_exceptions=True)
        with pytest.raises(LLMCapacityError):
            await workers.run_llm_blocking(lambda: None)
    finally:
        release.set()
    for _ in range(100):
        try:
            assert await workers.run_llm_blocking(lambda: 7) == 7
            break
        except LLMCapacityError:
            await asyncio.sleep(.01)
    else:
        pytest.fail('capacity was not released')
    assert not queued_called.is_set()

@pytest.mark.asyncio
async def test_worker_exception_releases_slot(pool):
    def fail():
        raise ValueError('failed')
    for _ in range(4):
        with pytest.raises(ValueError, match='failed'):
            await workers.run_llm_blocking(fail)
    assert await workers.run_llm_blocking(lambda: 1) == 1

@pytest.mark.asyncio
async def test_submit_failure_releases_slot(pool, monkeypatch):
    def fail(*args):
        raise RuntimeError('closed')
    monkeypatch.setattr(workers._llm_executor, 'submit', fail)
    for _ in range(4):
        with pytest.raises(RuntimeError, match='closed'):
            await workers.run_llm_blocking(lambda: 1)
