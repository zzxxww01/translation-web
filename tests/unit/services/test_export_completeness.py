"""Regression tests for read-only Chinese export completeness and its QA gate."""
import json

import pytest

from src.core.models import ElementType, Paragraph, Section
from src.core.project_export_service import ExportBlockedError
from src.core.export_completeness import build_translation_completeness
from test_project_export_service import _build_service, _demo_meta


def test_reports_missing_titles_and_body_locations_without_mutation():
    sections = [Section(section_id="s1", title="Market outlook", paragraphs=[
        Paragraph(id="p1", index=4, source="Demand is growing."),
        Paragraph(id="p2", index=5, source="Supply is limited.", confirmed="Supply remains limited."),
        Paragraph(id="p3", index=6, source="Costs are falling.", confirmed="成本正在下降。"),
    ])]
    before = [s.model_dump() for s in sections]
    report = build_translation_completeness(sections)
    assert report["is_complete"] is False
    assert report["missing_title_count"] == 1
    assert report["missing_body_count"] == 2
    assert report["missing_count"] == 3
    assert report["items"][1]["paragraph_id"] == "p1"
    assert report["items"][1]["paragraph_index"] == 4
    assert report["items"][1]["section_id"] == "s1"
    assert [s.model_dump() for s in sections] == before


@pytest.mark.parametrize("brand", ["OpenAI", "AMD", "NVIDIA", "Anthropic", "Google Cloud", "GPT-4", "CoreWeave", "vLLM", "Claude", "[OpenAI](https://openai.com)"])
def test_brand_only_metadata_images_code_and_numeric_tables_are_not_missing(brand):
    section = Section(section_id="s1", title=brand, paragraphs=[
        Paragraph(id="brand", index=0, source=brand, confirmed=brand),
        Paragraph(id="image", index=1, source="![English caption](image.png)", element_type=ElementType.IMAGE),
        Paragraph(id="meta", index=2, source="Written by John Smith", is_metadata=True),
        Paragraph(id="code", index=3, source="print('hello')", element_type=ElementType.CODE),
        Paragraph(id="table", index=4, source="| 2025 | 12 |\n| --- | --- |", element_type=ElementType.TABLE),
    ])
    assert build_translation_completeness([section])["is_complete"] is True


@pytest.mark.parametrize("replacement", ["OpenAI", "123", "Demand remains high."])
def test_replacing_prose_with_brand_or_number_is_not_a_chinese_translation(replacement):
    section = Section(section_id="s", title="Market outlook", title_translation=replacement, paragraphs=[
        Paragraph(id="p", index=0, source="Demand is growing.", confirmed=replacement),
    ])
    assert build_translation_completeness([section])["missing_count"] == 2


def test_chinese_and_synthetic_titles_are_not_missing():
    section = Section(section_id="intro", title="Introduction", synthetic=True, paragraphs=[
        Paragraph(id="p", index=0, source="中文原文。"),
    ])
    assert build_translation_completeness([section])["missing_count"] == 0


def test_incomplete_export_blocks_preserves_report_and_one_time_override(tmp_path):
    section = Section(section_id="s", title="Market outlook", paragraphs=[
        Paragraph(id="p", index=0, source="Demand is growing."),
    ])
    service = _build_service(tmp_path, [section], _demo_meta())
    def write_json(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    service._write_json = write_json
    with pytest.raises(ExportBlockedError, match="章节标题 1.*正文 1") as blocked:
        service.export("demo")
    assert blocked.value.blocked_path is not None
    assert blocked.value.blocked_path.exists()
    assert not service.get_export_path("demo").exists()
    report_path = tmp_path / "demo/artifacts/export-lint/latest.json"
    report = json.loads(report_path.read_text())
    assert report["translation_completeness"]["missing_count"] == 2
    assert any(i["type"] == "qa_missing_translation" for i in report["issues"])
    content = service.export("demo", allow_qa_override=True)
    assert "Demand is growing." in content
    assert json.loads(report_path.read_text())["qa_override_requested"] is True
    with pytest.raises(ExportBlockedError):
        service.export("demo")
    (tmp_path / "demo/source_en.md").write_text("# Original\n\nDemand is growing.")
    assert service.export("demo", format="en") == "# Original\n\nDemand is growing."


def test_fully_translated_export_passes(tmp_path):
    section = Section(section_id="s", title="Market outlook", title_translation="市场展望", paragraphs=[
        Paragraph(id="p", index=0, source="Demand is growing.", confirmed="需求正在增长。"),
        Paragraph(id="brand", index=1, source="OpenAI", confirmed="OpenAI"),
    ])
    service = _build_service(tmp_path, [section], _demo_meta())
    assert "需求正在增长" in service.export("demo")
    payload = service.build_export_lint_payload(_demo_meta(), [section])
    assert payload["translation_completeness"]["is_complete"] is True
    assert not any(i["type"] in {"missing_translation", "untranslated_paragraph", "qa_missing_translation"} for i in payload["issues"])
