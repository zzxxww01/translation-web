# -*- coding: utf-8 -*-
"""深度分析的采样预算必须随文章长度自适应。

采样预算决定了主题/论点/风格/术语这些判断能看到多少正文，而它们会注入**每一章**
的翻译提示词。此前预算写死 2000 字符，与文章长度完全解耦：16 篇语料实测覆盖率
0.68%–7.92%，最长的一篇只有 0.68% 的正文参与过判断，且没有任何告警。

同时 SmartSampler 按「预算 ÷ 章节数」分配每章配额，预算固定意味着章节一多，
中段/末段/术语密集段就永远挤不进来，四路采样退化成只取首段。
"""

from src.agents.deep_analyzer import DeepAnalyzer
from src.agents.smart_sampler import create_smart_sampler
from src.core.constants import MAX_DEEP_ANALYSIS_LENGTH
from src.core.models import Paragraph, Section


def _analyzer(max_sample_chars=None) -> DeepAnalyzer:
    analyzer = DeepAnalyzer.__new__(DeepAnalyzer)
    analyzer.max_sample_chars = max_sample_chars
    return analyzer


def _sections(count: int, paragraphs_per_section: int, chars: int):
    return [
        Section(
            section_id=f"s{index}",
            title=f"Section {index}",
            paragraphs=[
                Paragraph(id=f"s{index}-p{n}", index=n, source="x" * chars)
                for n in range(paragraphs_per_section)
            ],
        )
        for index in range(count)
    ]


def test_short_article_keeps_the_original_floor():
    # 短文行为不变，避免为了修长文而改坏已经调好的短文链路
    sections = _sections(4, 3, 500)  # 6000 字符
    assert _analyzer()._resolve_sample_budget(sections) == DeepAnalyzer.MIN_SAMPLE_CHARS


def test_long_article_scales_up_with_length():
    sections = _sections(20, 10, 500)  # 100_000 字符
    budget = _analyzer()._resolve_sample_budget(sections)
    assert budget > DeepAnalyzer.MIN_SAMPLE_CHARS
    assert budget == int(100_000 * DeepAnalyzer.SAMPLE_RATIO_OF_ARTICLE)


def test_budget_is_capped_by_the_documented_maximum():
    sections = _sections(60, 20, 800)  # 960_000 字符
    assert _analyzer()._resolve_sample_budget(sections) == MAX_DEEP_ANALYSIS_LENGTH


def test_explicit_budget_still_wins():
    # 测试与特殊调用方显式传值时不受自适应影响
    sections = _sections(20, 10, 500)
    assert _analyzer(max_sample_chars=1234)._resolve_sample_budget(sections) == 1234


def test_empty_article_falls_back_to_floor():
    assert _analyzer()._resolve_sample_budget([]) == DeepAnalyzer.MIN_SAMPLE_CHARS
    assert _analyzer()._resolve_sample_budget(_sections(2, 0, 0)) == (
        DeepAnalyzer.MIN_SAMPLE_CHARS
    )


def test_retry_steps_actually_shrink():
    # 递减重试的目的就是缩小输入以规避超时；四档必须真的递减，
    # 曾因为给每档都套上 MIN_SAMPLE_CHARS 下限而塌成同一个值、重试形同空转。
    budget = 2000
    steps = []
    for ratio in DeepAnalyzer.ANALYSIS_SAMPLE_RATIOS:
        value = max(DeepAnalyzer.RETRY_FLOOR_CHARS, int(budget * ratio))
        if value not in steps:
            steps.append(value)
    assert len(steps) >= 3
    assert steps == sorted(steps, reverse=True)


def test_many_sections_still_sample_beyond_first_paragraph():
    # 章节数一多，每章配额 = 预算 ÷ 章节数；预算固定时中段/末段永远挤不进来。
    sections = _sections(25, 8, 600)  # 120_000 字符 / 25 章
    budget = _analyzer()._resolve_sample_budget(sections)
    result = create_smart_sampler(max_total_chars=budget).sample_for_deep_analysis(
        sections, include_term_dense=True
    )
    reasons = {sample.sample_reason for sample in result.sampled_paragraphs}
    assert "first" in reasons
    assert reasons & {"middle", "last"}, "四路采样退化成了只取首段"
