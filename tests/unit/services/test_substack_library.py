import json

import pytest

from src.services.substack_library import (
    MAX_DIGEST_ATTEMPTS,
    LibraryPost,
    SubstackLibrary,
    parse_digest_response,
)
from src.services.substack_service import ArchivePost


def _post(n: int, title: str = "", subtitle: str = "") -> ArchivePost:
    return ArchivePost(
        title=title or f"Post {n}",
        subtitle=subtitle,
        slug=f"post-{n}",
        url=f"https://newsletter.semianalysis.com/p/post-{n}",
        post_date=f"2026-01-01T00:00:{n:02d}Z" if n < 60 else f"2026-01-01T00:{n // 60:02d}:{n % 60:02d}Z",
        is_paid=n % 2 == 0,
        cover_image=None,
        wordcount=1000 + n,
        excerpt=f"Opening paragraph of post {n}.",
    )


class FakeArchive:
    """模拟 Substack 的归档接口：从新到旧，每页最多 page_size 篇，hidden 的文章不返回。"""

    def __init__(self, posts, page_size=25, hidden=()):
        self.posts = list(posts)
        self.page_size = page_size
        self.hidden = set(hidden)
        self.offsets = []

    def list_archive(self, *, offset=0, limit=24, search=""):
        self.offsets.append(offset)
        window = self.posts[offset:offset + min(limit, self.page_size)]
        return [post for post in window if post.slug not in self.hidden]


def _newest_first(count):
    return [_post(n) for n in range(count, 0, -1)]


def _library(tmp_path, archive, digest_fn=None):
    return SubstackLibrary(tmp_path / "library.json", client_factory=lambda: archive, digest_fn=digest_fn)


def test_first_open_pulls_every_page_and_persists(tmp_path):
    archive = FakeArchive(_newest_first(60))
    library = _library(tmp_path, archive)
    library.ensure_synced()

    assert library.count() == 60
    assert [p.slug for p in library.posts()][:2] == ["post-60", "post-59"]
    assert library.posts()[0].excerpt == "Opening paragraph of post 60."

    reopened = _library(tmp_path, FakeArchive([]))
    reopened.ensure_synced()
    assert reopened.count() == 60  # 从文件读回来，不再去拉


def test_quick_sync_only_reads_the_first_page_when_nothing_is_new(tmp_path):
    archive = FakeArchive(_newest_first(60))
    library = _library(tmp_path, archive)
    library.ensure_synced()
    archive.offsets.clear()

    archive.posts = [_post(62), _post(61)] + archive.posts
    assert library.sync() == 2
    assert archive.offsets == [0]
    assert library.count() == 62


def test_quick_sync_keeps_paging_until_it_reaches_a_known_article(tmp_path):
    archive = FakeArchive(_newest_first(10))
    library = _library(tmp_path, archive)
    library.ensure_synced()

    archive.posts = _newest_first(70)  # 一下子多了 60 篇新的，超过两页
    assert library.sync() == 60
    assert library.count() == 70


def test_hidden_articles_shrink_pages_without_skipping_any(tmp_path):
    archive = FakeArchive(_newest_first(80), hidden={"post-75", "post-50", "post-49"})
    library = _library(tmp_path, archive)
    library.ensure_synced()
    assert library.count() == 77


def test_full_sync_drops_deleted_articles_and_regenerates_changed_titles(tmp_path):
    archive = FakeArchive([_post(3), _post(2), _post(1)])
    library = _library(tmp_path, archive, digest_fn=lambda posts: {
        p.slug: {"zh_title": f"中文{p.slug}", "zh_summary": "摘要"} for p in posts
    })
    library.ensure_synced()
    library.generate_digests()

    archive.posts = [_post(3, title="Renamed"), _post(1)]
    library.sync(full=True)
    posts = {p.slug: p for p in library.posts()}
    assert set(posts) == {"post-3", "post-1"}
    assert posts["post-1"].zh_title == "中文post-1"
    assert posts["post-3"].zh_title == "" and posts["post-3"].needs_digest


def test_search_covers_chinese_digest_and_requires_every_word(tmp_path):
    archive = FakeArchive([_post(2, title="HBM4 Supply"), _post(1, title="TPU Roadmap")])
    library = _library(tmp_path, archive, digest_fn=lambda posts: {
        p.slug: {"zh_title": "存储" if "HBM" in p.title else "谷歌芯片", "zh_summary": ""} for p in posts
    })
    library.ensure_synced()
    library.generate_digests()

    assert [p.slug for p in library.posts("存储")] == ["post-2"]
    assert [p.slug for p in library.posts("hbm4 supply")] == ["post-2"]
    assert library.posts("hbm4 roadmap") == []


def test_digests_are_generated_in_batches_and_saved(tmp_path):
    batches = []

    def digest(posts):
        batches.append([p.slug for p in posts])
        return {p.slug: {"zh_title": f"标题{p.slug}", "zh_summary": "一句话"} for p in posts}

    library = _library(tmp_path, FakeArchive(_newest_first(25)), digest_fn=digest)
    library.ensure_synced()
    assert library.pending_digests() == 25

    assert library.generate_digests() == 25
    assert [len(b) for b in batches] == [10, 10, 5]
    assert batches[0][0] == "post-25"  # 先给最新的文章生成
    assert library.pending_digests() == 0

    saved = json.loads((tmp_path / "library.json").read_text(encoding="utf-8"))
    assert saved["posts"][0]["zh_title"] == "标题post-25"


