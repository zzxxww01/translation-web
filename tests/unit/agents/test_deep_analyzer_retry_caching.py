"""回归测试：Phase0 重试时复用已成功的术语验证结果，不重复调用 LLM（finding 30）。"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.agents.deep_analyzer import DeepAnalyzer
from src.core.models import Paragraph, Section, ParagraphStatus
from src.llm.usage_metrics import LLMUsageMetrics


class _FakeLLM:
    def __init__(self):
        self.deep_calls = 0
        self.verify_calls = 0

    def deep_analyze_document(self, outline, sampled_text, timeout=None):
        self.deep_calls += 1
        if self.deep_calls == 1:
            raise RuntimeError("deadline exceeded")  # 可重试
        return {
            "theme": "主题",
            "key_arguments": ["论点1"],
            "structure_summary": "结构",
            "terminology": [],
            "style": {"tone": "professional", "target_audience": "工程师", "translation_voice": "专业"},
            "challenges": [],
            "guidelines": ["指南1"],
        }

    def verify_high_frequency_terms(self, sampled_text, high_freq_candidates, timeout=None):
        self.verify_calls += 1
        return [{"term": "GPU", "is_technical_term": True, "translation": "图形处理器"}]

    def generate(self, prompt, response_format=None, timeout=None):
        return '{"section_roles": {}}'

    def _parse_json_response(self, response):
        import json
        return json.loads(response)

    class prompt_manager:
        @staticmethod
        def get(name, **kwargs):
            return "prompt"


def _section(sid: str) -> Section:
    paras = [
        Paragraph(id=f"{sid}-p{i}", index=i, source="The GPU runs CUDA " * 30,
                  status=ParagraphStatus.PENDING)
        for i in range(3)
    ]
    return Section(section_id=sid, title=f"Sec {sid}", paragraphs=paras)


def test_term_verification_not_repeated_across_deep_retry():
    llm = _FakeLLM()
    analyzer = DeepAnalyzer(llm_provider=llm, max_sample_chars=2000)

    analysis = analyzer.analyze([_section("s1"), _section("s2")])

    # 深度分析重试了一次（共 2 次），术语验证只在首轮成功后被复用，仅 1 次
    assert llm.deep_calls == 2
    assert llm.verify_calls == 1
    assert analysis.theme == "主题"


def test_phase_zero_worker_calls_keep_run_context():
    metrics = LLMUsageMetrics()
    metrics.start_run("phase-zero-run", project_id="demo")

    class _MetricsLLM(_FakeLLM):
        def deep_analyze_document(self, outline, sampled_text, timeout=None):
            metrics.record_call(
                provider="fake",
                model="analysis",
                duration_seconds=0,
                success=True,
            )
            return {
                "theme": "主题",
                "key_arguments": ["论点1"],
                "structure_summary": "结构",
                "terminology": [],
                "style": {
                    "tone": "professional",
                    "target_audience": "工程师",
                    "translation_voice": "专业",
                },
                "challenges": [],
                "guidelines": ["指南1"],
            }

        def verify_high_frequency_terms(
            self,
            sampled_text,
            high_freq_candidates,
            timeout=None,
        ):
            metrics.record_call(
                provider="fake",
                model="term-verification",
                duration_seconds=0,
                success=True,
            )
            return []

    DeepAnalyzer(_MetricsLLM(), max_sample_chars=2000).analyze([_section("s1")])

    assert metrics.summary("phase-zero-run")["api_calls"] == 2
    assert metrics.summary("__unscoped__")["api_calls"] == 0
