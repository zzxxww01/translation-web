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
    MARK_METHODS,
    SlackCredentialStore,
    SlackInbox,
    SlackInboxError,
    SlackReadOnlyClient,
    export_to_markdown,
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
        assert method in ALLOWED_METHODS or method in MARK_METHODS
        self.calls.append((method, params))
        if method == "client.userBoot":
            return _boot()
        if method == "subscriptions.thread.getView":
            return _thread_view()
        if method in MARK_METHODS:
            return {"ok": True}
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
        assert verb in {"test", "counts", "userBoot", "info", "history", "replies", "getView"}, method
    # 唯一的写操作：推进我自己的已读位置
    assert MARK_METHODS == {"conversations.mark", "subscriptions.thread.mark"}


@pytest.mark.parametrize("method", ["chat.postMessage", "chat.update", "chat.delete", "reactions.add", "files.upload",
                                    "conversations.join", "subscriptions.thread.add"])
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
    assert parse_slack_text("<javascript:alert(1)|x>", str) == [{"type": "text", "text": "<javascript:alert(1)|x>"}]


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


def test_mark_read_only_moves_forward(inbox):
    assert inbox.mark_conversation("C000000001", f"{NOW - 4 * DAY:.6f}")["marked"] is False
    assert inbox.mark_conversation("C000000001", f"{NOW:.6f}")["marked"] is True
    assert ("conversations.mark", {"channel": "C000000001", "ts": f"{NOW:.6f}"}) in inbox.fake.calls
    assert inbox.mark_thread("C000000001", THREAD_TS, f"{NOW - 200:.6f}")["marked"] is False
    assert inbox.mark_thread("C000000001", THREAD_TS, f"{NOW - 10:.6f}")["marked"] is True
    assert inbox.mark_thread("C000000001", f"{NOW:.6f}", f"{NOW:.6f}")["marked"] is False  # 没参与
    with pytest.raises(SlackInboxError) as exc:
        inbox.mark_conversation("D000000005", f"{NOW:.6f}")  # bot 私信不在展示范围
    assert exc.value.code == "CONVERSATION_NOT_VISIBLE"
    with pytest.raises(SlackInboxError):
        inbox.mark_conversation("C000000001", "1; drop")


def test_client_posts_mark_methods():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    client = SlackReadOnlyClient(normalize_credentials("xoxc-a", "xoxd-b"), http=httpx.Client(transport=httpx.MockTransport(handler)))
    client.call("conversations.mark", channel="C000000001", ts="1.2")
    client.call("auth.test")
    assert [r.method for r in seen] == ["POST", "GET"]


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
