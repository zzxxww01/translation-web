import json

import pytest
from starlette.requests import Request

from src.api.middleware import APIException
from src.api.routers import workbench
from src.core.models import ParagraphStatus
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


def _request(method="POST"):
    return Request({"type": "http", "method": method, "path": "/api/x", "headers": [], "client": ("127.0.0.1", 1)})


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
    pm.confirm_paragraph(main_id, section_id, first.id, "关于晶圆供应的第一段。")

    report = article_edits.with_segments(article_edits.collect_changes(pm.get_sections(main_id)))

    assert report["total"] == 2 and report["changed"] == 1
    change = report["changes"][0]
    assert (change["before"], change["after"]) == ("关于晶圆供给的第一段。", "关于晶圆供应的第一段。")
    assert change["source"].startswith("First paragraph")
    assert {"op": "delete", "text": "给"} in change["segments"] and {"op": "insert", "text": "应"} in change["segments"]


def test_confirming_without_changing_text_is_not_a_change(pm, main_id):
    _machine_translate(pm, main_id, ["第一段。", "第二段。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "第一段。")
    assert article_edits.collect_changes(pm.get_sections(main_id))["changed"] == 0


def test_finalize_confirms_everything_and_saves_final_text_and_diff(pm, main_id):
    _machine_translate(pm, main_id, ["关于晶圆供给的第一段。", "解释 HBM 需求的一段。"])
    (section_id, first), (_, second) = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "关于晶圆供应的第一段。")

    result = article_edits.finalize(pm, main_id, main_id)

    assert (result["total"], result["changed"], result["confirmed"]) == (2, 1, 1)
    assert all(p.status == ParagraphStatus.APPROVED for _, p in _body(pm, main_id))
    folder = article_edits.finalized_dir(pm, main_id)
    record = json.loads((folder / "changes.json").read_text(encoding="utf-8"))
    assert record["changed"] == 1 and record["changes"][0]["after"] == "关于晶圆供应的第一段。"
    assert "关于晶圆供应的第一段。" in (folder / "final.md").read_text(encoding="utf-8")
    patch = (folder / "diff.patch").read_text(encoding="utf-8")
    assert "-关于晶圆供给的第一段。" in patch and "+关于晶圆供应的第一段。" in patch
    assert "初稿：关于晶圆供给的第一段。" in (folder / "changes.md").read_text(encoding="utf-8")
    assert article_edits.read_summary(pm, main_id)["changed"] == 1
    assert pm.get(main_id).finalized_at is not None
    assert pm.list_summaries()[0].finalized_at is not None

    lines = [json.loads(line) for line in article_edits.export_all(pm)]
    assert [(line["project_id"], line["label"], line["paragraph_id"]) for line in lines] == [(main_id, "网页版", first.id)]


def test_finalizing_a_variant_marks_the_article_finalized(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="claude", label="Codex", suffix="Codex")
    _machine_translate(pm, variant, ["Codex 第一段。", "Codex 第二段。"])

    article_edits.finalize(pm, main_id, variant)

    assert pm.get(variant).finalized_at is not None
    assert pm.get(main_id).finalized_at is not None
    assert article_edits.read_summary(pm, main_id) is None  # 网页版这一版没保存过


@pytest.mark.asyncio
async def test_endpoints_reject_versions_of_other_articles(pm, main_id, tmp_path):
    other_source = tmp_path / "other.html"
    other_source.write_text(HTML.replace("Demo Post", "Other Post"), encoding="utf-8")
    other = pm.create("other", str(other_source)).id

    with pytest.raises(APIException):
        await workbench.finalize_version(_request(), main_id, workbench.FinalizeRequest(target=other), pm)
    with pytest.raises(APIException):
        await workbench.get_changes(main_id, other, pm)


@pytest.mark.asyncio
async def test_endpoints_finalize_and_list_changes(pm, main_id):
    _machine_translate(pm, main_id, ["初稿一。", "初稿二。"])
    (section_id, first), _ = _body(pm, main_id)
    pm.confirm_paragraph(main_id, section_id, first.id, "改后一。")

    changes = await workbench.get_changes(main_id, main_id, pm)
    assert changes["changed"] == 1 and changes["finalized"] is None

    saved = await workbench.finalize_version(_request(), main_id, workbench.FinalizeRequest(target=main_id), pm)
    assert saved["changed"] == 1
    assert (await workbench.get_changes(main_id, main_id, pm))["finalized"]["changed"] == 1

    response = await workbench.export_human_edits(pm)
    assert response.headers["content-disposition"].startswith('attachment; filename="human-edits-')
    assert json.loads(response.body.decode().splitlines()[0])["after"] == "改后一。"
