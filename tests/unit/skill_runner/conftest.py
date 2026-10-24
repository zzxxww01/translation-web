"""skill-runner 测试夹具。替身实现见 skill_runner_fakes.py。"""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_runner.config import Config
from skill_runner.runner import Runner
from skill_runner.store import RunStore
from skill_runner_fakes import FakeFactory, make_config


@pytest.fixture
def factory() -> FakeFactory:
    return FakeFactory()


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return make_config(tmp_path)


@pytest.fixture
def store(config: Config) -> RunStore:
    return RunStore(config.runs_dir)


@pytest.fixture
def runner(config: Config, store: RunStore, factory: FakeFactory) -> Runner:
    return Runner(config, store, factory)
