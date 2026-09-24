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


def test_opposite_instruction_is_not_dropped_as_a_near_duplicate(service):
    service._append_rules(['必要的转折连接词应该保留'])
    service._append_rules(['必要的转折连接词不应该保留'])
    assert len(service.get_all_rules()) == 2


def test_failed_atomic_write_does_not_leak_new_rule_into_cache(service, monkeypatch):
    service._append_rules(['原有规则'])
    from src.core import file_utils
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(file_utils, 'write_text_atomic', fail)
    with pytest.raises(OSError):
        service._append_rules(['没有落盘的规则'])
    assert service.get_all_rules() == ['原有规则']


def test_corrupt_rule_file_is_not_overwritten_with_an_empty_library(service):
    ms.GLOBAL_MEMORY_PATH.write_bytes(b'\xff\xfe invalid UTF8')
    with pytest.raises(UnicodeDecodeError):
        service._append_rules(['新规则'])
    assert ms.GLOBAL_MEMORY_PATH.read_bytes() == b'\xff\xfe invalid UTF8'


def test_lock_failure_never_falls_through_to_unlocked_write(service, monkeypatch):
    import portalocker
    def fail(*args, **kwargs):
        raise portalocker.exceptions.LockException('busy')
    monkeypatch.setattr(portalocker, 'Lock', fail)
    with pytest.raises(portalocker.exceptions.LockException):
        service._append_rules(['不应写入'])
    assert not ms.GLOBAL_MEMORY_PATH.exists()


def test_overlong_newest_rule_does_not_hide_all_other_rules(service):
    service._append_rules(['仍应生效的规则', 'x' * 1000])
    assert service.get_rules_for_prompt() == ['仍应生效的规则']
