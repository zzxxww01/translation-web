"""
Substack article browsing and one-click import endpoints.
"""

import asyncio
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.core.project import ProjectListSummary, ProjectManager
from src.services import article_primary
from src.services.substack_library import LibraryPost, SubstackLibrary, make_llm_digest_fn
from src.services.substack_service import (
    SubstackClient,
    SubstackCookieStore,
    SubstackError,
    article_key,
    normalize_article_url,
)
from src.services.terminology_review_job_service import TerminologyReviewJobStore
from src.services.translation_run_registry import translation_run_registry
from src.settings import settings
from src.api.utils.concurrency import run_blocking

from ..dependencies import ProjectManagerDep
from ..middleware import APIException
from ..middleware.rate_limit import limiter
from .projects_management import _build_project_response
from .projects_models import ProjectResponse


router = APIRouter(prefix="/substack")


def get_substack_client() -> SubstackClient:
    store = SubstackCookieStore(
        cookie_file=Path(settings.substack_cookie_file),
        env_file=Path(".env"),
        domain=settings.substack_cookie_domain,
    )
    return SubstackClient(store)


SubstackClientDep = Annotated[SubstackClient, Depends(get_substack_client)]


@lru_cache(maxsize=1)
def get_substack_library() -> SubstackLibrary:
    # 全进程共用一份：清单在内存里缓存，后台生成中文的线程也只开一个
    return SubstackLibrary(
        Path(settings.substack_library_file),
        client_factory=get_substack_client,
        digest_fn=make_llm_digest_fn(),
    )


SubstackLibraryDep = Annotated[SubstackLibrary, Depends(get_substack_library)]

# not_imported 没导入；imported 已导入还没翻；awaiting_terms 翻译在等你确认术语；
# translating 翻译中；partial 翻了一部分停下了；translated 已译完。网页版和译本 2 取进度高的那一版
ArticleStatus = Literal["not_imported", "imported", "awaiting_terms", "translating", "partial", "translated"]


class SubstackArticle(BaseModel):
    title: str
    subtitle: str
    slug: str
    url: str
    post_date: str
    is_paid: bool
    cover_image: Optional[str] = None
    wordcount: Optional[int] = None
    zh_title: str = ""
    zh_summary: str = ""
    project_id: Optional[str] = None
    status: ArticleStatus = "not_imported"
    progress: int = 0  # 已翻段落的百分比


class SubstackArticlePage(BaseModel):
    articles: List[SubstackArticle]
    next_offset: Optional[int] = None  # 没有更多时为 None
    total: int = 0  # 符合当前搜索和筛选的总篇数
    pending_digests: int = 0  # 还没有中文标题和摘要的篇数
    counts: Dict[str, int] = Field(default_factory=dict)  # 当前搜索下各筛选的篇数：all / not_imported / imported
    digesting: bool = False  # 后台正在生成；前端据此决定要不要定时刷新


class SubstackSyncResult(BaseModel):
    added: int
    total: int


class SubstackImportRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)
    name: Optional[str] = Field(None, max_length=200)


class SubstackImportResponse(BaseModel):
    project: ProjectResponse
    already_imported: bool = False


class SubstackCookieStatus(BaseModel):
    configured: bool
    domain: str


class SubstackCookieRequest(BaseModel):
    cookie: str = Field(..., min_length=1, max_length=20000)


def _to_api_error(error: SubstackError) -> APIException:
    status_code = 502 if error.code == "UPSTREAM_ERROR" else 400
    return APIException(status_code=status_code, detail=error.message, error_code=error.code)


def _imported_projects(pm: ProjectManager) -> Tuple[Dict[str, ProjectListSummary], Dict[str, List[str]]]:
    """原文链接 → 主项目摘要（同一篇导入过多次时保留最新的那个），以及主项目 → 它的译本 2（孪生项目）id。"""
    imported: Dict[str, ProjectListSummary] = {}
    variants: Dict[str, List[str]] = {}
    for summary in reversed(pm.list_summaries(include_variants=True)):
        if summary.variant_of:
            variants.setdefault(summary.variant_of, []).append(summary.id)
            continue
        key = article_key(summary.original_url)
        if key:
            imported[key] = summary
    return imported, variants


_TERM_REVIEW_JOB_ID = re.compile(r"[0-9a-f]{32}")


def _awaiting_terms(pm: ProjectManager, project_id: str, run_id: Optional[str]) -> bool:
    # 术语预检阶段的 run_id 就是预检任务 ID；确认窗口打开时任务记录里是 waiting
    if not run_id or not _TERM_REVIEW_JOB_ID.fullmatch(run_id):
        return False
    try:
        job = TerminologyReviewJobStore(pm.projects_path).get(project_id, run_id)
    except (OSError, ValueError):
        return False
    return job.get("confirmation_status") == "waiting"


