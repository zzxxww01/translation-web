"""回归测试：gemini 限流重试的退避策略（finding 21）。

修复前缺陷：
1. 限流（429）换 key 时零延迟，会瞬间把所有 key 逐个撞限流烧光。
2. 指数退避计数器只在最终路由分支递增，key 轮换期间恒为 0，2**n 退避不增长。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import src.llm.gemini as gemini_mod
from src.llm.gemini import GeminiGenerationResult, GeminiProvider
from src.llm.usage_metrics import llm_usage_metrics


def _make_provider():
    p = GeminiProvider.__new__(GeminiProvider)
    p.api_keys = ["k1", "k2"]
    p.backup_model = None
    p.model_name = "m"
    p.max_attempts = 5
    p.retry_delay = 0.5
    p.request_timeout = 30
    return p


def test_rate_limit_backs_off_during_key_rotation_and_grows(monkeypatch):
    p = _make_provider()

    # 始终抛 429
    def _always_429(**kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED rate limit")

    monkeypatch.setattr(p, "_generate_once", _always_429)

    sleeps = []
    monkeypatch.setattr(gemini_mod.time, "sleep", lambda s: sleeps.append(round(s, 3)))

    try:
        p.generate("prompt")
    except Exception:
        pass

    # 计划 2 个 key、max_attempts=5。修复后退避序列应为：
    #   换 key 前退避(0.5) → 最终路由 1.0 → 2.0 → 4.0
    # 关键点：第一个 0.5 发生在“换 key”阶段（修复前此处零延迟），
    # 且退避随单调计数器指数增长（修复前轮换期间计数器不增长）。
    assert sleeps == [0.5, 1.0, 2.0, 4.0], sleeps
    # 严格单调递增，证明退避计数器贯穿整个循环
    assert all(b > a for a, b in zip(sleeps, sleeps[1:]))


def test_non_rate_limit_transient_rotates_without_backoff(monkeypatch):
    """非限流的暂时性错误（如 503）换 key 时不应额外退避，保持快速轮换。"""
    p = _make_provider()

    def _always_503(**kwargs):
        raise RuntimeError("503 service unavailable")

    monkeypatch.setattr(p, "_generate_once", _always_503)

    sleeps = []
    monkeypatch.setattr(gemini_mod.time, "sleep", lambda s: sleeps.append(round(s, 3)))

    try:
        p.generate("prompt")
    except Exception:
        pass

    # 第一次换 key 不退避；之后最终路由用 _retry_delay_for_error 的非限流分支（平坦小延迟）
    # 因此 sleeps 数量比限流场景少一次（没有换 key 退避），且首个延迟不是限流退避。
    assert len(sleeps) == 3, sleeps


def test_success_records_provider_token_usage(monkeypatch):
    p = _make_provider()
    monkeypatch.setattr(p, "_use_rest_transport", lambda: False)
    monkeypatch.setattr(
        p,
        "_generate_once",
        lambda **_kwargs: GeminiGenerationResult(
            text=" translated ",
            input_tokens=12,
            output_tokens=7,
            total_tokens=19,
        ),
    )
    run_id = "gemini-token-usage"
    llm_usage_metrics.start_run(run_id, project_id="demo")
    try:
        assert p.generate("source") == "translated"
        summary = llm_usage_metrics.summary(run_id)
        assert summary["api_calls"] == 1
        assert summary["input_tokens"] == 12
        assert summary["output_tokens"] == 7
        assert summary["total_tokens"] == 19
    finally:
        llm_usage_metrics.finish_run(run_id)