def test_model_outage_pauses_without_giving_up_on_articles(tmp_path, monkeypatch):
    calls = []

    def broken(posts):
        calls.append(len(posts))
        raise RuntimeError("relay down")

    library = _library(tmp_path, FakeArchive(_newest_first(3)), digest_fn=broken)
    library.ensure_synced()
    assert library.generate_digests() == 0
    assert calls == [3]  # 出错就停下，不接着打下一批
    assert library.pending_digests() == 3  # 不算单篇失败，服务恢复后还会生成

    library.start_digest_worker()  # 冷却期内不重开
    assert library._digest_thread is None and not library.digest_running()

    import src.services.substack_library as module
    monkeypatch.setattr(module.time, "monotonic", lambda: library._digest_retry_at + 1)
    library.start_digest_worker()
    library._digest_thread.join(timeout=5)
    assert calls == [3, 3]


def test_truncated_replies_shrink_the_batch_instead_of_stalling(tmp_path):
    from src.llm.errors import LLMOutputTruncatedError

    sizes = []

    def long_winded(posts):
        sizes.append(len(posts))
        if len(posts) > 3 or any(p.slug == "post-1" for p in posts):  # 带上 post-1 就会被截断
            raise LLMOutputTruncatedError("Model generation reached its output limit")
        return {p.slug: {"zh_title": "短", "zh_summary": ""} for p in posts}

    library = _library(tmp_path, FakeArchive(_newest_first(12)), digest_fn=long_winded)
    library.ensure_synced()
    assert library.generate_digests() == 11
    assert sizes[:3] == [10, 5, 2]  # 逐步减半直到不再截断
    assert library.pending_digests() == 0  # post-1 试满次数后放弃，不会卡住
    assert library._digest_retry_at == 0  # 截断不触发冷却


def test_missing_items_in_a_reply_count_as_one_failed_attempt(tmp_path):
    library = _library(tmp_path, FakeArchive([_post(2), _post(1)]), digest_fn=lambda posts: {
        "post-2": {"zh_title": "有结果", "zh_summary": ""}
    })
    library.ensure_synced()
    library.generate_digests()
    posts = {p.slug: p for p in library.posts()}
    assert posts["post-2"].zh_title == "有结果"
    assert posts["post-1"].digest_misses == MAX_DIGEST_ATTEMPTS  # 每轮都缺它，直到放弃


def test_background_worker_fills_digests(tmp_path):
    library = _library(tmp_path, FakeArchive([_post(1)]), digest_fn=lambda posts: {
        p.slug: {"zh_title": "后台生成", "zh_summary": ""} for p in posts
    })
    library.ensure_synced()
    library.start_digest_worker()
    library._digest_thread.join(timeout=5)
    assert library.posts()[0].zh_title == "后台生成"


def test_corrupt_store_file_is_rebuilt(tmp_path):
    (tmp_path / "library.json").write_text("{not json", encoding="utf-8")
    library = _library(tmp_path, FakeArchive([_post(1)]))
    library.ensure_synced()
    assert library.count() == 1


def test_old_store_entries_without_new_fields_still_load(tmp_path):
    (tmp_path / "library.json").write_text(json.dumps({"posts": [{
        "title": "T", "subtitle": "", "slug": "t", "url": "https://x.substack.com/p/t",
        "post_date": "2026-01-01", "is_paid": False, "cover_image": None, "wordcount": None,
        "unknown_field": 1,
    }]}), encoding="utf-8")
    library = _library(tmp_path, FakeArchive([]))
    assert library.posts()[0] == LibraryPost(
        title="T", subtitle="", slug="t", url="https://x.substack.com/p/t",
        post_date="2026-01-01", is_paid=False, cover_image=None, wordcount=None,
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('[{"slug": "a", "zh_title": " 标题 ", "zh_summary": "摘要"}]', {"a": {"zh_title": "标题", "zh_summary": "摘要"}}),
        ('```json\n[{"slug": "a", "zh_title": "标题"}]\n```', {"a": {"zh_title": "标题", "zh_summary": ""}}),
        ('{"articles": [{"slug": "a", "zh_title": "标题", "zh_summary": "s"}]}', {"a": {"zh_title": "标题", "zh_summary": "s"}}),
        ('[{"slug": "a", "zh_title": "标题", "zh_summary": "文章探讨了 HBM"}]', {"a": {"zh_title": "标题", "zh_summary": "探讨了 HBM"}}),
        ('[{"slug": "a", "zh_title": ""}, {"zh_title": "无 slug"}, "x", {"slug": "b", "zh_title": 3}]', {}),
        ("not json", {}),
        ("", {}),
        # 2026-10-25 线上真实回复：JSON 模式下只回了单篇对象
        ('{"slug": "a", "zh_title": "标题", "zh_summary": "s"}', {"a": {"zh_title": "标题", "zh_summary": "s"}}),
        ('{"results": [{"slug": "a", "zh_title": "标题"}]}', {"a": {"zh_title": "标题", "zh_summary": ""}}),
    ],
)
def test_parse_digest_response(raw, expected):
    assert parse_digest_response(raw) == expected


def test_posts_given_up_under_the_old_counter_are_retried(tmp_path):
    (tmp_path / "library.json").write_text(json.dumps({"posts": [{
        "title": "T", "subtitle": "", "slug": "t", "url": "https://x.substack.com/p/t",
        "post_date": "2026-01-01", "is_paid": False, "cover_image": None, "wordcount": None,
        "zh_title": "", "digest_attempts": 3,
    }]}), encoding="utf-8")
    library = _library(tmp_path, FakeArchive([]))
    assert library.posts()[0].needs_digest