def _progress(pm: ProjectManager, project_id: str) -> Optional[Tuple[int, int]]:
    """(已翻段数, 百分比)；项目不在了返回 None。"""
    try:
        summary = pm.get_translation_summary(project_id)
    except FileNotFoundError:
        return None
    total, done = summary.total_paragraphs, summary.translated_paragraphs
    return done, (min(100, done * 100 // total) if total else 0)


def _translation_state(pm: ProjectManager, project_id: str, variant_ids: List[str],
                       primary_target: Optional[str] = None) -> Tuple[ArticleStatus, int]:
    """只看主译本（services/article_primary.py）；主译本在跑或在等术语确认时照旧显示。"""
    main = _progress(pm, project_id)
    if main is None:
        return "not_imported", 0  # 列清单和这里之间项目被删了
    main_done, main_percent = main
    primary = article_primary.resolve_primary(pm, project_id, variant_ids, primary_target=primary_target,
                                              main_started=article_primary.started(project_id, main_done))
    percent = main_percent if primary == project_id else (_progress(pm, primary) or (0, 0))[1]
    active = translation_run_registry.get_active_run(primary)
    if active is not None:
        return ("awaiting_terms" if _awaiting_terms(pm, primary, active.run_id) else "translating"), percent
    if percent >= 100:
        return "translated", 100
    if percent:
        return "partial", percent
    return "imported", 0


def _to_article(
    pm: ProjectManager, post: LibraryPost, project: Optional[ProjectListSummary], variant_ids: List[str]
) -> SubstackArticle:
    article = SubstackArticle(
        title=post.title,
        subtitle=post.subtitle,
        slug=post.slug,
        url=post.url,
        post_date=post.post_date,
        is_paid=post.is_paid,
        cover_image=post.cover_image,
        wordcount=post.wordcount,
        zh_title=post.zh_title,
        zh_summary=post.zh_summary,
    )
    if project is not None:
        status, progress = _translation_state(pm, project.id, variant_ids, project.primary_target)
        if status != "not_imported":
            article.project_id, article.status, article.progress = project.id, status, progress
    return article


@router.get("/articles", response_model=SubstackArticlePage)
async def list_articles(
    pm: ProjectManagerDep,
    library: SubstackLibraryDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=50),
    search: str = Query("", max_length=200),
    imported_filter: Literal["all", "not_imported", "imported"] = Query("all", alias="filter"),
):
    # 读服务器上存的清单；只有第一次（清单还是空的）才会当场把全部文章拉一遍
    try:
        await run_blocking(library.ensure_synced)
    except SubstackError as error:
        raise _to_api_error(error) from error
    library.start_digest_worker()

    posts = await asyncio.to_thread(library.posts, search)
    imported, variants = await asyncio.to_thread(_imported_projects, pm)

    def project_of(post: LibraryPost) -> Optional[ProjectListSummary]:
        return imported.get(article_key(post.url) or "")

    imported_count = sum(1 for post in posts if project_of(post) is not None)
    counts = {"all": len(posts), "not_imported": len(posts) - imported_count, "imported": imported_count}
    if imported_filter != "all":
        want_imported = imported_filter == "imported"
        posts = [post for post in posts if (project_of(post) is not None) == want_imported]

    def to_article(post: LibraryPost) -> SubstackArticle:
        project = project_of(post)
        return _to_article(pm, post, project, variants.get(project.id, []) if project else [])

    page = posts[offset:offset + limit]
    articles = await asyncio.to_thread(lambda: [to_article(post) for post in page])
    return SubstackArticlePage(
        articles=articles,
        next_offset=offset + limit if offset + limit < len(posts) else None,
        total=len(posts),
        pending_digests=library.pending_digests(),
        digesting=library.digest_running(),
        counts=counts,
    )


@router.post("/articles/sync", response_model=SubstackSyncResult)
@limiter.limit("10/minute")
async def sync_articles(
    request: Request,
    library: SubstackLibraryDep,
    full: bool = Query(False),
):
    """平时只看 Substack 最新一页有没有新文章；full=true 把全部清单重新拉一遍。"""
    try:
        added = await run_blocking(library.sync, full=full)
    except SubstackError as error:
        raise _to_api_error(error) from error
    library.start_digest_worker()
    return SubstackSyncResult(added=added, total=library.count())


@router.post("/import", response_model=SubstackImportResponse)
@limiter.limit("20/minute")
async def import_article(
    request: Request,
    body: SubstackImportRequest,
    pm: ProjectManagerDep,
    client: SubstackClientDep,
):
    try:
        requested_url = normalize_article_url(body.url)
    except SubstackError as error:
        raise _to_api_error(error) from error

    # 已导入过的直接返回原项目，不重复下载
    imported, _variants = await asyncio.to_thread(_imported_projects, pm)
    existing = imported.get(article_key(requested_url) or "")
    if existing is not None:
        return SubstackImportResponse(project=_build_project_response(existing), already_imported=True)

    try:
        article = await run_blocking(client.fetch_article, requested_url)
    except SubstackError as error:
        raise _to_api_error(error) from error

    # 分享链接（open.substack.com 等）跳转后才知道真正的原文地址，再查一次
    existing = imported.get(article_key(article.url) or "")
    if existing is not None:
        return SubstackImportResponse(project=_build_project_response(existing), already_imported=True)

    def stage_and_create():
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / f"{article.slug}.html"
            source_path.write_text(article.html, encoding="utf-8")
            return pm.create((body.name or "").strip() or article.title, str(source_path))

    try:
        meta = await run_blocking(stage_and_create)
    except ValueError as error:
        if "already exists" in str(error):
            raise APIException(
                status_code=409,
                detail=f"已经有同名项目「{article.title}」，请换个项目名再导入",
                error_code="PROJECT_EXISTS",
            ) from error
        raise APIException(status_code=400, detail=str(error), error_code="BAD_REQUEST") from error
    return SubstackImportResponse(project=_build_project_response(meta))


@router.get("/cookie", response_model=SubstackCookieStatus)
async def get_cookie_status(client: SubstackClientDep):
    configured = await asyncio.to_thread(client.cookie_store.is_configured)
    return SubstackCookieStatus(configured=configured, domain=client.cookie_store.domain)


@router.put("/cookie", response_model=SubstackCookieStatus)
@limiter.limit("10/minute")
async def save_cookie(request: Request, body: SubstackCookieRequest, client: SubstackClientDep):
    # 只回状态，永不回显 cookie 本身
    try:
        await asyncio.to_thread(client.cookie_store.save, body.cookie)
    except SubstackError as error:
        raise _to_api_error(error) from error
    return SubstackCookieStatus(configured=True, domain=client.cookie_store.domain)
