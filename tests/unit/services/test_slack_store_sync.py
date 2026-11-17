"""本地副本：只拉新的、往前补、定期补编辑和删除、thread 增量、图片预取和清理。"""

import pytest

from src.services.slack_inbox import (
    ALLOWED_METHODS,
    MARK_METHODS,
    REFRESH_EVERY_S,
    THREAD_FETCH_TTL_S,
    THREAD_FULL_EVERY_S,
    SlackCredentialStore,
    SlackInbox,
)
from src.services.slack_store import SlackStore

ME = "UME0000001"
CID = "C000000001"
T0 = 1_800_000_000.0


def ts(n: float) -> str:
    return f"{T0 + n:.6f}"


class Clock:
    def __init__(self):
        self.t = T0 + 1000

    def __call__(self):
        return self.t


class FakeSlack:
    """像 Slack 一样处理 oldest / latest（都不含边界）和 limit；history 新→旧。"""

    def __init__(self):
        self.history = []  # 新→旧
        self.threads = {}  # thread_ts -> [root, replies...] 旧→新
        self.calls = []
        self.downloads = []
        self.latest = None

    def add(self, n, text="hi", **extra):
        msg = {"ts": ts(n), "user": "UAAAAAAAA1", "text": text, **extra}
        self.history.insert(0, msg)
        self.history.sort(key=lambda m: -float(m["ts"]))
        return msg

    def call(self, method, **params):
        assert method in ALLOWED_METHODS or method in MARK_METHODS
        self.calls.append((method, params))
        if method == "auth.test":
            return {"ok": True, "user": "me", "user_id": ME, "team": "T", "url": "https://team.slack.com"}
        if method == "client.counts":
            latest = self.history[0]["ts"] if self.history else None
            return {"ok": True, "channels": [{"id": CID, "latest": latest, "has_unreads": False, "last_read": latest}]}
        if method == "client.userBoot":
            return {"ok": True, "channels": [{"id": CID, "is_channel": True, "name": "social"}], "ims": []}
        if method == "conversations.info":
            return {"ok": True, "channel": {"id": CID, "name": "social"}}
        if method == "users.info":
            return {"ok": True, "user": {"name": "alice", "profile": {"display_name": "Alice"}}}
        if method == "subscriptions.thread.getView":
            return {"ok": True, "threads": []}
        if method == "conversations.history":
            msgs = self.history
            if "oldest" in params:
                msgs = [m for m in msgs if float(m["ts"]) > float(params["oldest"])]
            if "latest" in params:
                msgs = [m for m in msgs if float(m["ts"]) < float(params["latest"])]
            limit = int(params.get("limit", 100))
            return {"ok": True, "messages": msgs[:limit], "has_more": len(msgs) > limit}
        if method == "conversations.replies":
            msgs = self.threads.get(params["ts"], [])
            if "oldest" in params:
                msgs = [msgs[0]] + [m for m in msgs[1:] if float(m["ts"]) > float(params["oldest"])]
            return {"ok": True, "messages": msgs, "has_more": False}
        raise AssertionError(method)

    def download(self, url):
        self.downloads.append(url)
        return b"PNG", "image/png"

    def history_calls(self):
        return [p for m, p in self.calls if m == "conversations.history"]


@pytest.fixture
def env(tmp_path):
    creds = SlackCredentialStore(tmp_path / "creds.json")
    creds.save("xoxc-abc", "xoxd-def")
    slack = FakeSlack()
    clock = Clock()
    inbox = SlackInbox(creds, cache_dir=tmp_path / "cache", client_factory=lambda c: slack, now=clock)
    return inbox, slack, clock


def advance(inbox, clock, seconds):
    clock.t += seconds
    inbox._cache.clear()  # 模拟 TTL 过期（_TTLCache 用的是真实单调时钟）


def test_first_open_fetches_one_page_then_only_new(env):
    inbox, slack, clock = env
    for n in range(150):
        slack.add(n)
    page = inbox.messages(CID, limit=50)
    assert len(page["messages"]) == 50 and page["messages"][0]["ts"] == ts(149)
    assert len(slack.history_calls()) == 1 and slack.history_calls()[0]["limit"] == 100

    # 没有新消息：counts 的最新 ts 本地已经有了，一次 history 都不调
    advance(inbox, clock, 20)
    inbox.messages(CID, limit=50)
    assert len(slack.history_calls()) == 1

    # 来了两条新的：只用 oldest=本地最新 去要
    slack.add(150, "new 1")
    slack.add(151, "new 2")
    advance(inbox, clock, 20)
    page = inbox.messages(CID, limit=50)
    assert [m["text"] for m in page["messages"][:2]] == ["new 2", "new 1"]
    assert slack.history_calls()[-1]["oldest"] == ts(149)


def test_paging_reads_local_then_backfills_from_slack(env):
    inbox, slack, _ = env
    for n in range(150):
        slack.add(n)
    first = inbox.messages(CID, limit=50)
    second = inbox.messages(CID, limit=50, cursor=first["next_cursor"])
    assert second["messages"][0]["ts"] == ts(99) and len(slack.history_calls()) == 1  # 本地就有
    third = inbox.messages(CID, limit=50, cursor=second["next_cursor"])
    assert third["messages"][0]["ts"] == ts(49) and len(third["messages"]) == 50
    assert slack.history_calls()[-1]["latest"] == ts(50)  # 本地最早那条再往前补
    assert third["next_cursor"] is None  # 拉全了
    assert len(slack.history_calls()) == 2
    # 再翻一遍全部走本地
    inbox.messages(CID, limit=50, cursor=second["next_cursor"])
    assert len(slack.history_calls()) == 2


