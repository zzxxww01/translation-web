"""Muse 自动化接口（/internal/automation）：只许本机、updates 水位线、translate-article 幂等、status 映射。"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from src.api.middleware import APIException, ConflictException
from src.api.routers import automation
from src.core.project import ProjectManager
from src.services.substack_library import SubstackLibrary
from src.services.substack_service import ArchivePost, FetchedArticle, SubstackCookieStore, SubstackError

URL_NEW = "https://newsletter.semianalysis.com/p/new-post"
URL_OLD = "https://newsletter.semianalysis.com/p/old-post"
HTML = f"""<html><head><title>New Post</title><meta property="og:url" content="{URL_NEW}"></head><body>
<article class="newsletter-post post"><div class="post-header"><h1 class="post-title">New Post</h1></div>
<div class="available-content"><div class="body markup">
<p>First paragraph of the article body with enough words to be kept.</p>
<p>Another paragraph in the article with enough words as well.</p>
</div></div></article></body></html>"""


def _request(headers=(), host="127.0.0.1") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/internal/automation/x",
                    "headers": [(k.encode(), v.encode()) for k, v in headers], "client": (host, 50000)})


def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


class FakeClient:
    def __init__(self, tmp_path):
        self.cookie_store = SubstackCookieStore(cookie_file=tmp_path / "cookie.txt",
                                                domain="newsletter.semianalysis.com")
        self.fetched = []
        self.archive_error = None

    def fetch_article(self, url):
        self.fetched.append(url)
        return FetchedArticle(url=URL_NEW, slug="new-post", title="New Post", html=HTML)

    def list_archive(self, *, cursor=None, limit=24, search=""):
        if self.archive_error:
            raise self.archive_error
        return [
            ArchivePost(title="New Post", subtitle="", slug="new-post", url=URL_NEW,
                        post_date="2026-11-17T10:00:00.000Z", is_paid=True, cover_image=None, wordcount=4894),
            ArchivePost(title="Old Post", subtitle="", slug="old-post", url=URL_OLD,
                        post_date="2026-10-01T10:00:00.000Z", is_paid=False, cover_image=None, wordcount=900),
        ], None


class FakeInbox:
    def __init__(self, configured=True, error=None):
        self.store = SimpleNamespace(load=lambda: object() if configured else None)
        self.error = error
        self.synced = 0
        self.since = None

    def sync_all(self):
        if self.error:
            raise self.error
        self.synced += 1

    def mentions_since(self, since, group_ids):
        self.since = since
        return [{"conversation_id": "C1", "message_ts": "1.0", "mention_type": "direct"}] if since < 100 else []


@pytest.fixture
def env(tmp_path, monkeypatch):
    pm = ProjectManager(projects_path=str(tmp_path / "projects"))
    client = FakeClient(tmp_path)
    library = SubstackLibrary(tmp_path / "library.json", client_factory=lambda: client)
    inbox = FakeInbox()
    monkeypatch.setattr(automation, "get_project_manager", lambda: pm)
    monkeypatch.setattr(automation, "get_substack_client", lambda: client)
    monkeypatch.setattr(automation, "get_substack_library", lambda: library)
    monkeypatch.setattr(automation, "get_slack_inbox", lambda: inbox)
    return SimpleNamespace(pm=pm, client=client, library=library, inbox=inbox, monkeypatch=monkeypatch)


# ---------------------------------------------------------------- 只许本机


@pytest.mark.parametrize("headers,host", [
    ((("x-forwarded-for", "1.2.3.4"),), "127.0.0.1"),
    ((("cf-connecting-ip", "1.2.3.4"),), "127.0.0.1"),
    ((("x-real-ip", "1.2.3.4"),), "127.0.0.1"),
    ((), "10.0.0.5"),
])
def test_require_local_rejects_proxied_or_remote(headers, host):
    with pytest.raises(APIException) as exc:
        automation.require_local(_request(headers, host))
    assert exc.value.status_code == 403


def test_require_local_allows_loopback():
    automation.require_local(_request())
    automation.require_local(_request(host="::1"))


def test_router_is_outside_api_prefix_and_guarded():
    from fastapi.testclient import TestClient
    from src.api.app import app
    with TestClient(app) as client:
        # 挂在 /internal 下（nginx 只转发 /api/）；经过代理的请求在进到接口前就被拒
        proxied = client.get("/internal/automation/health", headers={"X-Forwarded-For": "1.2.3.4"})
        assert proxied.status_code == 403 and proxied.json()["error_code"] == "FORBIDDEN"
        # TestClient 的来源不是回环地址，同样拒绝
        assert client.get("/internal/automation/health").status_code == 403
        assert client.get("/api/internal/automation/health").status_code == 404


# ---------------------------------------------------------------- updates


@pytest.mark.asyncio
async def test_updates_returns_new_since_and_watermark_empties_next_call(env):
    since = _epoch("2026-11-01T00:00:00Z")
    first = await automation.updates(since=since)
    assert [a["slug"] for a in first["new_articles"]] == ["new-post"]
    article = first["new_articles"][0]
    assert article["status"] == "not_imported" and article["paid"] is True and article["word_count"] == 4894
    assert first["mentions"] == []  # FakeInbox 只在 since < 100 时返回
    assert "warnings" not in first
    assert env.inbox.synced == 1

    again = await automation.updates(since=_epoch(first["watermark"]))
    assert again["new_articles"] == [] and again["mentions"] == []
    assert _epoch(again["watermark"]) >= _epoch(first["watermark"])


@pytest.mark.asyncio
async def test_updates_never_imports_or_translates(env):
    await automation.updates(since=0)
    assert env.pm.list_summaries(include_variants=True) == []
    assert env.client.fetched == []


@pytest.mark.asyncio
async def test_updates_slack_failure_keeps_watermark(env):
    env.inbox.error = RuntimeError("boom")
    result = await automation.updates(since=50)
    assert result["watermark"] == datetime.fromtimestamp(50, timezone.utc).isoformat().replace("+00:00", "Z")
    assert "slack" in result["warnings"]
    assert len(result["new_articles"]) == 2  # 文章照常返回


@pytest.mark.asyncio
async def test_updates_substack_failure_still_answers_from_cache(env):
    await automation.updates(since=0)  # 先把清单存下来
    env.client.archive_error = SubstackError("UPSTREAM_ERROR", "Substack 暂时打不开")
    result = await automation.updates(since=0)
    assert result["warnings"]["substack"] == "Substack 暂时打不开"
    assert len(result["new_articles"]) == 2


# ---------------------------------------------------------------- translate-article


def _fake_workflow(env, *, conflict=False):
    calls = []

    async def wrapped(*, request, project_id, service, body):
        calls.append((project_id, body))
        if conflict:
            raise ConflictException(detail="busy")
        await asyncio.sleep(0)
        return {"status": "started", "run_id": "r1", "resumed": False}

    env.monkeypatch.setattr(automation, "start_longform_workflow", SimpleNamespace(__wrapped__=wrapped))
    env.monkeypatch.setattr(automation, "get_batch_service", lambda: None)
    return calls


@pytest.mark.asyncio
async def test_translate_article_imports_and_starts_four_step_with_auto_terms(env):
    calls = _fake_workflow(env)
    result = await automation.translate_article(_request(), automation.TranslateArticleRequest(article="new-post"))
    assert result["status"] == "started"
    assert result["url"].endswith(f"/articles/{result['project_id']}")
    (project_id, body), = calls
    assert project_id == result["project_id"]
    assert body.method == "four-step" and body.auto_accept_terms is True


@pytest.mark.asyncio
async def test_translate_article_is_idempotent_and_serialised(env):
    calls = _fake_workflow(env)
    states = iter([("imported", 0), ("translating", 0)])
    env.monkeypatch.setattr(automation, "_translation_state", lambda *a, **k: next(states))
    req = automation.TranslateArticleRequest(article="new-post")
    first, second = await asyncio.gather(automation.translate_article(_request(), req),
                                         automation.translate_article(_request(), req))
    assert {first["status"], second["status"]} == {"started", "already_exists"}
    assert first["project_id"] == second["project_id"]
    assert len(env.pm.list_summaries(include_variants=True)) == 1
    assert len(calls) == 1
    assert env.client.fetched == [URL_NEW]  # 第二次没有重新下载


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["translating", "awaiting_terms", "translated"])
async def test_translate_article_returns_existing_project(env, state):
    calls = _fake_workflow(env)
    env.monkeypatch.setattr(automation, "_translation_state", lambda *a, **k: (state, 40))
    result = await automation.translate_article(_request(), automation.TranslateArticleRequest(article=URL_NEW))
    assert result["status"] == "already_exists" and result["translation_status"] == state
    assert calls == []


@pytest.mark.asyncio
async def test_translate_article_slot_conflict_counts_as_existing(env):
    _fake_workflow(env, conflict=True)
    result = await automation.translate_article(_request(), automation.TranslateArticleRequest(article="new-post"))
    assert result["status"] == "already_exists"


@pytest.mark.asyncio
async def test_translate_article_unknown_slug_and_language(env):
    _fake_workflow(env)
    with pytest.raises(APIException) as exc:
        await automation.translate_article(_request(), automation.TranslateArticleRequest(article="nope"))
    assert exc.value.status_code == 404
    with pytest.raises(APIException):
        await automation.translate_article(
            _request(), automation.TranslateArticleRequest(article="new-post", target_lang="ja"))


# ---------------------------------------------------------------- status


class FakeStatusService:
    def __init__(self, payload):
        self.payload = payload

    async def get_translation_progress(self, project_id):
        return self.payload


async def _imported_project(env):
    _fake_workflow(env)
    env.monkeypatch.setattr(automation, "_translation_state", lambda *a, **k: ("imported", 0))
    result = await automation.translate_article(_request(), automation.TranslateArticleRequest(article="new-post"))
    return result["project_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("state,payload,expected", [
    (("translating", 30), {"status": "processing", "current_step": "第 2 章"}, "running"),
    (("awaiting_terms", 0), {"status": "starting"}, "running"),
    (("translated", 100), {"status": "completed"}, "done"),
    (("partial", 60), {"status": "failed", "errors": [{"error": "model timeout"}]}, "failed"),
    (("partial", 60), {"status": "idle"}, "failed"),
    (("imported", 0), {"status": "idle"}, "not_started"),
])
async def test_status_mapping(env, state, payload, expected):
    project_id = await _imported_project(env)
    env.monkeypatch.setattr(automation, "_translation_state", lambda *a, **k: state)
    env.monkeypatch.setattr(automation, "get_translation_status_service", lambda: FakeStatusService(payload))
    result = await automation.project_status(project_id)
    assert result["status"] == expected
    assert result["progress"] == state[1]
    if expected == "done":
        assert result["result"].endswith(f"/articles/{project_id}")
    else:
        assert result["result"] is None
    if expected == "failed":
        assert result["error"]
    if expected == "running":
        assert result["stage"] == payload.get("current_step")


@pytest.mark.asyncio
async def test_status_unknown_project(env):
    env.monkeypatch.setattr(automation, "get_translation_status_service", lambda: FakeStatusService({}))
    with pytest.raises(APIException) as exc:
        await automation.project_status("missing-project")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------- translate-slack


class SlackSourceInbox(FakeInbox):
    def __init__(self, text="Hello world"):
        super().__init__()
        self.text = text

    def translation_source(self, cid, ts, thread_ts, with_thread):
        return {"source_text": self.text, "messages": 2 if with_thread else 1,
                "permalink": f"https://team.slack.com/archives/{cid}/p{ts.replace('.', '')}"}


def _fake_post(env):
    calls = []

    async def wrapped(*, request, body):
        calls.append(body)
        await asyncio.sleep(0)
        return SimpleNamespace(translation=f"译文：{body.content}", model_used=body.model)

    env.monkeypatch.setattr(automation, "translate_post", SimpleNamespace(__wrapped__=wrapped))
    return calls


@pytest.fixture
def slack_env(env, tmp_path):
    env.monkeypatch.setattr(automation.settings, "slack_cache_dir", str(tmp_path / "slack_cache"))
    env.inbox = SlackSourceInbox()
    env.monkeypatch.setattr(automation, "get_slack_inbox", lambda: env.inbox)
    return env


@pytest.mark.asyncio
async def test_translate_slack_translates_once_and_caches(slack_env):
    calls = _fake_post(slack_env)
    req = automation.TranslateSlackRequest(conversation_id="C0123456789", message_ts="1763424000.000100")
    first, second = await asyncio.gather(automation.translate_slack(_request(), req),
                                         automation.translate_slack(_request(), req))
    assert {first["status"], second["status"]} == {"done", "already_exists"}
    assert first["project_id"] == second["project_id"] == "slack-C0123456789-1763424000.000100"
    assert first["translation"] == "译文：Hello world"
    (body,) = calls
    assert body.model == "gpt-6.2-sol" and body.include_hashtags is False

    status = await automation.project_status(first["project_id"])
    assert status["status"] == "done" and status["result"] == "译文：Hello world"

    # 消息被编辑过（内容变了）才重新翻
    slack_env.inbox.text = "Hello world, edited"
    third = await automation.translate_slack(_request(), req)
    assert third["status"] == "done" and len(calls) == 2


@pytest.mark.asyncio
async def test_translate_slack_thread_has_its_own_id(slack_env):
    _fake_post(slack_env)
    result = await automation.translate_slack(_request(), automation.TranslateSlackRequest(
        conversation_id="C0123456789", message_ts="1763424000.000100", with_thread=True))
    assert result["project_id"].endswith("-thread") and result["messages"] == 2


@pytest.mark.asyncio
async def test_translate_slack_rejects_empty_and_too_long(slack_env):
    calls = _fake_post(slack_env)
    req = automation.TranslateSlackRequest(conversation_id="C0123456789", message_ts="1763424000.000100")
    for text, code in (("   ", "EMPTY_MESSAGE"), ("x" * 10001, "TOO_LONG")):
        slack_env.inbox.text = text
        with pytest.raises(APIException) as exc:
            await automation.translate_slack(_request(), req)
        assert exc.value.error_code == code
    assert calls == []


@pytest.mark.asyncio
async def test_slack_status_unknown(slack_env):
    with pytest.raises(APIException) as exc:
        await automation.project_status("slack-C0123456789-1.0")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------- slack-todos / drafts / draft / translate-slack-post

DRAFT_ID = "s_C0123456789_1763424000_000100"


class ImageInbox:
    def __init__(self, files):
        self.files = files  # id -> (path, mimetype, name)
        self.replies_calls = []

    def replies(self, channel_id, thread_ts):
        self.replies_calls.append((channel_id, thread_ts))

    def file(self, file_id):
        from src.services.slack_inbox import SlackInboxError
        if file_id not in self.files:
            raise SlackInboxError("FILE_UNKNOWN", "先打开包含这个文件的消息再下载", 404)
        return self.files[file_id]


@pytest.fixture
def drafts_env(env, tmp_path):
    from src.services.post_drafts import PostDraftStore
    store = PostDraftStore(tmp_path / "drafts")
    env.monkeypatch.setattr(automation, "get_draft_store", lambda: store)
    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNG fake image bytes")
    env.inbox = ImageInbox({"FAAAAAAA1": (img, "image/png", "chart.png")})
    env.monkeypatch.setattr(automation, "get_slack_inbox", lambda: env.inbox)
    state = {"originalText": "AI racks are here", "versions": [
        {"id": "v1", "content": "旧译文"}, {"id": "v2", "content": "AI 机柜来了"}], "currentVersionId": "v2",
        "generatedTitles": ["标题一", "标题二"], "selectedTitle": ""}
    store.put_system({"id": DRAFT_ID, "source": "slack", "status": "draft", "auto": True, "seen": False,
                      "slack": {"channel_id": "C0123456789", "thread_ts": "1763424000.000100",
                                "channel_name": "social", "title": "AI racks", "permalink": "https://x/p1"},
                      "extraction": {"has_post": True, "note": ""},
                      "images": [{"id": "FAAAAAAA1", "name": "chart.png"}, {"id": "FBBBBBBB2", "name": "gone.png"}],
                      "state": state})
    store.save("m_0123456789ab", {"state": {"originalText": "done one", "versions": []}, "status": "done"},
               rev=None, source="manual")
    env.store = store
    return env


@pytest.mark.asyncio
async def test_drafts_lists_unconfirmed_by_default(drafts_env):
    result = await automation.drafts(status="draft", source="", q="", limit=50)
    assert result["total"] == 1
    (item,) = result["items"]
    assert item["draft_id"] == DRAFT_ID and item["title"] == "标题一" and item["image_count"] == 2
    assert item["slack"]["conversation_id"] == "C0123456789" and item["auto"] is True
    everything = await automation.drafts(status="all", source="", q="", limit=50)
    assert {i["draft_id"] for i in everything["items"]} == {DRAFT_ID, "m_0123456789ab"}


@pytest.mark.asyncio
async def test_draft_returns_translation_titles_and_original_images(drafts_env):
    import base64
    result = await automation.draft(DRAFT_ID, images=True)
    assert result["translation"] == "AI 机柜来了" and result["source_text"] == "AI racks are here"
    assert result["titles"] == ["标题一", "标题二"] and result["slack"]["permalink"] == "https://x/p1"
    assert result["link"].endswith("/slack?mode=translate&tc=C0123456789&t=1763424000.000100")
    first, missing = result["images"]
    assert base64.b64decode(first["data_base64"]) == b"\x89PNG fake image bytes"
    assert first["n"] == 1 and first["mimetype"] == "image/png" and first["size"] == 21 and len(first["sha256"]) == 64
    assert missing["n"] == 2 and "error" in missing and "data_base64" not in missing
    assert drafts_env.inbox.replies_calls == [("C0123456789", "1763424000.000100")]

    light = await automation.draft(DRAFT_ID, images=False)
    assert "data_base64" not in light["images"][0] and light["images"][0]["size"] == 21


@pytest.mark.asyncio
async def test_draft_oversized_image_gives_metadata_only(drafts_env):
    drafts_env.monkeypatch.setattr(automation, "MAX_IMAGE_BYTES", 5)
    result = await automation.draft(DRAFT_ID, images=True)
    assert "data_base64" not in result["images"][0] and result["images"][0]["error"]


@pytest.mark.asyncio
async def test_draft_unknown_and_bad_id(drafts_env):
    with pytest.raises(APIException) as exc:
        await automation.draft("m_000000000000", images=True)
    assert exc.value.status_code == 404
    with pytest.raises(APIException) as exc:
        await automation.draft("../x", images=True)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_translate_slack_post_runs_the_web_pipeline(drafts_env):
    calls = []

    async def fake_pipeline(channel_id, thread_ts, *, instruction=None, auto=False):
        calls.append((channel_id, thread_ts, instruction, auto))
        return drafts_env.store.get(DRAFT_ID)

    drafts_env.monkeypatch.setattr(automation, "run_slack_pipeline", fake_pipeline)
    result = await automation.translate_slack_post(automation.TranslateSlackPostRequest(
        conversation_id="C0123456789", thread_ts="1763424000.000100", instruction="翻第二版", with_images=False))
    assert calls == [("C0123456789", "1763424000.000100", "翻第二版", True)]
    assert result["draft_id"] == DRAFT_ID and "data_base64" not in result["images"][0]


@pytest.mark.asyncio
async def test_slack_todos_uses_the_web_todos(env):
    item = {"kind": "mention", "action": "do", "task": "Daksh 让你翻这篇", "title": "AI racks", "channel_name": "social",
            "from": ["Daksh"], "count": 2, "channel_id": "C0123456789", "thread_ts": "1763424000.000100",
            "latest_ts": "1763424000.000300", "conversation_kind": "channel", "mark": {},
            "draft": {"id": DRAFT_ID, "status": "draft", "auto": True, "seen": False, "versions": 1, "no_post": False}}

    async def fake_todos():
        return {"items": [item], "fyi": []}

    env.monkeypatch.setattr(automation, "build_todos", fake_todos)
    result = await automation.slack_todos()
    (todo,) = result["items"]
    assert todo["where"] == "#social" and todo["conversation_id"] == "C0123456789"
    assert todo["draft"] == {"draft_id": DRAFT_ID, "status": "draft", "versions": 1, "no_post": False}
    assert todo["latest_at"].endswith("Z") and result["fyi"] == []


# ---------------------------------------------------------------- translate-post / slack-reply


@pytest.mark.asyncio
async def test_translate_post_uses_web_pipeline_without_hashtags(env):
    calls = _fake_post(env)
    result = await automation.translate_post_text(_request(), automation.TranslatePostRequest(content="Hello"))
    assert result["translation"] == "译文：Hello"
    (body,) = calls
    assert body.include_hashtags is False and body.model is None
    await automation.translate_post_text(_request(), automation.TranslatePostRequest(content="Hi", hashtags=True))
    assert calls[1].include_hashtags is True


@pytest.mark.asyncio
async def test_translate_post_rejects_blank(env):
    calls = _fake_post(env)
    with pytest.raises(APIException) as exc:
        await automation.translate_post_text(_request(), automation.TranslatePostRequest(content="   "))
    assert exc.value.error_code == "EMPTY_MESSAGE" and calls == []


def _fake_reply(env):
    calls = []
    variant = SimpleNamespace(version="A", style="简洁", english="Sounds good.", chinese="好的。")

    async def process(*, request, body):
        calls.append(("incoming", body))
        return SimpleNamespace(translation="听起来不错", suggested_replies=[variant], model_used="m")

    async def compose(*, request, body):
        calls.append(("compose", body))
        return SimpleNamespace(versions=[variant], model_used="m")

    env.monkeypatch.setattr(automation, "process_slack_message", SimpleNamespace(__wrapped__=process))
    env.monkeypatch.setattr(automation, "compose_slack_message", SimpleNamespace(__wrapped__=compose))
    return calls


@pytest.mark.asyncio
async def test_slack_reply_picks_mode_and_passes_history(env):
    calls = _fake_reply(env)
    history = [{"role": "them", "content": "Can you check?"}]
    incoming = await automation.slack_reply(_request(), automation.SlackReplyRequest(
        text="Looks good to me", history=history))
    assert incoming["mode"] == "incoming" and incoming["translation"] == "听起来不错"
    assert incoming["replies"] == [{"version": "A", "style": "简洁", "english": "Sounds good.", "chinese": "好的。"}]
    assert calls[0][1].message == "Looks good to me" and calls[0][1].conversation_history[0].role == "them"

    compose = await automation.slack_reply(_request(), automation.SlackReplyRequest(text="我明天看一下"))
    assert compose["mode"] == "compose" and compose["translation"] is None
    assert calls[1][0] == "compose" and calls[1][1].content == "我明天看一下"

    forced = await automation.slack_reply(_request(), automation.SlackReplyRequest(text="我明天看", mode="incoming"))
    assert forced["mode"] == "incoming"
