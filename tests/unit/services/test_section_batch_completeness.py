# -*- coding: utf-8 -*-
"""section 模式必须分批，并且不得静默丢段。

此前整章拼成一个 prompt 发一次调用，既没有按段数/字符数切批，也没有任何完整性
校验：模型只吐出前几十段时，其余段落既不报错也不重试地留在未翻译状态，而本次
运行仍然报「成功」。语料里 ClusterMAX 有 5 个单章 >3500 词的章节会稳定触发。
"""

import asyncio
from types import SimpleNamespace

import pytest

from src.services.batch_translation_service import BatchTranslationService


def _service() -> BatchTranslationService:
    return BatchTranslationService.__new__(BatchTranslationService)


def _lines(count: int, chars: int = 100):
    ids = [f"p{i:03d}" for i in range(count)]
    lines = [f"[{pid}] " + "x" * chars for pid in ids]
    return lines, ids


# --- 分批 -------------------------------------------------------------------


def test_small_section_stays_one_batch():
    lines, ids = _lines(5)
    batches = _service()._split_section_batches(lines, ids)
    assert len(batches) == 1
    assert batches[0][1] == ids


def test_batch_splits_on_paragraph_count():
    count = BatchTranslationService.MAX_SECTION_BATCH_PARAGRAPHS * 2 + 3
    lines, ids = _lines(count, chars=10)
    batches = _service()._split_section_batches(lines, ids)
    assert len(batches) == 3
    assert all(
        len(batch_ids) <= BatchTranslationService.MAX_SECTION_BATCH_PARAGRAPHS
        for _, batch_ids in batches
    )


def test_batch_splits_on_char_budget():
    # 段数没超，但字符数超了，同样要切
    lines, ids = _lines(10, chars=BatchTranslationService.MAX_SECTION_BATCH_CHARS // 3)
    batches = _service()._split_section_batches(lines, ids)
    assert len(batches) > 1


def test_every_paragraph_appears_exactly_once():
    lines, ids = _lines(137, chars=500)
    batches = _service()._split_section_batches(lines, ids)
    flat = [pid for _, batch_ids in batches for pid in batch_ids]
    assert flat == ids


def test_single_oversized_paragraph_still_forms_a_batch():
    lines, ids = _lines(1, chars=BatchTranslationService.MAX_SECTION_BATCH_CHARS * 3)
    batches = _service()._split_section_batches(lines, ids)
    assert len(batches) == 1
    assert batches[0][1] == ids


# --- 缺段重试 ---------------------------------------------------------------


class _Recorder:
    """记录每次请求的段落 id，并按脚本决定返回哪些。"""

    def __init__(self, drop_ids):
        self.drop_ids = set(drop_ids)
        self.requests = []

    async def call(self, *, provider, section, context, format_tokens, batch_lines, batch_ids):
        self.requests.append(list(batch_ids))
        return [
            {"id": pid, "translation": f"译文-{pid}"}
            for pid in batch_ids
            if pid not in self.drop_ids
        ]


def _retry(service, recorder, lines, ids, translated):
    service._call_section_batch = recorder.call
    return asyncio.run(
        service._retry_missing_paragraphs(
            provider=SimpleNamespace(),
            section=SimpleNamespace(section_id="s1", title="S"),
            context={},
            format_tokens=[],
            section_lines=lines,
            paragraph_ids=ids,
            translated=translated,
        )
    )


def test_missing_paragraphs_are_retried_and_recovered():
    lines, ids = _lines(10)
    # 首轮只返回前 4 段
    first_round = [{"id": pid, "translation": "t"} for pid in ids[:4]]
    recorder = _Recorder(drop_ids=set())

    result = _retry(_service(), recorder, lines, ids, list(first_round))

    returned = {item["id"] for item in result}
    assert returned == set(ids), "缺失段落没有被补齐"
    assert recorder.requests, "根本没有触发重试"
    assert set(recorder.requests[0]) == set(ids[4:])


def test_no_retry_when_everything_returned():
    lines, ids = _lines(6)
    complete = [{"id": pid, "translation": "t"} for pid in ids]
    recorder = _Recorder(drop_ids=set())

    result = _retry(_service(), recorder, lines, ids, list(complete))

    assert recorder.requests == [], "全部返回时不该发起重试"
    assert len(result) == len(ids)


def test_blank_translation_counts_as_missing():
    lines, ids = _lines(3)
    partial = [
        {"id": ids[0], "translation": "t"},
        {"id": ids[1], "translation": "   "},  # 空白等同于没翻
    ]
    recorder = _Recorder(drop_ids=set())

    result = _retry(_service(), recorder, lines, ids, list(partial))

    assert set(recorder.requests[0]) == {ids[1], ids[2]}
    good = {
        item["id"] for item in result
        if isinstance(item.get("translation"), str) and item["translation"].strip()
    }
    assert good == set(ids)


def test_permanently_missing_paragraphs_are_reported(caplog):
    lines, ids = _lines(4)
    # 模型始终不返回最后一段
    recorder = _Recorder(drop_ids={ids[-1]})
    partial = [{"id": pid, "translation": "t"} for pid in ids[:-1]]

    with caplog.at_level("ERROR"):
        _retry(_service(), recorder, lines, ids, list(partial))

    assert any("still untranslated" in record.message for record in caplog.records), (
        "补不齐时必须留下明确错误，不能让运行伪装成功"
    )


def test_retry_uses_smaller_batches():
    count = BatchTranslationService.MAX_SECTION_BATCH_PARAGRAPHS
    lines, ids = _lines(count)
    recorder = _Recorder(drop_ids=set())

    _retry(_service(), recorder, lines, ids, [])

    assert recorder.requests
    retry_size = max(1, BatchTranslationService.MAX_SECTION_BATCH_PARAGRAPHS // 4)
    assert all(len(req) <= retry_size for req in recorder.requests)
