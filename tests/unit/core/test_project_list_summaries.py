import json
from datetime import datetime

from src.api.routers.projects_management import _build_project_response
from src.core.file_utils import write_json_atomic
from src.core.models import ProjectMeta
from src.core.project import ProjectManager


def _write_meta(
    manager: ProjectManager,
    project_id: str,
    *,
    title: str,
    created_at: str,
    total: int = 10,
    approved: int = 3,
    sections=None,
):
    project_dir = manager.projects_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    payload = ProjectMeta(
        id=project_id,
        title=title,
        source_file="source.md",
        created_at=datetime.fromisoformat(created_at),
        progress={
            "total_paragraphs": total,
            "approved": approved,
        },
    ).model_dump(mode="json")
    payload["sections"] = sections if sections is not None else []
    write_json_atomic(project_dir / "meta.json", payload)


def test_list_summaries_preserves_response_shape_and_sort_without_sections_scan(
    tmp_path,
    monkeypatch,
):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    large_legacy_sections = [
        {"section_id": f"s{index}", "paragraphs": [{"source": "x" * 5000}]}
        for index in range(10)
    ]
    _write_meta(
        manager,
        "older",
        title="Older",
        created_at="2025-01-01T00:00:00",
        total=0,
        approved=0,
        sections=large_legacy_sections,
    )
    _write_meta(
        manager,
        "newer",
        title="Newer",
        created_at="2026-01-01T00:00:00",
        total=20,
        approved=5,
    )

    monkeypatch.setattr(
        manager,
        "get_sections",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("list endpoint must not scan sections")
        ),
    )
    monkeypatch.setattr(
        manager,
        "get",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("list endpoint must not load full metadata")
        ),
    )

    summaries = manager.list_summaries()
    responses = [_build_project_response(summary) for summary in summaries]

    assert [summary.id for summary in summaries] == ["newer", "older"]
    assert responses[0].model_dump() == {
        "id": "newer",
        "title": "Newer",
        "status": "created",
        "progress": {"total": 20, "approved": 5, "percent": 25.0},
        "created_at": "2026-01-01T00:00:00",
    }
    assert responses[1].progress == {
        "total": 0,
        "approved": 0,
        "percent": 0.0,
    }


def test_list_summary_cache_revalidates_external_atomic_replacement(
    tmp_path,
    monkeypatch,
):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    _write_meta(
        manager,
        "demo",
        title="Before",
        created_at="2026-01-01T00:00:00",
    )
    original_parse = manager._parse_project_summary
    parse_count = 0

    def counted_parse(meta_path):
        nonlocal parse_count
        parse_count += 1
        return original_parse(meta_path)

    monkeypatch.setattr(manager, "_parse_project_summary", counted_parse)

    assert manager.list_summaries()[0].title == "Before"
    assert manager.list_summaries()[0].title == "Before"
    assert parse_count == 1

    meta_path = manager.projects_path / "demo" / "meta.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    payload["title"] = "After"
    write_json_atomic(meta_path, payload)

    assert manager.list_summaries()[0].title == "After"
    assert parse_count == 2


def test_list_summaries_skips_corrupt_metadata_and_bounds_cache(tmp_path):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager._PROJECT_SUMMARY_CACHE_SIZE = 2
    for index in range(3):
        _write_meta(
            manager,
            f"valid-{index}",
            title=f"Valid {index}",
            created_at=f"2026-01-0{index + 1}T00:00:00",
        )

    corrupt_dir = manager.projects_path / "corrupt"
    corrupt_dir.mkdir()
    (corrupt_dir / "meta.json").write_text('{"id": "corrupt"', encoding="utf-8")
    _write_meta(
        manager,
        "invalid directory",
        title="Must Be Skipped",
        created_at="2026-01-04T00:00:00",
    )

    assert len(manager.list_summaries()) == 3
    assert len(manager._project_summary_cache) == 2


def test_get_ignores_legacy_sections_snapshot(tmp_path, monkeypatch):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    _write_meta(
        manager,
        "demo",
        title="Demo",
        created_at="2026-01-01T00:00:00",
        sections=[{"not": "a valid Section"}],
    )
    monkeypatch.setattr(
        manager,
        "get_sections",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("non-zero progress must not scan sections")
        ),
    )

    project = manager.get("demo")

    assert project.sections == []
    assert project.progress.total_paragraphs == 10
