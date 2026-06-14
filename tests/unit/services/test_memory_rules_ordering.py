"""回归测试：get_rules_for_prompt 必须注入最新规则，而非最旧的前 N 条。

此前实现用 rules[:MAX_RULES_IN_PROMPT] 取列表开头（最旧）的规则，导致一旦
规则总数超过上限，新学习成果永远排在上限之后、注入不进 prompt，自学习闭环失效。

用临时文件隔离，避免触碰真实 data/global_memory.md，并规避类级共享缓存的跨测试污染。
"""

import pytest

from src.services import memory_service as ms
from src.services.memory_service import (
    MAX_RULES_IN_PROMPT,
    TranslationMemoryService,
)


@pytest.fixture
def service(tmp_path, monkeypatch):
    path = tmp_path / "global_memory.md"
    monkeypatch.setattr(ms, "GLOBAL_MEMORY_PATH", path)
    svc = TranslationMemoryService(llm_provider=object())
    return svc


def _write_rules(service, rules):
    # 经由内部存储写入（含 mtime 缓存刷新），模拟真实落盘顺序（最旧在前）
    service._save_rules(list(rules))


def test_returns_newest_rules_when_over_limit(service):
    rules = [f"rule-{i}" for i in range(MAX_RULES_IN_PROMPT + 5)]
    _write_rules(service, rules)

    selected = service.get_rules_for_prompt()

    assert selected == rules[-MAX_RULES_IN_PROMPT:]
    assert rules[-1] in selected
    assert rules[0] not in selected


def test_respects_char_budget_taking_newest_first(service):
    big = "x" * 500
    rules = ["old-small-rule", big + "-a", big + "-b"]
    _write_rules(service, rules)

    selected = service.get_rules_for_prompt()

    assert selected == [rules[-1]]


def test_under_limit_returns_all_in_order(service):
    rules = ["r1", "r2", "r3"]
    _write_rules(service, rules)

    assert service.get_rules_for_prompt() == rules


def test_empty_returns_empty(service):
    assert service.get_rules_for_prompt() == []
