# -*- coding: utf-8 -*-
"""路径边界兜底：project_id / section_id 不得越出各自的根目录。

这是不依赖调用方的第二道防线——路由层的 validate_path_component 是第一道。
特别覆盖 `target == base` 这个边界：一个路径相对于它自己也满足
`is_relative_to`，所以 ""、"."、"a/.." 会解析回根目录本身。
"""

from pathlib import Path

import pytest

from src.core.glossary import GlossaryManager
from src.core.project_repository import ProjectRepository


def _build_repository(tmp_path: Path) -> ProjectRepository:
    return ProjectRepository(
        project_dir_resolver=lambda pid: tmp_path / "projects" / pid,
        read_json=lambda path: None,
        write_json=lambda path, payload: None,
        write_text=lambda path, text: None,
        get_project=lambda pid: None,
        render_source_block_markdown=lambda paragraphs: "",
        render_markdown_line=lambda element_type, text: text,
        best_translation_text=lambda paragraph, fallback_to_source=True: "",
    )


@pytest.fixture
def manager(tmp_path: Path) -> GlossaryManager:
    return GlossaryManager(
        global_path=str(tmp_path / "glossary"),
        projects_path=str(tmp_path / "projects"),
    )


@pytest.mark.parametrize(
    "project_id",
    ["", ".", "demo/..", "../evil", "..\\evil", "a/../../evil"],
)
def test_glossary_rejects_escaping_project_id(manager: GlossaryManager, project_id):
    with pytest.raises(ValueError):
        manager._resolve_project_dir(project_id)


def test_glossary_accepts_normal_project_id(manager: GlossaryManager, tmp_path: Path):
    resolved = manager._resolve_project_dir("demo")
    assert resolved == (tmp_path / "projects" / "demo").resolve()


@pytest.mark.parametrize(
    "section_id",
    ["", ".", "a/..", "../../evil", "..\\evil"],
)
def test_repository_rejects_escaping_section_id(tmp_path: Path, section_id):
    repo = _build_repository(tmp_path)
    assert repo._resolve_section_dir("demo", section_id) is None


def test_repository_accepts_normal_section_id(tmp_path: Path):
    repo = _build_repository(tmp_path)
    resolved = repo._resolve_section_dir("demo", "s001")
    assert resolved == (tmp_path / "projects" / "demo" / "sections" / "s001").resolve()
