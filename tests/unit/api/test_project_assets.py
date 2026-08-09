from pathlib import Path

import pytest

from src.api.routers.projects_management import (
    _project_asset_url,
    _rewrite_project_image_html,
    get_project_asset,
)
from src.api.middleware import NotFoundException
from src.core.project import ProjectManager


def test_project_asset_url_uses_public_api_and_encodes_filename() -> None:
    assert _project_asset_url("demo", "./images/hero image.png") == (
        "/api/projects/demo/assets/images/hero%20image.png"
    )
    assert _project_asset_url("demo", "../meta.json") is None
    assert _project_asset_url("demo", "https://cdn.example/image.png") == (
        "https://cdn.example/image.png"
    )
    assert _project_asset_url("demo", "./images/chart.png?version=2") == (
        "/api/projects/demo/assets/images/chart.png"
    )
    assert _project_asset_url(
        "demo",
        "![](./Co_Packaged_Optics_(CPO)_images/img_098.png)",
    ) == (
        "/api/projects/demo/assets/"
        "Co_Packaged_Optics_%28CPO%29_images/img_098.png"
    )


def test_rewrite_project_image_html_handles_both_quote_styles() -> None:
    html = '<picture><img src="./images/a.png"><img src=\'figures/b.jpg\'></picture>'

    rewritten = _rewrite_project_image_html("demo", html)

    assert 'src="/api/projects/demo/assets/images/a.png"' in rewritten
    assert "src='/api/projects/demo/assets/figures/b.jpg'" in rewritten


def test_resolve_project_asset_confines_path_to_project(tmp_path: Path) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    image = manager.projects_path / "demo" / "images" / "hero.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")

    assert manager.resolve_project_asset("demo", "images/hero.png") == image.resolve()
    with pytest.raises(FileNotFoundError):
        manager.resolve_project_asset("demo", "../outside.png")

    symlink = image.parent / "outside.png"
    symlink.symlink_to(outside)
    with pytest.raises(FileNotFoundError):
        manager.resolve_project_asset("demo", "images/outside.png")


@pytest.mark.asyncio
async def test_project_asset_endpoint_serves_only_image_files(tmp_path: Path) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    image = manager.projects_path / "demo" / "images" / "hero.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    metadata = manager.projects_path / "demo" / "meta.json"
    metadata.write_text("{}", encoding="utf-8")

    response = await get_project_asset("demo", "images/hero.png", manager)

    assert Path(response.path) == image.resolve()
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.headers["x-content-type-options"] == "nosniff"

    with pytest.raises(NotFoundException):
        await get_project_asset("demo", "meta.json", manager)
