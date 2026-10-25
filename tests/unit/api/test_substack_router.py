import pytest
from starlette.requests import Request

from src.api.middleware import APIException
from src.api.routers import substack
from src.core.models import ProjectStatus
from src.core.project import ProjectManager, ProjectTranslationSummary
from src.services import article_variants
from src.services.substack_library import SubstackLibrary
from src.services.substack_service import (
    ArchivePost,
    FetchedArticle,
    SubstackCookieStore,
    SubstackError,
)
from src.services.terminology_review_job_service import TerminologyReviewJobStore
from src.services.translation_run_registry import translation_run_registry

ARTICLE_URL = "https://newsletter.semianalysis.com/p/demo-post"
ARTICLE_HTML = f"""<html><head>
<title>Demo Post - by Someone</title>
<meta property="og:url" content="{ARTICLE_URL}">
</head><body>
<article class="newsletter-post post">
<div class="post-header"><h1 class="post-title">Demo Post</h1></div>
<div class="available-content"><div class="body markup">
<p>First paragraph of the article body with enough words to be kept.</p>
<h2>Second Section</h2>
<p>Another paragraph in the second section of the article.</p>
</div></div>
</article>
</body></html>"""


def _request(method: str = "POST", path: str = "/api/substack/import") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )


class FakeClient:
    def __init__(self, tmp_path, *, error=None, final_url=ARTICLE_URL):
        self.cookie_store = SubstackCookieStore(
            cookie_file=tmp_path / "cookie.txt", domain="newsletter.semianalysis.com"
        )
        self.error = error
        self.final_url = final_url
        self.fetched = []

    def fetch_article(self, url):
        self.fetched.append(url)
        if self.error:
            raise self.error
        return FetchedArticle(url=self.final_url, slug="demo-post", title="Demo Post", html=ARTICLE_HTML)

    def list_archive(self, *, offset=0, limit=24, search=""):
        if offset > 0:
            return []
        return [
            ArchivePost(
                title="Demo Post", subtitle="", slug="demo-post", url=ARTICLE_URL,
                post_date="2026-10-23T00:00:00Z", is_paid=True, cover_image=None, wordcount=100,
            ),
            ArchivePost(
                title="Other", subtitle="s", slug="other", url="https://newsletter.semianalysis.com/p/other",
                post_date="2026-10-22T00:00:00Z", is_paid=False, cover_image=None, wordcount=None,
            ),
        ]


@pytest.fixture(autouse=True)
def _no_env_cookie(monkeypatch):
    # 其他测试导入 app 时 load_dotenv() 可能把开发机 .env 里的真实 cookie 读进环境变量
    monkeypatch.delenv("SUBSTACK_COOKIE", raising=False)


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(projects_path=str(tmp_path / "projects"))


@pytest.mark.asyncio
async def test_import_creates_project_named_after_article(tmp_path, pm):
    client = FakeClient(tmp_path)
    result = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL + "?utm_source=share"), pm, client
    )
    assert result.already_imported is False
    assert result.project.title == "Demo Post"
    assert client.fetched == [ARTICLE_URL]

    meta = pm.get(result.project.id)
    assert meta.metadata.original_url == ARTICLE_URL
    assert meta.progress.total_paragraphs > 0


@pytest.mark.asyncio
async def test_import_uses_custom_name_for_project_id(tmp_path, pm):
    # 与上传流程一致：项目名决定项目 ID，标题仍取自文章本身
    result = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL, name="My Custom Name"), pm, FakeClient(tmp_path)
    )
    assert result.project.id == "my-custom-name"
    assert result.project.title == "Demo Post"


@pytest.mark.asyncio
async def test_second_import_returns_existing_project_without_downloading(tmp_path, pm):
    first = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL), pm, FakeClient(tmp_path)
    )
    client = FakeClient(tmp_path)
    second = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL + "/"), pm, client
    )
    assert second.already_imported is True
    assert second.project.id == first.project.id
    assert client.fetched == []


