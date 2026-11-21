import os
import stat

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import register_error_handlers
from src.api.routers import slack_inbox as slack_inbox_router
from src.services.slack_inbox import (
    ALLOWED_METHODS,
    SlackCredentialStore,
    SlackInbox,
    SlackInboxError,
    SlackReadOnlyClient,
    export_to_markdown,
    agent_context_markdown,
    mpim_label,
    normalize_credentials,
    parse_slack_text,
)

NOW = 1_800_000_000.0
DAY = 86400
ME = "UME0000001"

USERS = {
    "UAAAAAAAA1": {"name": "alice", "profile": {"display_name": "Alice", "real_name": "Alice A"}},
    "UBBBBBBBB2": {"name": "bob", "profile": {"real_name": "Bob B"}},
    "UBOT000003": {"name": "bot", "is_bot": True, "profile": {}},
    ME: {"name": "me", "profile": {"display_name": "me"}},
}

CONVERSATIONS = {
    "C000000001": {"name": "social", "is_private": False},
    "D000000001": {"is_im": True, "user": "UAAAAAAAA1"},   # 最近有往来
    "D000000002": {"is_im": True, "user": "UBBBBBBBB2"},   # 很久没往来
    "D000000003": {"is_im": True, "user": "USLACKBOT"},
    "D000000004": {"is_im": True, "user": ME},
    "D000000005": {"is_im": True, "user": "UBOT000003"},
    "G000000001": {"is_mpim": True, "name": "mpdm-a--b--me-1", "purpose": {"value": ""}},
    "C000000002": {"name": "alpha", "is_private": False},  # 只在侧栏（userBoot）里，counts 没有
    "C000000003": {"name": "old", "is_archived": True},
}


def _counts():
    recent = f"{NOW - 2 * DAY:.6f}"
    old = f"{NOW - 90 * DAY:.6f}"
    return {
        "ok": True,
        "channels": [{"id": "C000000001", "latest": recent, "has_unreads": True, "last_read": f"{NOW - 3 * DAY:.6f}"}],
        "threads": {"has_unreads": True, "mention_count": 1,
                    "unread_count_by_channel": {"C000000001": 1}, "mention_count_by_channel": {"C000000001": 1}},
        "mpims": [{"id": "G000000001", "latest": recent}],
        "ims": [
            {"id": "D000000001", "latest": recent},
            {"id": "D000000002", "latest": old},
            {"id": "D000000003", "latest": recent},
            {"id": "D000000004", "latest": recent},
            {"id": "D000000005", "latest": recent},
        ],
    }


THREAD_TS = f"{NOW - DAY:.6f}"


def _boot():
    return {
        "ok": True,
        "channels": [
            {"id": "C000000002", "is_channel": True, "name": "alpha"},
            {"id": "C000000003", "is_channel": True, "name": "old", "is_archived": True},
            {"id": "C000000001", "is_channel": True, "name": "social"},
        ],
        # 很久没往来但在 Slack 侧栏里打开着的私信也要显示
        "ims": [{"id": "D000000002", "is_im": True, "user": "UBBBBBBBB2", "is_open": True}],
        "is_open": ["D000000002"],
    }


def _thread_view():
    return {
        "ok": True,
        "threads": [
            {
                "root_msg": {"channel": "C000000001", "ts": THREAD_TS, "thread_ts": THREAD_TS, "user": "UAAAAAAAA1",
                             "text": "root", "reply_count": 3, "latest_reply": f"{NOW - 10:.6f}",
                             "last_read": f"{NOW - 100:.6f}"},
                "latest_replies": [
                    {"ts": f"{NOW - 200:.6f}", "user": "UBBBBBBBB2", "text": "old reply", "thread_ts": THREAD_TS},
                    {"ts": f"{NOW - 10:.6f}", "user": "UBBBBBBBB2", "text": f"<@{ME}> ping", "thread_ts": THREAD_TS},
                ],
            },
            {   # 看不到的会话里的 thread 不展示
                "root_msg": {"channel": "C999999999", "ts": THREAD_TS, "thread_ts": THREAD_TS, "text": "x",
                             "reply_count": 1, "latest_reply": THREAD_TS, "last_read": THREAD_TS},
                "latest_replies": [],
            },
        ],
    }


