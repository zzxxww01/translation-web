import pytest
from starlette.requests import Request

from src.api.middleware import BadRequestException
from src.api.routers import workbench
from src.core.project import ProjectManager
from src.services import article_sent, article_variants

HTML = """<html><head><title>Demo Post</title></head><body>
<article class="newsletter-post post">
<div class="post-header"><h1 class="post-title">Demo Post</h1></div>
<div class="available-content"><div class="body markup">
<p>First paragraph about wafer supply and the 2027 buildout of datacenters.</p>
<h2>Second Section</h2>
<p>Another paragraph explaining why HBM demand keeps outrunning supply.</p>
</div></div>
</article></body></html>"""


def _request():
    return Request({"type": "http", "method": "PUT", "path": "/api/x", "headers": [], "client": ("127.0.0.1", 1)})


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


def _first(pm, project_id):
    return next((s.section_id, p) for s in pm.get_sections(project_id) for p in s.paragraphs if not p.is_metadata)


async def _save(pm, main_id, target, text):
    section_id, first = _first(pm, main_id)
    await workbench.save_text(_request(), main_id, workbench.SaveTextRequest(
        target=target, section_id=section_id, paragraph_id=first.id, text=text), pm)


@pytest.mark.asyncio
async def test_sent_mark_survives_stale_meta_save_and_can_be_undone(pm, main_id):
    stale_meta = pm.get(main_id)
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"] is None

    result = await workbench.put_sent(main_id, workbench.SentRequest(sent=True), pm)
    assert result["sent"]["changed"] is False
    pm.save_meta(stale_meta)  # 后台翻译拿旧快照存 meta，不能冲掉标记

    data = await workbench.get_workbench(main_id, pm, FakeStatus())
    assert data["sent"] == {"at": result["sent"]["at"], "changed": False}

    assert (await workbench.put_sent(main_id, workbench.SentRequest(sent=False), pm))["sent"] is None
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"] is None


@pytest.mark.asyncio
async def test_editing_primary_after_sending_is_flagged_until_marked_again(pm, main_id):
    await _save(pm, main_id, main_id, "发出去的译文")
    await workbench.put_sent(main_id, workbench.SentRequest(sent=True), pm)

    await _save(pm, main_id, main_id, "发出去以后又改了")
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"]["changed"] is True

    await workbench.put_sent(main_id, workbench.SentRequest(sent=True), pm)  # 再标一次就按现在的算
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"]["changed"] is False


@pytest.mark.asyncio
async def test_switching_primary_or_editing_other_version_after_sending(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")
    await _save(pm, main_id, main_id, "网页版")
    pm.merge_meta_fields(main_id, fields={"primary_target": main_id})
    await workbench.put_sent(main_id, workbench.SentRequest(sent=True), pm)

    await _save(pm, main_id, variant, "另一版改了不算")
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"]["changed"] is False

    await workbench.set_primary(main_id, workbench.PrimaryRequest(target=variant), pm)
    assert (await workbench.get_workbench(main_id, pm, FakeStatus()))["sent"]["changed"] is True


def test_sent_can_only_be_marked_on_the_main_project(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")
    with pytest.raises(BadRequestException):
        workbench.set_sent(pm, variant, True)


def test_corrupt_sent_record_reads_as_not_sent(pm, main_id):
    path = pm._project_dir(main_id) / "artifacts" / "sent.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert article_sent.read(pm, main_id) is None
    path.write_text('{"at": "yesterday"}', encoding="utf-8")
    assert article_sent.read(pm, main_id) is None
