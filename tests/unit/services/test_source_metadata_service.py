from types import SimpleNamespace
from unittest.mock import Mock

from src.core.models import Glossary, InlineElement, Paragraph, Section
from src.services.source_metadata_service import (
    SourceMetadataEntry,
    SourceMetadataTranslationService,
)


def test_source_metadata_reports_only_persisted_updates(tmp_path):
    paragraph = Paragraph(
        id="metadata-1",
        index=0,
        source="Source: estimate",
        is_metadata=True,
        metadata_type="source",
    )
    section = Section(
        section_id="s1",
        title="Sources",
        paragraphs=[paragraph],
    )

    project_manager = Mock()
    project_manager.get.return_value = SimpleNamespace(metadata=None)
    project_manager.glossary_manager.load_merged.return_value = Glossary()
    project_manager.merge_translation_updates_locked.return_value = (
        section,
        [],
        ["metadata-1"],
    )
    service = SourceMetadataTranslationService(project_manager, Mock())

    result = service.translate_project_sources(
        "demo",
        sections=[section],
        artifact_dir=tmp_path,
    )

    assert result["translated"] == 0
    assert result["applied_count"] == 0
    assert result["conflict_count"] == 1
    assert result["conflict_paragraph_ids"] == ["metadata-1"]
    project_manager.update_progress.assert_not_called()


# --- A-8："等 N 人"口径统一为"及另外 N 位作者"（N=others 原值，禁累加）---


def _byline_entry(source: str, inline_elements=None) -> SourceMetadataEntry:
    paragraph = Paragraph(
        id="byline-1",
        index=0,
        source=source,
        is_metadata=True,
        metadata_type="byline",
        inline_elements=inline_elements or [],
    )
    return SourceMetadataEntry(
        source_text=source,
        prompt_text=source,
        paragraph=paragraph,
        metadata_type="byline",
    )


def _service() -> SourceMetadataTranslationService:
    return SourceMetadataTranslationService(Mock(), Mock())


def test_byline_plain_names_with_others_uses_original_count():
    entry = _byline_entry("By Jane Doe, John Smith, and 2 others")

    payload = _service()._translate_byline(entry)

    assert payload is not None
    assert payload.text == "作者：Jane Doe、John Smith 及另外 2 位作者"
    assert "等" not in payload.text  # 累加口径（"等 4 人"）不得再出现


def test_byline_tokenized_names_with_others_uses_original_count():
    source = "By Jane Doe, and 2 others"
    entry = _byline_entry(
        source,
        inline_elements=[
            InlineElement(
                type="link",
                text="Jane Doe",
                start=3,
                end=11,
                href="https://substack.com/@janedoe",
            )
        ],
    )

    payload = _service()._translate_byline(entry)

    assert payload is not None
    assert "及另外 2 位作者" in payload.text
    assert "等 3 人" not in payload.text


def test_byline_without_others_lists_names_only():
    entry = _byline_entry("By Jane Doe, John Smith")

    payload = _service()._translate_byline(entry)

    assert payload is not None
    assert payload.text == "作者：Jane Doe、John Smith"