def test_periodic_refresh_picks_up_edits_reply_counts_and_deletions(env):
    inbox, slack, clock = env
    for n in range(5):
        slack.add(n)
    inbox.messages(CID)
    slack.history[0]["text"] = "edited"
    slack.history[1]["reply_count"] = 3
    slack.history[1]["thread_ts"] = slack.history[1]["ts"]
    deleted = slack.history.pop(2)
    advance(inbox, clock, REFRESH_EVERY_S + 1)
    msgs = {m["ts"]: m for m in inbox.messages(CID)["messages"]}
    assert msgs[ts(4)]["text"] == "edited"
    assert msgs[ts(3)]["reply_count"] == 3
    assert deleted["ts"] not in msgs


def test_threads_fetch_incrementally_and_update_root(env):
    inbox, slack, clock = env
    root = slack.add(0, "root", thread_ts=ts(0), reply_count=1, latest_reply=ts(1))
    slack.threads[ts(0)] = [root, {"ts": ts(1), "thread_ts": ts(0), "user": "UAAAAAAAA1", "text": "r1"}]
    assert [m["text"] for m in inbox.replies(CID, ts(0))["messages"]] == ["root", "r1"]

    new_root = {**root, "reply_count": 2, "latest_reply": ts(2)}
    slack.history[0] = new_root  # Slack 两边返回的根消息是同一份
    slack.threads[ts(0)] = [new_root, slack.threads[ts(0)][1], {"ts": ts(2), "thread_ts": ts(0), "user": "UAAAAAAAA1", "text": "r2"}]
    advance(inbox, clock, THREAD_FETCH_TTL_S + 1)
    assert [m["text"] for m in inbox.replies(CID, ts(0))["messages"]] == ["root", "r1", "r2"]
    last = [p for m, p in slack.calls if m == "conversations.replies"][-1]
    assert last["oldest"] == ts(1)
    # 根消息的回复数顺便更新到频道消息流里
    assert inbox.messages(CID)["messages"][0]["reply_count"] == 2

    # 30 秒内再看不打 Slack；10 分钟后整个重拉并去掉删掉的回复
    n = len(slack.calls)
    inbox.replies(CID, ts(0))
    assert len(slack.calls) == n
    slack.threads[ts(0)] = [new_root, slack.threads[ts(0)][2]]
    advance(inbox, clock, THREAD_FULL_EVERY_S + 1)
    assert [m["text"] for m in inbox.replies(CID, ts(0))["messages"]] == ["root", "r2"]


def test_images_are_prefetched_and_pruned(env, tmp_path):
    inbox, slack, _ = env
    slack.add(0, "pic", files=[
        {"id": "F000000001", "mimetype": "image/png", "name": "a.png", "size": 10, "url_private": "https://files.slack.com/a.png"},
        {"id": "F000000002", "mimetype": "application/pdf", "name": "b.pdf", "url_private": "https://files.slack.com/b.pdf"},
        {"id": "F000000003", "mimetype": "image/png", "name": "c.png", "size": 10, "url_private": "https://evil.example.com/c.png"},
    ])
    inbox.messages(CID)
    inbox._prefetch_thread.join(timeout=5)
    assert slack.downloads == ["https://files.slack.com/a.png"]  # 只预取 slack.com 上的图片
    assert (inbox.cache_dir / "files" / "F000000001").is_file()
    # 超过上限删最旧的
    assert inbox.prune_files(max_bytes=1) == 1
    assert not (inbox.cache_dir / "files" / "F000000001").exists()
    assert inbox.prune_files(max_bytes=10**9) == 0


def test_sync_all_only_asks_for_new_messages(env):
    inbox, slack, clock = env
    for n in range(3):
        slack.add(n)
    assert inbox.sync_all()["new"] == 3
    advance(inbox, clock, 20)
    assert inbox.sync_all()["new"] == 0
    assert len(slack.history_calls()) == 1
    slack.add(3)
    advance(inbox, clock, 20)
    assert inbox.sync_all()["new"] == 1


def test_store_survives_restart(tmp_path):
    db = SlackStore(tmp_path / "s.db")
    db.upsert(CID, [{"ts": ts(1), "text": "a"}, {"ts": ts(2), "text": "b", "thread_ts": ts(2)}], in_history=True)
    db.upsert(CID, [{"ts": ts(3), "text": "r", "thread_ts": ts(2)}], in_history=False)
    db.set_conv_state(CID, newest_ts=ts(2), oldest_ts=ts(1), complete=True)
    db.close()
    db = SlackStore(tmp_path / "s.db")
    assert [m["text"] for m in db.history(CID)] == ["b", "a"]  # 回复不进主消息流
    assert [m["text"] for m in db.thread(CID, ts(2))] == ["b", "r"]
    assert db.conv_state(CID)["complete"] is True
    # thread 里拉到的根消息不会把它从主消息流里拿掉
    db.upsert(CID, [{"ts": ts(2), "text": "b2", "thread_ts": ts(2)}], in_history=False)
    assert [m["text"] for m in db.history(CID)] == ["b2", "a"]
    assert db.stats()["messages"] == 3