class FakeClient:
    def __init__(self, creds=None):
        self.calls = []
        self.downloads = []

    def call(self, method, **params):
        assert method in ALLOWED_METHODS
        self.calls.append((method, params))
        if method == "client.userBoot":
            return _boot()
        if method == "subscriptions.thread.getView":
            return _thread_view()
        if method == "search.messages":
            return {"ok": True, "messages": {"total": 2, "matches": [
                {"channel": {"id": "C000000001", "name": "social"}, "ts": f"{NOW - 10:.6f}", "user": "UBBBBBBBB2",
                 "text": "HBM yields", "permalink": f"https://team.slack.com/archives/C000000001/p1?thread_ts={THREAD_TS}&cid=C000000001"},
                {"channel": {"id": "C777777777", "name": "secret-other", "is_channel": True}, "ts": f"{NOW:.6f}",
                 "user": "UAAAAAAAA1", "text": "HBM elsewhere", "permalink": "https://team.slack.com/archives/C777777777/p2"},
            ]}}
        if method == "auth.test":
            return {"ok": True, "user": "me", "user_id": ME, "team": "T", "url": "https://team.slack.com/"}
        if method == "client.counts":
            return _counts()
        if method == "conversations.info":
            return {"ok": True, "channel": {"id": params["channel"], **CONVERSATIONS[params["channel"]]}}
        if method == "users.info":
            return {"ok": True, "user": USERS[params["user"]]}
        if method == "conversations.history":
            return {
                "ok": True,
                "has_more": False,
                "messages": [
                    {
                        "ts": f"{NOW:.6f}",
                        "user": "UAAAAAAAA1",
                        "text": "<!subteam^S1> Racks &amp; floors <@UBBBBBBBB2>",
                        "thread_ts": f"{NOW:.6f}",
                        "reply_count": 2,
                        "files": [
                            {"id": "F000000001", "mimetype": "image/png", "name": "a.png",
                             "url_private": "https://files.slack.com/files-pri/T-F1/a.png"},
                            {"id": "F000000002", "mimetype": "image/svg+xml", "name": "evil.svg",
                             "url_private": "https://files.slack.com/files-pri/T-F2/evil.svg"},
                            {"id": "F000000003", "mimetype": "image/png", "name": "x.png",
                             "url_private": "https://evil.example.com/x.png"},
                        ],
                    }
                ],
            }
        if method == "conversations.replies":
            return {
                "ok": True,
                "has_more": False,
                "messages": [
                    {"ts": params["ts"], "user": "UAAAAAAAA1", "text": "root", "thread_ts": params["ts"]},
                    {"ts": f"{NOW + 1:.6f}", "user": "UBBBBBBBB2", "text": "*1/* draft (1/1)", "thread_ts": params["ts"]},
                ],
            }
        raise AssertionError(method)

    def download(self, url):
        self.downloads.append(url)
        return b"<svg onload=alert(1)></svg>" if url.endswith(".svg") else b"PNG", "image/png"


@pytest.fixture
def inbox(tmp_path):
    store = SlackCredentialStore(tmp_path / "creds.json")
    store.save("xoxc-abc", "xoxd-def")
    fake = FakeClient()
    box = SlackInbox(store, cache_dir=tmp_path / "cache", client_factory=lambda creds: fake, now=lambda: NOW)
    box.fake = fake
    return box


def test_whitelist_is_read_only():
    for method in ALLOWED_METHODS:
        verb = method.rsplit(".", 1)[1]
        assert verb in {"test", "counts", "userBoot", "info", "history", "replies", "getView", "messages"}, method


# Slack 及其状态完全只读：发送、改消息、改已读状态的方法一个都不能调
@pytest.mark.parametrize("method", ["chat.postMessage", "chat.update", "chat.delete", "reactions.add", "files.upload",
                                    "conversations.join", "subscriptions.thread.add",
                                    "conversations.mark", "subscriptions.thread.mark"])
