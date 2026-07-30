# -*- coding: utf-8 -*-
"""帖子翻译回归样例的结构校验。

样例文件本身是人工维护的「期望译文」语料，用于沉淀典型失败模式。这里只做
**离线**结构断言（不花 CI 时间调 LLM）；调用真实模型的语义校验需显式设置
``RUN_LLM_TESTS=1``。
"""

import json
import os
from pathlib import Path

import pytest

CASES_PATH = Path(__file__).parent / "post_translation_regression_cases.json"

REQUIRED_FIELDS = {
    "id",
    "category",
    "target_style",
    "source",
    "expected_translation",
    "must_include",
    "should_avoid",
    "notes",
}


def _load_cases() -> list[dict]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return payload["cases"]


def test_cases_file_is_valid_json_with_enough_coverage():
    cases = _load_cases()
    assert len(cases) >= 7, "回归样例太少，覆盖不到主要失败模式"


def test_every_case_has_required_fields():
    for case in _load_cases():
        missing = REQUIRED_FIELDS - set(case)
        assert not missing, f"样例 {case.get('id')} 缺字段: {sorted(missing)}"


def test_case_ids_are_unique():
    ids = [case["id"] for case in _load_cases()]
    assert len(ids) == len(set(ids)), "样例 id 重复"


def test_expected_translations_are_non_empty():
    for case in _load_cases():
        assert case["expected_translation"].strip(), f"样例 {case['id']} 没有期望译文"
        assert case["source"].strip(), f"样例 {case['id']} 没有原文"


def test_expected_translation_never_contains_its_own_should_avoid():
    """期望译文自己不能命中 should_avoid——否则这条样例自相矛盾。"""
    for case in _load_cases():
        for banned in case["should_avoid"]:
            assert banned not in case["expected_translation"], (
                f"样例 {case['id']} 的期望译文包含了它自己禁止的表达: {banned}"
            )


def test_expected_translation_contains_its_must_include():
    for case in _load_cases():
        for required in case["must_include"]:
            assert required in case["expected_translation"], (
                f"样例 {case['id']} 的期望译文缺少必含内容: {required}"
            )


@pytest.mark.skipif(
    not os.getenv("RUN_LLM_TESTS"),
    reason="需要真实 LLM 调用，设置 RUN_LLM_TESTS=1 后运行",
)
def test_live_translation_satisfies_case_constraints():
    """用真实模型跑一遍，检查 must_include / should_avoid。

    这是人工验收用的慢测试，不进常规 CI。
    """
    from src.api.utils.llm_factory import create_llm_provider
    from src.prompts import prompt_manager

    provider = create_llm_provider()
    failures: list[str] = []
    for case in _load_cases():
        prompt = prompt_manager.get(
            "post_translation", dynamic_sections="", text=case["source"]
        )
        output = provider.generate(prompt)
        for required in case["must_include"]:
            if required not in output:
                failures.append(f"{case['id']}: 缺少 {required!r}\n  输出: {output}")
        for banned in case["should_avoid"]:
            if banned in output:
                failures.append(f"{case['id']}: 出现禁止表达 {banned!r}\n  输出: {output}")
    assert not failures, "\n".join(failures)