@pytest.mark.asyncio
async def test_share_link_resolving_to_imported_article_is_not_duplicated(tmp_path, pm):
    first = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL), pm, FakeClient(tmp_path)
    )
    client = FakeClient(tmp_path)
    second = await substack.import_article(
        _request(),
        substack.SubstackImportRequest(url="https://open.substack.com/pub/semianalysis/p/demo-post"),
        pm,
        client,
    )
    assert client.fetched == ["https://open.substack.com/pub/semianalysis/p/demo-post"]
    assert second.already_imported is True
    assert second.project.id == first.project.id
    assert len(pm.list_summaries()) == 1


@pytest.mark.asyncio
async def test_same_title_from_different_url_reports_name_conflict(tmp_path, pm):
    await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL), pm, FakeClient(tmp_path)
    )
    other = FakeClient(tmp_path, final_url="https://x.substack.com/p/demo-post")
    with pytest.raises(APIException) as exc_info:
        await substack.import_article(
            _request(), substack.SubstackImportRequest(url="https://x.substack.com/p/demo-post"), pm, other
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "PROJECT_EXISTS"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code, status_code",
    [("COOKIE_MISSING", 400), ("COOKIE_EXPIRED", 400), ("BLOCKED_URL", 400), ("UPSTREAM_ERROR", 502)],
)
async def test_fetch_errors_keep_their_code(tmp_path, pm, code, status_code):
    client = FakeClient(tmp_path, error=SubstackError(code, "说明"))
    with pytest.raises(APIException) as exc_info:
        await substack.import_article(_request(), substack.SubstackImportRequest(url=ARTICLE_URL), pm, client)
    assert exc_info.value.error_code == code
    assert exc_info.value.status_code == status_code
    assert pm.list_summaries() == []


@pytest.mark.asyncio
async def test_invalid_url_is_rejected_before_download(tmp_path, pm):
    client = FakeClient(tmp_path)
    with pytest.raises(APIException) as exc_info:
        await substack.import_article(_request(), substack.SubstackImportRequest(url="ftp://x/y"), pm, client)
    assert exc_info.value.error_code == "INVALID_URL"
    assert client.fetched == []


def _library(tmp_path, client=None):
    client = client or FakeClient(tmp_path)
    return SubstackLibrary(tmp_path / "library.json", client_factory=lambda: client)


async def _list(pm, library, *, offset=0, limit=24, search="", imported_filter="all"):
    # 直接调用路由函数时 Query 默认值不会生效，参数要写全
    return await substack.list_articles(
        pm, library, offset=offset, limit=limit, search=search, imported_filter=imported_filter
    )


async def _import(tmp_path, pm):
    result = await substack.import_article(
        _request(), substack.SubstackImportRequest(url=ARTICLE_URL), pm, FakeClient(tmp_path)
    )
    return result.project.id


@pytest.mark.asyncio
async def test_list_articles_marks_imported_ones(tmp_path, pm):
    project_id = await _import(tmp_path, pm)
    library = _library(tmp_path)
    page = await _list(pm, library)
    assert [(a.project_id, a.status) for a in page.articles] == [(project_id, "imported"), (None, "not_imported")]
    assert page.total == 2 and page.next_offset is None

    first = await _list(pm, library, limit=1)
    assert [a.slug for a in first.articles] == ["demo-post"] and first.next_offset == 1
    second = await _list(pm, library, offset=1, limit=1)
    assert [a.slug for a in second.articles] == ["other"] and second.next_offset is None


@pytest.mark.asyncio
async def test_list_articles_filters_by_imported(tmp_path, pm):
    await _import(tmp_path, pm)
    library = _library(tmp_path)
    imported = await _list(pm, library, imported_filter="imported")
    assert [a.slug for a in imported.articles] == ["demo-post"] and imported.total == 1
    not_imported = await _list(pm, library, imported_filter="not_imported")
    assert [a.slug for a in not_imported.articles] == ["other"]


@pytest.mark.asyncio
async def test_list_articles_counts_imported_and_not_imported(tmp_path, pm):
    await _import(tmp_path, pm)
    library = _library(tmp_path)
    page = await _list(pm, library)
    assert page.counts == {"all": 2, "not_imported": 1, "imported": 1}
    assert (await _list(pm, library, imported_filter="imported")).counts == page.counts


