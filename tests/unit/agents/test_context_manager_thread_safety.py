"""回归测试：LayeredContextManager 的线程安全术语追踪访问器与并发正确性。

批量翻译流程现在通过 asyncio.to_thread 真并发执行章节翻译，多个工作线程会并发
读写共享的 term_tracker / section_translations。这些测试锁定加锁访问器的语义，
并以多线程压力测试验证不会出现 "dict changed size during iteration" 等竞态。
"""

import threading

from src.agents.context_manager import LayeredContextManager


def test_accessor_semantics():
    cm = LayeredContextManager()

    assert cm.has_term_usage("GPU") is False

    cm.record_term_usage("GPU", "图形处理器", "s0")

    # 大小写不敏感
    assert cm.has_term_usage("gpu") is True
    assert cm.get_preferred_term_translation("GPU") == "图形处理器"

    snap = cm.snapshot_term_usage()
    assert snap["gpu"] == ["图形处理器"]

    # 快照是拷贝：修改快照不影响内部状态
    snap["gpu"].append("污染")
    assert cm.snapshot_term_usage()["gpu"] == ["图形处理器"]


def test_concurrent_term_and_translation_no_race():
    cm = LayeredContextManager()
    errors = []
    workers = 8
    per_worker = 200

    def worker(n: int):
        try:
            for i in range(per_worker):
                term = f"term{n}_{i}"
                cm.record_term_usage(term, f"t{i}", f"s{n}")
                cm.has_term_usage(term)
                cm.snapshot_term_usage()  # 并发快照不应抛 dict changed size
                cm.record_translation(f"s{n}", f"src{i}", f"dst{i}", {term: f"t{i}"})
        except Exception as e:  # noqa: BLE001 - 收集任何竞态异常
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"并发访问出现异常: {errors[:3]}"

    snap = cm.snapshot_term_usage()
    # 每个 worker 写入 per_worker 个不同术语，全部应被记录
    assert len(snap) == workers * per_worker

    # section_translations 每个 section 应有 per_worker 条记录
    all_trans = cm.get_all_translations()
    assert len(all_trans) == workers
    for n in range(workers):
        assert len(all_trans[f"s{n}"]) == per_worker
