"""回归测试：纯修订模式只处理有问题的段落，避免对无问题段落做不必要的 LLM 改写（finding 47）。"""

from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.core.format_tokens import TranslationPayload
from src.core.models import (
    Paragraph,
    ParagraphStatus,
    ReflectionResult,
    Section,
    SectionUnderstanding,
    TranslationIssue,
)


class _RecordingLLM:
    def __init__(self):
        self.received_pairs = []

    def refine_and_polish_batch(self, pairs, context):
        # 记录本次批量收到的 pair 数，并原样回显译文
        self.received_pairs.extend(pairs)
        return [p["translation"] for p in pairs]


def _section(n=4):
    return Section(
        section_id="s1", title="S",
        paragraphs=[
            Paragraph(id=f"p{i}", index=i, source=f"source {i}", status=ParagraphStatus.PENDING)
            for i in range(n)
        ],
    )


def _reflection(issues):
    return ReflectionResult(
        overall_score=8.6, terminology_score=9, accuracy_score=9,
        fluency_score=9, conciseness_score=9, consistency_score=9,
        logic_score=9, issues=issues,
    )


def _understanding():
    return SectionUnderstanding(role_in_article="body", relation_to_previous="",
                                relation_to_next="", key_points=[], translation_notes=[])


def _payloads(n=4):
    return [TranslationPayload(text=f"译文{i}") for i in range(n)]


def test_refine_only_processes_paragraphs_with_issues():
    llm = _RecordingLLM()
    tr = FourStepTranslator(llm, LayeredContextManager())
    section = _section(4)
    # 只有第 1 段有问题
    issue = TranslationIssue(paragraph_index=1, priority="P1", issue_type="accuracy",
                             description="x", suggestion="y")

    out = tr._step_refine_and_polish(
        section, _payloads(4), _reflection([issue]), _understanding(),
        issues_filter=[issue], polish_all=False,
    )

    # 仅 1 段被送往 LLM
    assert len(llm.received_pairs) == 1
    # 其余段落保留初译
    assert out[0].text == "译文0"
    assert out[2].text == "译文2"
    assert out[3].text == "译文3"


def test_polish_all_processes_every_paragraph():
    llm = _RecordingLLM()
    tr = FourStepTranslator(llm, LayeredContextManager())
    section = _section(4)
    issue = TranslationIssue(paragraph_index=1, priority="P1", issue_type="accuracy",
                             description="x", suggestion="y")

    tr._step_refine_and_polish(
        section, _payloads(4), _reflection([issue]), _understanding(),
        issues_filter=[issue], polish_all=True,
    )

    # 风格润色覆盖全部 4 段
    assert len(llm.received_pairs) == 4
