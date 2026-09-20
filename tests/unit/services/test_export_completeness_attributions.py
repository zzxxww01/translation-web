"""Pure author credits are not prose; source labels still need translation."""
import pytest

from src.core.export_completeness import build_translation_completeness
from src.core.models import Paragraph, Section


CREDITS = [
    "RedHat/llm-d: Michael Goin, Robert Shaw, Tyler Michael Smith",
    "LMCache/TensorMesh: Samuel Shen",
    "Weka: Callan Fox, Val Bercovici",
    "RyanLee@RyanLeeMiniMax",
]
SOURCE = "[Source: GitHub](https://github.com/NVIDIA/TensorRT-LLM/pull/17462)"


def report_for(source, translated=None):
    section = Section(section_id="s", title="正文", paragraphs=[
        Paragraph(id="p", index=7, source=source, confirmed=translated),
    ])
    before = section.model_dump()
    report = build_translation_completeness([section])
    assert section.model_dump() == before
    return report


@pytest.mark.parametrize("credit", CREDITS)
@pytest.mark.parametrize("retained", [False, True])
def test_explicit_author_credits_can_be_retained(credit, retained):
    assert report_for(credit, credit if retained else None)["is_complete"]


@pytest.mark.parametrize("source", [
    SOURCE,
    "RedHat/llm-d: Michael Goin explains the architecture.",
    "LMCache/TensorMesh: Samuel Shen improved throughput",
    "Weka: Callan Fox, Val Bercovici discuss storage",
    "Weka: Performance Is Improving",
    "Warning: System Failure",
    "Source: Michael Goin",
    "Weka:",
    "Weka: Callan Fox,",
    "Weka: Callan Fox: Performance improves",
    "Results: Demand is growing.",
    "RyanLee@RyanLeeMiniMax explains the results.",
    "Contact: support@example.com",
    "RedHat/llm-d: Michael Goin\nDemand is growing.",
])
@pytest.mark.parametrize("retained", [False, True])
def test_english_prose_and_source_labels_still_block(source, retained):
    report = report_for(source, source if retained else None)
    assert report["missing_body_count"] == 1
    assert report["items"][0]["paragraph_id"] == "p"
    assert report["items"][0]["reason"] == (
        "untranslated_text" if retained else "missing_translation"
    )


def test_only_source_label_remains_of_the_five_reported_blockers():
    sources = [*CREDITS, SOURCE]
    section = Section(section_id="s", title="正文", paragraphs=[
        Paragraph(id=f"p{i}", index=i, source=source, confirmed=source)
        for i, source in enumerate(sources)
    ])
    report = build_translation_completeness([section])
    assert report["missing_count"] == 1
    assert report["items"][0]["source_preview"] == SOURCE
    section.paragraphs[-1].confirmed = "[来源：GitHub](https://github.com/NVIDIA/TensorRT-LLM/pull/17462)"
    assert build_translation_completeness([section])["is_complete"]


@pytest.mark.parametrize("credit", CREDITS)
def test_credit_as_replacement_does_not_exempt_english_prose(credit):
    assert report_for("The system improves performance.", credit)["missing_count"] == 1