def test_client_rejects_methods_outside_whitelist(method):
    def handler(request):  # pragma: no cover - must never be reached
        raise AssertionError("no network call expected")

    client = SlackReadOnlyClient(normalize_credentials("xoxc-a", "xoxd-b"), http=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(SlackInboxError) as exc:
        client.call(method)
    assert exc.value.code == "METHOD_NOT_ALLOWED"


def test_default_client_ignores_env_proxies(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    client = SlackReadOnlyClient(normalize_credentials("xoxc-a", "xoxd-b"))
    assert client._http.trust_env is False


def test_client_sends_credentials_only_to_slack():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

    client = SlackReadOnlyClient(normalize_credentials("xoxc-a", "d=xoxd-b;"), http=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(SlackInboxError) as exc:
        client.call("auth.test")
    assert exc.value.code == "CREDENTIALS_EXPIRED"
    assert seen[0].method == "GET" and seen[0].url.host == "slack.com"
    assert seen[0].headers["cookie"] == "d=xoxd-b"
    with pytest.raises(SlackInboxError) as exc:
        client.download("https://evil.example.com/a.png")
    assert exc.value.code == "FILE_NOT_ALLOWED"
    assert len(seen) == 1


def test_credential_store_validates_and_restricts_permissions(tmp_path):
    store = SlackCredentialStore(tmp_path / "creds.json")
    assert store.load() is None
    with pytest.raises(SlackInboxError):
        store.save("not-a-token", "xoxd-x")
    store.save(" xoxc-a ", "Cookie: d=xoxd-b")
    assert store.load() == normalize_credentials("xoxc-a", "xoxd-b")
    assert stat.S_IMODE(os.stat(tmp_path / "creds.json").st_mode) == 0o600


def test_parse_slack_text():
    names = {"U1": "Alice"}
    segments = parse_slack_text(
        "<@U1> &amp; <!subteam^S9|@social> see <https://x.com/a?b=1&amp;c=2|x.com/a> <!here> <#C1|general> &lt;b&gt;",
        lambda uid: names.get(uid, uid),
    )
    assert segments == [
        {"type": "mention", "text": "@Alice"},
        {"type": "text", "text": " & "},
        {"type": "mention", "text": "@social"},
        {"type": "text", "text": " see "},
        {"type": "link", "url": "https://x.com/a?b=1&c=2", "text": "x.com/a"},
        {"type": "text", "text": " "},
        {"type": "mention", "text": "@here"},
        {"type": "text", "text": " "},
        {"type": "mention", "text": "#general"},
        {"type": "text", "text": " <b>"},
    ]
    # 非 http 链接从不变成可点的 link：有显示名只留名字，没有就原样当文字
    assert parse_slack_text("<javascript:alert(1)|x>", str) == [{"type": "text", "text": "x"}]
    assert parse_slack_text("<javascript:alert(1)>", str) == [{"type": "text", "text": "<javascript:alert(1)>"}]
    assert parse_slack_text("by <slack://user?team=T1&amp;id=U2|Reyk>", str) == [{"type": "text", "text": "by Reyk"}]


def test_conversations_show_sidebar_channels_and_human_dms(inbox):
    convs = inbox.conversations()
    assert [(c["id"], c["kind"], c["name"]) for c in convs] == [
        ("C000000002", "channel", "alpha"),     # 频道按名字排，含 counts 里没有的
        ("C000000001", "channel", "social"),
        ("G000000001", "mpim", "a, b"),
        ("D000000001", "im", "Alice A"),
        ("D000000002", "im", "Bob B"),          # 旧私信但在侧栏打开着
    ]
    social = convs[1]
    assert social["has_unreads"] is True and social["last_read"] == f"{NOW - 3 * DAY:.6f}"
    assert (social["thread_unreads"], social["thread_mentions"]) == (1, 1)
    assert convs[0]["last_read"] is None and convs[0]["has_unreads"] is False
    assert inbox.thread_badge() == {"has_unreads": True, "mention_count": 1}


def test_conversations_fall_back_to_counts_without_user_boot(inbox):
    original = inbox.fake.call

    def call(method, **params):
        if method == "client.userBoot":
            raise SlackInboxError("SLACK_ERROR", "enterprise_is_restricted")
        return original(method, **params)

    inbox.fake.call = call
    assert [c["id"] for c in inbox.conversations()] == ["C000000001", "G000000001", "D000000001"]


def test_followed_threads_track_unread_and_mentions(inbox):
    threads = inbox.threads()["threads"]
    assert len(threads) == 1  # 看不到的会话被过滤
    t = threads[0]
    assert (t["channel_id"], t["thread_ts"], t["following"], t["has_unreads"], t["mentions_me"]) == (
        "C000000001", THREAD_TS, True, True, True)
    assert t["root"]["user_name"] == "Alice"
    assert inbox.replies("C000000001", THREAD_TS)["last_read"] == f"{NOW - 100:.6f}"


def test_channel_threads_merge_history_and_followed(inbox):
    threads = inbox.channel_threads("C000000001")["threads"]
    assert [(t["thread_ts"], t["following"]) for t in threads] == [
        (f"{NOW:.6f}", False),   # 历史里有回复的根消息
        (THREAD_TS, True),       # 我参与的
    ]
    assert threads[0]["has_unreads"] is False  # 没参与的 thread Slack 不记已读


def test_mark_read_is_local_only_and_moves_forward(inbox):
    # 频道：Slack 记的已读在 3 天前，有未读
    assert inbox.mark_conversation("C000000001", f"{NOW - 4 * DAY:.6f}")["marked"] is True  # 本地第一次记
    assert inbox.mark_conversation("C000000001", f"{NOW - 5 * DAY:.6f}")["marked"] is False  # 不往回退
    social = next(c for c in inbox.conversations() if c["id"] == "C000000001")
    assert social["has_unreads"] is True and social["last_read"] == f"{NOW - 3 * DAY:.6f}"  # Slack 的更新，用 Slack 的
    assert inbox.mark_conversation("C000000001", f"{NOW:.6f}")["marked"] is True
    inbox._cache.pop("counts")
    social = next(c for c in inbox.conversations() if c["id"] == "C000000001")
    assert social["has_unreads"] is False and social["last_read"] == f"{NOW:.6f}"

    # thread：本地看过最新回复后不再算未读，也不再 @我
    assert inbox.thread_badge() == {"has_unreads": True, "mention_count": 1}
    assert inbox.mark_thread("C000000001", THREAD_TS, f"{NOW - 10:.6f}")["marked"] is True
    assert inbox.thread_badge() == {"has_unreads": False, "mention_count": 0}
    assert inbox.threads()["threads"][0]["has_unreads"] is False
    assert inbox.replies("C000000001", THREAD_TS)["last_read"] == f"{NOW - 10:.6f}"
    # 没参与的 thread 也能在本地记
    assert inbox.mark_thread("C000000001", f"{NOW:.6f}", f"{NOW:.6f}")["marked"] is True

    # 全程没有任何写 Slack 的调用
    assert all(method in ALLOWED_METHODS for method, _ in inbox.fake.calls)
    assert not any(method.endswith(".mark") for method, _ in inbox.fake.calls)
    with pytest.raises(SlackInboxError) as exc:
        inbox.mark_conversation("D000000005", f"{NOW:.6f}")  # bot 私信不在展示范围
    assert exc.value.code == "CONVERSATION_NOT_VISIBLE"
    with pytest.raises(SlackInboxError):
        inbox.mark_conversation("C000000001", "1; drop")


def test_client_only_uses_get():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    client = SlackReadOnlyClient(normalize_credentials("xoxc-a", "xoxd-b"), http=httpx.Client(transport=httpx.MockTransport(handler)))
    client.call("auth.test")
    client.call("conversations.history", channel="C000000001")
    assert [r.method for r in seen] == ["GET", "GET"]


def test_messages_resolve_names_files_and_permalink(inbox):
    page = inbox.messages("C000000001")
    msg = page["messages"][0]
    assert msg["user_name"] == "Alice"
    assert (msg["is_me"], msg["mentions_me"]) == (False, False)
    assert msg["text"] == "@用户组 Racks & floors @Bob B"
    assert [f["id"] for f in msg["files"]] == ["F000000001", "F000000002"]
    assert msg["permalink"] == f"https://team.slack.com/archives/C000000001/p{f'{NOW:.6f}'.replace('.', '')}"
    assert page["next_cursor"] is None


def test_invisible_conversation_is_rejected(inbox):
    for cid in ["D000000005", "C999999999"]:
        with pytest.raises(SlackInboxError) as exc:
            inbox.messages(cid)
        assert exc.value.code == "CONVERSATION_NOT_VISIBLE"
    with pytest.raises(SlackInboxError):
        inbox.messages("../etc")


def test_export_includes_thread_replies(inbox):
    data = inbox.export("C000000001")
    assert data["messages"][0]["replies"][0]["text"] == "*1/* draft (1/1)"
    md = export_to_markdown(data)
    assert "# Slack · #social" in md and "> *1/* draft (1/1)" in md


def test_missing_credentials(tmp_path):
    box = SlackInbox(SlackCredentialStore(tmp_path / "none.json"), cache_dir=tmp_path, client_factory=FakeClient)
    assert box.status()["error_code"] == "CREDENTIALS_MISSING"
    with pytest.raises(SlackInboxError) as exc:
        box.conversations()
    assert exc.value.code == "CREDENTIALS_MISSING"


def test_file_route_only_inlines_safe_images(inbox, monkeypatch):
    monkeypatch.setattr(slack_inbox_router, "get_slack_inbox", lambda: inbox)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(slack_inbox_router.router, prefix="/api")
    with TestClient(app) as client:
        assert client.get("/api/slack-inbox/files/F000000001").status_code == 404  # 还没见过这个文件
        assert client.get("/api/slack-inbox/conversations/C000000001/messages").status_code == 200
        png = client.get("/api/slack-inbox/files/F000000001")
        assert png.status_code == 200 and png.headers["content-type"] == "image/png"
        assert png.headers["content-disposition"].startswith("inline")
        svg = client.get("/api/slack-inbox/files/F000000002")
        assert svg.headers["content-type"] == "application/octet-stream"
        assert svg.headers["content-disposition"].startswith("attachment")
        assert svg.headers["x-content-type-options"] == "nosniff"
        assert client.get("/api/slack-inbox/files/F000000003").status_code == 404
        assert client.get("/api/slack-inbox/conversations/D000000005/messages").status_code == 404
        listing = client.get("/api/slack-inbox/conversations").json()
        assert listing["threads"] == {"has_unreads": True, "mention_count": 1}
        assert len(client.get("/api/slack-inbox/threads").json()["threads"]) == 1
        assert client.get("/api/slack-inbox/conversations/C000000001/threads").status_code == 200
        mark = client.post("/api/slack-inbox/conversations/C000000001/mark", json={"ts": f"{NOW:.6f}"})
        assert mark.status_code == 200 and mark.json()["marked"] is True
        assert client.post(f"/api/slack-inbox/conversations/C000000001/threads/{THREAD_TS}/mark",
                           json={"ts": f"{NOW:.6f}"}).json()["marked"] is True
        status = client.get("/api/slack-inbox/status").json()
        assert status["ok"] is True and "token" not in status


def test_mpim_label_drops_me():
    assert mpim_label("Group messaging with: @michelle @linrui @felix", "felix") == "michelle, linrui"
    assert mpim_label("mpdm-a--b--felix-1", "felix") == "a, b"
    assert mpim_label("custom name", "felix") == "custom name"


def test_agent_context_for_thread_and_dm(inbox):
    ctx = inbox.agent_context("C000000001", THREAD_TS)
    assert ctx["source"] == f"slack:C000000001:{THREAD_TS}" and ctx["kind"] == "thread"
    assert ctx["title"] == "root"
    assert ctx["history"] == [{"role": "them", "content": "root"}, {"role": "them", "content": "*1/* draft (1/1)"}]
    md = ctx["markdown"]
    assert "# Slack thread · #social" in md and "第一条是 thread 根消息" in md
    assert "## 2. Bob B" in md and "原文链接：https://team.slack.com/archives/C000000001/" in md

    dm = inbox.agent_context("C000000001")
    assert dm["source"] == "slack:C000000001" and dm["kind"] == "channel"
    assert "[图片] a.png" in dm["markdown"]
    with pytest.raises(SlackInboxError):
        inbox.agent_context("C000000001", "bad")
    with pytest.raises(SlackInboxError) as exc:
        inbox.agent_context("D000000005")
    assert exc.value.code == "CONVERSATION_NOT_VISIBLE"


def test_agent_context_marks_my_messages():
    conv = {"kind": "im", "name": "Alice"}
    msg = {"user_name": "me", "is_me": True, "time": "t", "edited": False, "permalink": "p", "text": "hi",
           "attachments": [{"service_name": "X", "title": "Post", "title_link": "https://x.com/a", "text": "line1\nline2"}],
           "files": []}
    md = agent_context_markdown(conv, [msg], "me", is_thread=False)
    assert "# Slack 会话 · 私信 · Alice" in md and "## 1. me（我）" in md
    assert "[链接卡片 · X] Post https://x.com/a" in md and "> line2" in md


def test_link_card_text_is_parsed_like_message_text(inbox):
    msg = inbox.normalize_message("C000000001", {
        "ts": f"{NOW:.6f}", "user": "UAAAAAAAA1", "text": "",
        "attachments": [{"service_name": "X", "title": "Post", "text": "via <https://x.com/a|the post> by <@UAAAAAAAA1> &amp; co"}],
    })
    card = msg["attachments"][0]
    assert "<" not in card["text"] and "the post (https://x.com/a)" in card["text"] and "& co" in card["text"]
    assert {"type": "link", "url": "https://x.com/a", "text": "the post"} in card["segments"]
    assert any(seg["type"] == "mention" for seg in card["segments"])



def test_search_marks_visibility_and_threads(inbox):
    out = inbox.search("HBM yields")
    assert out["total"] == 2
    first, second = out["results"]
    assert (first["channel_id"], first["visible"], first["thread_ts"], first["channel_name"]) == (
        "C000000001", True, THREAD_TS, "social")
    assert first["message"]["user_name"] == "Bob B" and first["message"]["permalink"].endswith("cid=C000000001")
    assert (second["visible"], second["channel_name"], second["thread_ts"]) == (False, "secret-other", None)
    with pytest.raises(SlackInboxError):
        inbox.search("  ")


def test_unread_material_collects_others_messages_after_last_read(inbox):
    sections = inbox.unread_material()
    kinds = [(s["kind"], s["conversation"]["id"], s["thread_ts"]) for s in sections]
    # 频道有未读（last_read 3 天前，最新消息在 NOW）；我参与的 thread 有新回复
    assert ("channel", "C000000001", None) in kinds
    thread = next(s for s in sections if s["kind"] == "thread")
    assert thread["thread_ts"] == THREAD_TS and thread["messages"]
    assert all(float(m["ts"]) > float(thread["last_read"]) and not m["is_me"] for m in thread["messages"])
    # 只读：没调任何标记已读
    assert all(method in ALLOWED_METHODS for method, _ in inbox.fake.calls)


def test_digest_and_search_routes(inbox, monkeypatch):
    class FakeAI:
        async def digest(self, key, where, messages):
            if "thread" in where:
                raise RuntimeError("model down")
            return {"summary": f"{where} 有 {len(messages)} 条", "items": [], "todo_for_me": ""}

        async def search_query(self, q):
            return "HBM yields"

    monkeypatch.setattr(slack_inbox_router, "get_slack_inbox", lambda: inbox)
    monkeypatch.setattr(slack_inbox_router, "get_slack_ai", lambda: FakeAI())
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(slack_inbox_router.router, prefix="/api")
    with TestClient(app) as client:
        sections = client.get("/api/slack-inbox/digest").json()["sections"]
        channel = next(s for s in sections if s["kind"] == "channel")
        assert channel["summary"].startswith("#social") and channel["unread_count"] >= 1
        thread = next(s for s in sections if s["kind"] == "thread")
        assert "error" in thread and thread["thread_ts"] == THREAD_TS
        # @我 / 有待办的排前面，其余按最新消息倒序
        order = [(not (x["mentions_me"] or x.get("todo_for_me")), -float(x["latest_ts"])) for x in sections]
        assert order == sorted(order)
        found = client.get("/api/slack-inbox/search", params={"q": "HBM 良率"}).json()
        assert found["input"] == "HBM 良率" and found["query"] == "HBM yields" and len(found["results"]) == 2
        assert client.get("/api/slack-inbox/search").status_code == 422



def test_usergroup_mention_in_search_format():
    assert parse_slack_text("<@S096243SP9T> hi", lambda uid: "WRONG") == [
        {"type": "mention", "text": "@用户组"}, {"type": "text", "text": " hi"}]
