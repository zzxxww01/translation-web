"""回归测试：get_rules_for_prompt 必须注入最新规则，而非最旧的前 N 条。

此前实现用 rules[:MAX_RULES_IN_PROMPT] 取列表开头（最旧）的规则，导致一旦
规则总数超过上限，新学习成果永远排在上限之后、注入不进 prompt，自学习闭环失效。
"""

from src.services.memory_service import (
    GLOBAL_MEMORY_PATH,
    MAX_RULES_CHARS,
    MAX_RULES_IN_PROMPT,
    TranslationMemoryService,
)


def _service_with_rules(rules):
    svc = TranslationMemoryService(llm_provider=object())
    # 直接注入内存缓存，绕过磁盘读写，保证测试隔离与确定性
    svc._cache[str(GLOBAL_MEMORY_PATH)] = list(rules)
    return svc


def test_returns_newest_rules_when_over_limit():
    rules = [f"rule-{i}" for i in range(MAX_RULES_IN_PROMPT + 5)]
    svc = _service_with_rules(rules)

    selected = svc.get_rules_for_prompt()

    # 取最新的 MAX_RULES_IN_PROMPT 条，且在窗口内保持时间顺序（旧→新）
    assert selected == rules[-MAX_RULES_IN_PROMPT:]
    # 最新规则必须在内
    assert rules[-1] in selected
    # 超出窗口的最旧规则必须被排除
    assert rules[0] not in selected


def test_respects_char_budget_taking_newest_first():
    big = "x" * 500
    # 最旧在前，最新在后；最新两条各 500 字符，叠加超过 600 上限
    rules = ["old-small-rule", big + "-a", big + "-b"]
    svc = _service_with_rules(rules)

    selected = svc.get_rules_for_prompt()

    # 仅最新一条（500）在预算内，第二条会让累计超 600 而停止
    assert selected == [rules[-1]]


def test_under_limit_returns_all_in_order():
    rules = ["r1", "r2", "r3"]
    svc = _service_with_rules(rules)

    assert svc.get_rules_for_prompt() == rules


def test_empty_returns_empty():
    svc = _service_with_rules([])
    assert svc.get_rules_for_prompt() == []
