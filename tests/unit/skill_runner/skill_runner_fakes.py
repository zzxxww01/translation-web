"""skill-runner 测试替身：假会话代替 Claude，不需要装 claude-agent-sdk。"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from skill_runner.config import Config
from skill_runner.runner import SessionSpec


class FakeSession:
    def __init__(self, spec: SessionSpec):
        self.spec = spec
        self.sent: list[str] = []
        self.closed = False
        self.interrupted = False
        self._queue: asyncio.Queue = asyncio.Queue()

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def interrupt(self) -> None:
        self.interrupted = True

    async def close(self) -> None:
        self.closed = True
        self._queue.put_nowait(None)

    async def events(self):
        while True:
            item = await self._queue.get()
            if item is None:
                return
            if isinstance(item, BaseException):
                raise item
            yield item

    # ---- 测试里模拟 Claude 的行为 ----

    def push(self, event: Any) -> None:
        self._queue.put_nowait(event)

    def end_stream(self) -> None:
        self._queue.put_nowait(None)


class FakeFactory:
    def __init__(self):
        self.sessions: list[FakeSession] = []
        self.fail_with: Exception | None = None

    async def __call__(self, spec: SessionSpec) -> FakeSession:
        if self.fail_with is not None:
            raise self.fail_with
        session = FakeSession(spec)
        self.sessions.append(session)
        return session

    @property
    def last(self) -> FakeSession:
        return self.sessions[-1]


def make_config(tmp_path: Path, **overrides: Any) -> Config:
    values: dict[str, Any] = {
        "home": tmp_path / "home",
        "password": "s3cret",
        "session_secret": hashlib.sha256(b"test").digest(),
        "skills": ("four-step-translate", "podcast-cn-dubber"),
        "skills_dir": tmp_path / "skills",
        "max_active": 2,
        "idle_timeout_s": 60.0,
        "cookie_secure": False,
    }
    values.update(overrides)
    return Config(**values)


async def settle(times: int = 5) -> None:
    """让后台的 pump 任务把队列里的事件处理完。"""
    for _ in range(times):
        await asyncio.sleep(0)
