"""回归测试：memory_service 的健壮性修复（缓存失效、去重、过滤、窗口合并）。"""

import pytest

from src.services import memory_service as ms
from src.services.memory_service import (
    MAX_RULES_HARD_CAP,
    TranslationMemoryService,
)


@pytest.fixture
def service(tmp_path, monkeypatch):
    path = tmp_path / "global_memory.md"
    monkeypatch.setattr(ms, "GLOBAL_MEMORY_PATH", path)
    # 隔离类级共享缓存，避免跨测试污染
    monkeypatch.setattr(TranslationMemoryService, "_cache", {})
    monkeypatch.setattr(TranslationMemoryService, "_cache_mtime", {})
    return TranslationMemoryService(llm_provider=object())


def test_cache_invalidates_on_external_write(service, tmp_path, monkeypatch):
    service._append_rules(["规则一"])
    assert service.get_all_rules() == ["规则一"]

    # 另一个实例（共享类级缓存）追加后，第一个实例应能看到（缓存按 mtime 失效）
    other = TranslationMemoryService(llm_provider=object())
    other._append_rules(["规则二"])

    assert "规则二" in service.get_all_rules()


def test_term_like_rules_filtered_out(service):
    service._append_rules([
        "保持长句拆分为短句",
        'GPU 翻译为 图形处理器',  # 术语型，应被过滤
        "TSMC 译为 台积电",       # 术语型，应被过滤
    ])
    rules = service.get_all_rules()
    assert "保持长句拆分为短句" in rules
    assert all("翻译为" not in r and "译为" not in r for r in rules)


def test_near_duplicate_rules_skipped(service):
    service._append_rules(["避免被动语态的堆叠使用"])
    service._append_rules(["避免被动语态的堆叠使用！"])  # 近似重复
    assert len(service.get_all_rules()) == 1


def test_exact_duplicate_skipped(service):
    service._append_rules(["规则A"])
    service._append_rules(["规则A"])
    assert service.get_all_rules() == ["规则A"]


def test_diff_ratio_handles_long_text_quickly(service):
    # 不应因超长文本而卡住（内部已截断到 MAX_DIFF_CHARS）
    a = "甲" * 200000
    b = "乙" * 200000
    ratio = service._compute_diff_ratio(a, b)
    assert 0.0 <= ratio <= 1.0


def test_is_term_rule_detection():
    assert TranslationMemoryService._is_term_rule("API 翻译为 接口") is True
    assert TranslationMemoryService._is_term_rule("长句应拆分") is False
