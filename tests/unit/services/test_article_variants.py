import pytest
from starlette.requests import Request

from src.api.middleware import APIException
from src.api.routers import workbench
from src.core.models import ParagraphStatus
from src.core.project import ProjectManager
from src.services import article_variants

HTML = """<html><head><title>Demo Post</title></head><body>
<article class="newsletter-post post">
<div class="post-header"><h1 class="post-title">Demo Post</h1></div>
<div class="available-content"><div class="body markup">
<p>First paragraph about wafer supply and the 2027 buildout of datacenters.</p>
<h2>Second Section</h2>
<p>Another paragraph explaining why HBM demand keeps outrunning supply.</p>
</div></div>
</article></body></html>"""


def _request(method="PUT"):
    return Request({"type": "http", "method": method, "path": "/api/x", "headers": [], "client": ("127.0.0.1", 1)})


class FakeStatus:
    async def get_translation_progress(self, project_id):
        return {"active_run_id": None, "status": "idle", "translated_paragraphs": 0, "total_paragraphs": 2}


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(projects_path=str(tmp_path / "projects"))


@pytest.fixture
def main_id(pm, tmp_path):
    source = tmp_path / "demo.html"
    source.write_text(HTML, encoding="utf-8")
    return pm.create("demo", str(source)).id


def _body_paragraphs(pm, project_id):
    return [(s.section_id, p) for s in pm.get_sections(project_id) for p in s.paragraphs if not p.is_metadata]


def test_variant_mirrors_structure_without_translations_and_is_hidden_from_lists(pm, main_id):
    section_id, first = _body_paragraphs(pm, main_id)[0]
    pm.confirm_paragraph(main_id, section_id, first.id, "主项目的译文")

    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")

    assert variant == f"{main_id}--argon"
    main_ids = [p.id for _, p in _body_paragraphs(pm, main_id)]
    assert [p.id for _, p in _body_paragraphs(pm, variant)] == main_ids
    assert all(not p.best_translation_text() for _, p in _body_paragraphs(pm, variant))
    meta = pm.get(variant)
    assert (meta.variant_of, meta.variant_kind, meta.variant_label) == (main_id, "model", "argon")
    assert [s.id for s in pm.list_summaries()] == [main_id]
    assert [s.id for s in article_variants.list_variants(pm, main_id)] == [variant]
    with pytest.raises(ValueError):
        article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")


def test_claude_import_aligns_text_into_its_own_variant(pm, main_id):
    en = ("# Demo Post\n\nFirst paragraph about wafer supply and the 2027 buildout of datacenters.\n\n"
          "## Second Section\n\nAnother paragraph explaining why HBM demand keeps outrunning supply.\n")
    zh = "# 演示文章\n\n关于晶圆供给和 2027 年数据中心建设的第一段。\n\n## 第二节\n\n解释 HBM 需求为何持续超过供给的一段。\n"

    result = article_variants.import_claude_translation(pm, main_id, zh_markdown=zh, en_markdown=en, run_id="r1")

    variant = result["variant_id"]
    texts = [p.best_translation_text() for _, p in _body_paragraphs(pm, variant)]
    assert texts == ["关于晶圆供给和 2027 年数据中心建设的第一段。", "解释 HBM 需求为何持续超过供给的一段。"]
    assert all(p.status == ParagraphStatus.TRANSLATED for _, p in _body_paragraphs(pm, variant))
    assert pm.get(variant).title_translation == "演示文章"
    assert "第二节" in [s.title_translation for s in pm.get_sections(variant)]
    assert article_variants.read_import_record(pm, variant)["run_id"] == "r1"
    # 主项目不受影响；重导是整篇替换
    assert all(not p.best_translation_text() for _, p in _body_paragraphs(pm, main_id))
    article_variants.import_claude_translation(pm, main_id, zh_markdown=zh, en_markdown=en)
    assert [s.id for s in article_variants.list_variants(pm, main_id)] == [variant]


def test_deleting_main_project_removes_its_variants(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")
    article_variants.delete_with_variants(pm, main_id)
    assert pm.list_summaries(include_variants=True) == []
    with pytest.raises(FileNotFoundError):
        pm.get(variant)


@pytest.mark.asyncio
async def test_workbench_rows_line_up_both_versions_and_save_to_either(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")
    section_id, first = _body_paragraphs(pm, main_id)[0]

    await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
        target=main_id, section_id=section_id, paragraph_id=first.id, text="译本一"), pm)
    await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
        target=variant, section_id=section_id, paragraph_id=first.id, text="译本二"), pm)
    second_section = pm.get_sections(main_id)[-1].section_id
    await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
        target=variant, section_id=second_section, text="第二节"), pm)

    data = await workbench.get_workbench(main_id, pm, FakeStatus())
    row = next(r for r in data["rows"] if r["key"] == f"{section_id}/{first.id}")
    assert (row["web"], row["alt"][variant]) == ("译本一", "译本二")
    heading = next(r for r in data["rows"] if r["key"] == f"section:{second_section}")
    assert heading["source"] == "Second Section" and heading["alt"][variant] == "第二节"
    assert [v["label"] for v in data["variants"]] == ["argon"]


@pytest.mark.asyncio
async def test_saving_into_a_project_that_is_not_this_articles_variant_is_refused(pm, main_id, tmp_path):
    other_source = tmp_path / "other.html"
    other_source.write_text(HTML.replace("Demo Post", "Other Post"), encoding="utf-8")
    other = pm.create("other", str(other_source)).id
    section_id, first = _body_paragraphs(pm, main_id)[0]
    with pytest.raises(APIException):
        await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
            target=other, section_id=section_id, paragraph_id=first.id, text="不该写进去"), pm)
    with pytest.raises(APIException):
        await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
            target=main_id, section_id=section_id, paragraph_id=first.id, text="   "), pm)


def test_codex_import_gets_its_own_variant(pm, main_id):
    en = "First paragraph about wafer supply and the 2027 buildout of datacenters.\n"
    zh = "关于晶圆供给和 2027 年数据中心建设的第一段。\n"
    result = article_variants.import_claude_translation(pm, main_id, zh_markdown=zh, en_markdown=en, agent="codex")
    assert result["variant_id"] == f"{main_id}--codex"
    assert pm.get(result["variant_id"]).variant_label == "Codex"
