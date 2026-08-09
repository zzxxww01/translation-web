from pathlib import Path

import pytest

from src.core.project import ProjectManager


def _manager(tmp_path: Path) -> ProjectManager:
    return ProjectManager(projects_path=str(tmp_path / "projects"))


def test_missing_source_does_not_leave_project_directory(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "missing.md"

    with pytest.raises(FileNotFoundError, match="Source file not found"):
        manager.create("Retryable Project", str(source))

    assert not (manager.projects_path / "retryable-project").exists()


def test_unsupported_source_does_not_leave_project_directory(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("unsupported", encoding="utf-8")

    with pytest.raises(ValueError, match="Only .* supported"):
        manager.create("Retryable Project", str(source))

    assert not (manager.projects_path / "retryable-project").exists()


def test_failed_persistence_removes_only_new_incomplete_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("# Title\n\nBody paragraph.", encoding="utf-8")
    existing = manager.projects_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    def fail_meta_save(_project_id, _meta):
        raise OSError("simulated metadata write failure")

    monkeypatch.setattr(
        manager.project_lifecycle_service,
        "_save_meta",
        fail_meta_save,
    )

    with pytest.raises(OSError, match="simulated metadata write failure"):
        manager.create("Retryable Project", str(source))

    assert not (manager.projects_path / "retryable-project").exists()
    assert marker.read_text(encoding="utf-8") == "keep"


def test_delete_discards_project_summary_caches(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("# Title\n\nBody paragraph.", encoding="utf-8")
    project = manager.create("Disposable Project", str(source))

    manager.list_summaries()
    manager.get_translation_summary(project.id)
    assert project.id in manager._project_summary_cache
    assert project.id in manager._translation_summary_cache
    assert project.id in manager._translation_summary_generations

    manager.delete(project.id)

    assert project.id not in manager._project_summary_cache
    assert project.id not in manager._translation_summary_cache
    assert project.id not in manager._translation_summary_generations


def test_create_copies_locally_referenced_image_with_parentheses(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    image_dir = tmp_path / "Article_(CPO)_images"
    image_dir.mkdir()
    source_image = image_dir / "chart.png"
    source_image.write_bytes(b"image-bytes")
    source = tmp_path / "source.md"
    source.write_text(
        "# Title\n\n## Charts\n\n![](./Article_(CPO)_images/chart.png)\n",
        encoding="utf-8",
    )

    project = manager.create("Image Project", str(source))

    copied = manager.projects_path / project.id / "Article_(CPO)_images" / "chart.png"
    assert copied.read_bytes() == b"image-bytes"
    paragraph = manager.get_sections(project.id)[0].paragraphs[0]
    assert paragraph.source == "./Article_(CPO)_images/chart.png"
