import json

import pytest

from src.api.middleware import APIException
from src.api.routers import workbench
from src.core.project import ProjectManager
from src.services import article_edits, article_variants

HTML = """<html><head><title>Demo Post</title></head><body>
<article class="newsletter-post post">
<div class="post-header"><h1 class="post-title">Demo Post</h1></div>
<div class="available-content"><div class="body markup">
<p>First paragraph about wafer supply and the 2027 buildout of datacenters.</p>
<h2>Second Section</h2>
<p>Another paragraph explaining why HBM demand keeps outrunning supply.</p>
</div></div>
</article></body></html>"""


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(projects_path=str(tmp_path / "projects"))


@pytest.fixture
def main_id(pm, tmp_path):
    source = tmp_path / "demo.html"
    source.write_text(HTML, encoding="utf-8")
    return pm.create("demo", str(source)).id


def _body(pm, project_id):
    return [(s.section_id, p) for s in pm.get_sections(project_id) for p in s.paragraphs if not p.is_metadata]


def _machine_translate(pm, project_id, texts):
    for (section_id, paragraph), text in zip(_body(pm, project_id), texts):
        pm.update_paragraph_locked(project_id, section_id, paragraph.id, translation=text, model="gemini-flash")


def test_changes_compare_machine_draft_with_human_edit(pm, main_id):
    _machine_translate(pm, main_id, ["关于晶圆供给的第一段。", "解释 HBM 需求的一段。"])
    (section_id, first), _ = _body(pm, main_id)
    # 工作台自动保存走的就是 confirm_paragraph
    pm.confirm_paragraph(main_id, section_id, first.id, "关于晶圆供应的第一段。")

    report = article_edits.with_segments(article_edits.collect_changes(pm.get_sections(main_id)))

    assert report["total"] == 2 and report["changed"] == 1
    change = report["changes"][0]
    assert (change["before"], change["after"]) == ("关于晶圆供给的第一段。", "关于晶圆供应的第一段。")
    assert change["source"].startswith("First paragraph")
    assert {"op": "delete", "text": "给"} in change["segments"] and {"op": "insert", "text": "应"} in change["segments"]


def test_editing_twice_still_compares_with_the_machine_draft(pm, main_id):
    _machine_translate(pm, main_id, ["初稿。", "第二段。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "改了一次。")
    pm.confirm_paragraph(main_id, section_id, first.id, "又改了一次。")
    change = article_edits.collect_changes(pm.get_sections(main_id))["changes"][0]
    assert (change["before"], change["after"]) == ("初稿。", "又改了一次。")


def test_saving_without_changing_text_is_not_a_change(pm, main_id):
    _machine_translate(pm, main_id, ["第一段。", "第二段。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "第一段。")
    assert article_edits.collect_changes(pm.get_sections(main_id))["changed"] == 0


def test_export_covers_every_article_and_version(pm, main_id):
    _machine_translate(pm, main_id, ["网页版初稿。", "第二段。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "网页版改后。")
    variant = article_variants.create_variant(pm, main_id, kind="claude", label="Codex", suffix="Codex")
    _machine_translate(pm, variant, ["Codex 初稿。", "Codex 第二段。"])
    pm.confirm_paragraph(variant, section_id, first.id, "Codex 改后。")

    lines = sorted((json.loads(line) for line in article_edits.export_all(pm)), key=lambda line: line["version"])

    assert [(line["version"], line["main_id"], line["before"], line["after"]) for line in lines] == [
        ("Codex", main_id, "Codex 初稿。", "Codex 改后。"),
        ("网页版", main_id, "网页版初稿。", "网页版改后。"),
    ]


@pytest.mark.asyncio
async def test_changes_endpoint_rejects_versions_of_other_articles(pm, main_id, tmp_path):
    other_source = tmp_path / "other.html"
    other_source.write_text(HTML.replace("Demo Post", "Other Post"), encoding="utf-8")
    other = pm.create("other", str(other_source)).id
    with pytest.raises(APIException):
        await workbench.get_changes(main_id, other, pm)


@pytest.mark.asyncio
async def test_changes_and_export_endpoints(pm, main_id):
    _machine_translate(pm, main_id, ["初稿一。", "初稿二。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "改后一。")

    assert (await workbench.get_changes(main_id, main_id, pm))["changed"] == 1

    response = await workbench.export_human_edits(pm)
    assert response.headers["content-disposition"].startswith('attachment; filename="human-edits-')
    assert json.loads(response.body.decode().splitlines()[0])["after"] == "改后一。"
