"""回归测试：Phase0 深度分析的健壮性修复。

1. section role map 调用失败时，不得废弃已完成的深度分析，应对所有章节回退为
   默认 SectionUnderstanding；但取消（cancel）仍需向上传播。
2. JSON 解析类错误应被识别为可重试（缩小样本能提升 JSON 完整性）。
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest

from src.agents.deep_analyzer import DeepAnalyzer
from src.core.models import Paragraph, Section, ParagraphStatus
from src.core.models.analysis import ArticleAnalysis, ArticleStyle


def _section(section_id: str) -> Section:
    paragraphs = [
        Paragraph(id=f"{section_id}-p{i}", index=i, source="A" * 200,
                  status=ParagraphStatus.PENDING)
        for i in range(3)
    ]
    return Section(section_id=section_id, title=f"Sec {section_id}", paragraphs=paragraphs)


def _analysis() -> ArticleAnalysis:
    return ArticleAnalysis(
        theme="t",
        structure_summary="s",
        style=ArticleStyle(tone="professional", target_audience="", translation_voice=""),
    )


class _RaisingLLM:
    """generate 总是抛指定异常。"""

    def __init__(self, exc: Exception):
        self._exc = exc

    def generate(self, *a, **k):
        raise self._exc

    def _parse_json_response(self, response):  # pragma: no cover - 不会走到
        return {}

    class prompt_manager:
        @staticmethod
        def get(name, **kwargs):
            return "prompt"


def test_section_role_map_failure_falls_back_to_defaults():
    analyzer = DeepAnalyzer(llm_provider=_RaisingLLM(RuntimeError("VectorEngine request timed out")))
    sections = [_section("s1"), _section("s2")]

    roles = analyzer._analyze_all_section_roles(sections, _analysis())

    # 不抛异常；每个章节都有默认理解
    assert set(roles.keys()) == {"s1", "s2"}
    assert roles["s1"].role_in_article == "待分析"


def test_section_role_map_propagates_cancellation():
    analyzer = DeepAnalyzer(llm_provider=_RaisingLLM(RuntimeError("Translation cancelled by user")))
    sections = [_section("s1")]

    with pytest.raises(RuntimeError, match="cancel"):
        analyzer._analyze_all_section_roles(sections, _analysis())


def test_json_errors_are_retryable():
    analyzer = DeepAnalyzer(llm_provider=_RaisingLLM(RuntimeError("noop")))
    assert analyzer._should_retry_with_smaller_sample(
        ValueError("Invalid JSON response from LLM: Expecting value")
    ) is True
    assert analyzer._should_retry_with_smaller_sample(
        RuntimeError("Unterminated string starting at")
    ) is True
    # 非重试类错误仍返回 False
    assert analyzer._should_retry_with_smaller_sample(
        RuntimeError("invalid argument: bad request")
    ) is False


@pytest.mark.parametrize("value,expected", [
    (True, True), (False, False), (None, False), ("true", True), ("false", False),
    ("首现作“CoWoS（台积电晶圆级封装）”，其后保留CoWoS。", True),  # 2026-10-25 线上真实输出
    ("不需要，直接用 CoWoS", False), ("无需加注", False), ("", False),
])
def test_term_note_flag_written_as_prose_does_not_abort_analysis(value, expected):
    # 模型把 first_occurrence_note 写成说明文字时，曾因校验失败让整篇长文翻译中止
    result = {"sampled_terms": [{"term": "CoWoS", "translation": "CoWoS", "strategy": "preserve",
                                 "first_occurrence_note": value, "alternatives": "晶圆级封装", "avoid": None}]}
    analysis = DeepAnalyzer(llm_provider=_RaisingLLM(RuntimeError("unused")))._parse_combined_analysis_result(
        result, [_section("s1")])
    term = analysis.terminology[0]
    assert term.first_occurrence_note is expected
    assert term.alternatives == ["晶圆级封装"] and term.avoid == []


def test_analysis_text_fields_written_as_objects_do_not_abort_translation():
    # 2026-10-25 线上真实输出：key_arguments 每项写成 {"argument": …, "evidence": …}，ArticleAnalysis 校验失败，整篇补译中止
    from src.core.models.analysis import SectionUnderstanding, TranslationChallenge

    analysis = ArticleAnalysis(
        theme={"zh": "数据中心加速"},
        key_arguments=[{"argument": "美国超大规模云厂商开工量创新高", "evidence": "季度开工 MW 呈抛物线"}, "租约是领先指标"],
        guidelines="数字单位保留 GW",
        challenges=[TranslationChallenge(location={"section": "intro"}, issue=["FUD", "需要意译"])],
        style=ArticleStyle(tone=None, target_audience=["投资者", "行业研究员"]),
    )
    assert analysis.theme == "数据中心加速"
    assert analysis.key_arguments == ["美国超大规模云厂商开工量创新高；季度开工 MW 呈抛物线", "租约是领先指标"]
    assert analysis.guidelines == ["数字单位保留 GW"]
    assert analysis.challenges[0].issue == "FUD；需要意译" and analysis.challenges[0].suggestion is None
    assert analysis.style.target_audience == "投资者；行业研究员"
    assert SectionUnderstanding(key_points="只有一条").key_points == ["只有一条"]


def test_analysis_objects_written_as_strings_are_parsed_not_crashed_on():
    # 2026-10-25 线上真实输出：style 写成一句话，解析时 style_data.get() 抛 AttributeError，补译整篇失败
    result = {
        "theme": "数据中心加速",
        "style": "专业、数据密集，面向投资者",
        "challenges": ["FUD 一词需要意译", {"location": "intro", "issue": "数字口径"}],
        "sampled_terms": ["CoWoS", {"term": "HBM", "translation": "HBM", "strategy": "preserve"}],
        "verified_high_freq_terms": "none",
    }
    analysis = DeepAnalyzer(llm_provider=_RaisingLLM(RuntimeError("unused")))._parse_combined_analysis_result(
        result, [_section("s1")])
    assert analysis.style.translation_voice == "专业、数据密集，面向投资者"
    assert [c.issue for c in analysis.challenges] == ["FUD 一词需要意译", "数字口径"]
    assert [t.term for t in analysis.terminology] == ["HBM"]
