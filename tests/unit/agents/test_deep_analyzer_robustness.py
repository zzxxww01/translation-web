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
