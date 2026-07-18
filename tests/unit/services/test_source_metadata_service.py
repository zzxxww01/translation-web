from types import SimpleNamespace
from unittest.mock import Mock

from src.core.models import Glossary, Paragraph, Section
from src.services.source_metadata_service import SourceMetadataTranslationService


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