@pytest.mark.asyncio
async def test_list_articles_progress_takes_the_further_version(tmp_path, pm, monkeypatch):
    project_id = await _import(tmp_path, pm)
    variant = article_variants.create_variant(pm, project_id, kind="claude", label="Codex", suffix="Codex")
    done = {project_id: 0, variant: 4}
    monkeypatch.setattr(pm, "get_translation_summary", lambda pid: ProjectTranslationSummary(
        status=ProjectStatus.IN_PROGRESS, total_sections=1, total_paragraphs=4,
        translated_sections=0, translated_paragraphs=done[pid],
    ))
    library = _library(tmp_path)
    article = (await _list(pm, library)).articles[0]
    assert (article.project_id, article.status, article.progress) == (project_id, "translated", 100)
    assert (await _list(pm, library)).counts["imported"] == 1  # 孪生项目不算一篇


@pytest.mark.asyncio
async def test_list_articles_searches_saved_list(tmp_path, pm):
    page = await _list(pm, _library(tmp_path), search="demo")
    assert [a.slug for a in page.articles] == ["demo-post"]


@pytest.mark.asyncio
@pytest.mark.parametrize("translated, status, progress", [(1, "partial", 25), (4, "translated", 100)])
async def test_list_articles_reports_translation_progress(tmp_path, pm, monkeypatch, translated, status, progress):
    await _import(tmp_path, pm)
    monkeypatch.setattr(pm, "get_translation_summary", lambda project_id: ProjectTranslationSummary(
        status=ProjectStatus.IN_PROGRESS, total_sections=1, total_paragraphs=4,
        translated_sections=0, translated_paragraphs=translated,
    ))
    page = await _list(pm, _library(tmp_path))
    assert (page.articles[0].status, page.articles[0].progress) == (status, progress)


@pytest.mark.asyncio
async def test_list_articles_shows_running_workflow_and_term_confirmation(tmp_path, pm):
    project_id = await _import(tmp_path, pm)
    store = TerminologyReviewJobStore(pm.projects_path)
    job_id = store.create(project_id)["job_id"]
    translation_run_registry.set_active_run(project_id, run_id=job_id, status="starting")
    library = _library(tmp_path)
    try:
        assert (await _list(pm, library)).articles[0].status == "translating"

        store.mark_succeeded(project_id, job_id, {"review_required": True, "total_candidates": 2})
        store.mark_waiting_confirmation(project_id, job_id, timeout_seconds=600)
        assert (await _list(pm, library)).articles[0].status == "awaiting_terms"

        store.mark_confirmation_resolved(project_id, job_id, "submitted")
        assert (await _list(pm, library)).articles[0].status == "translating"
    finally:
        translation_run_registry.release_active_run(project_id)


@pytest.mark.asyncio
async def test_sync_reports_new_articles(tmp_path):
    library = _library(tmp_path)
    request = _request("POST", "/api/substack/articles/sync")
    first = await substack.sync_articles(request, library, full=False)
    assert (first.added, first.total) == (2, 2)
    again = await substack.sync_articles(request, library, full=True)
    assert (again.added, again.total) == (0, 2)


@pytest.mark.asyncio
async def test_first_open_reports_upstream_failure(tmp_path, pm):
    class Down(FakeClient):
        def list_archive(self, **kwargs):
            raise SubstackError("UPSTREAM_ERROR", "连不上 Substack")

    with pytest.raises(APIException) as exc_info:
        await _list(pm, _library(tmp_path, Down(tmp_path)))
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_cookie_status_and_save_never_echo_the_cookie(tmp_path):
    client = FakeClient(tmp_path)
    status = await substack.get_cookie_status(client)
    assert status.configured is False

    saved = await substack.save_cookie(
        _request("PUT", "/api/substack/cookie"),
        substack.SubstackCookieRequest(cookie="_ga=1; connect.sid=s%3Asecret; __cf_bm=x"),
        client,
    )
    assert saved.model_dump() == {"configured": True, "domain": "newsletter.semianalysis.com"}
    assert client.cookie_store.load() == "connect.sid=s%3Asecret"


@pytest.mark.asyncio
async def test_save_cookie_rejects_paste_without_session_cookie(tmp_path):
    with pytest.raises(APIException) as exc_info:
        await substack.save_cookie(
            _request("PUT", "/api/substack/cookie"),
            substack.SubstackCookieRequest(cookie="_ga=1"),
            FakeClient(tmp_path),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_COOKIE"
