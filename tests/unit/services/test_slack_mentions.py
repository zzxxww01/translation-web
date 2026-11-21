"""Muse 自动化：从本地副本查 since 之后谁 @ 了我，分 direct / group / channel；全程只读。"""

import pytest

from src.services.slack_inbox import ALLOWED_METHODS, SlackCredentialStore, SlackInbox, mention_type

ME = "U0A8T7U5D7A"
CID = "C000000001"
DM = "D000000001"
T0 = 1_800_000_000.0


def ts(n: float) -> str:
    return f"{T0 + n:.6f}"


class FakeSlack:
    def __init__(self):
        self.calls = []
        self.search_matches = []  # search.messages 的结果，新→旧
        self.search_error = None

    def call(self, method, **params):
        assert method in ALLOWED_METHODS
        self.calls.append(method)
        if method == "auth.test":
            return {"ok": True, "user": "felix", "user_id": ME, "team": "T", "url": "https://team.slack.com"}
        if method == "conversations.info":
            if params["channel"] == DM:
                return {"ok": True, "channel": {"id": DM, "is_im": True, "user": "UAAAAAAAA1"}}
            return {"ok": True, "channel": {"id": CID, "name": "general"}}
        if method == "users.info":
            return {"ok": True, "user": {"name": "alice", "profile": {"display_name": "Alice"}}}
        if method == "client.userBoot":  # 没有 subteams：只靠手配的用户组
            return {"ok": True, "channels": [{"id": CID, "name": "general", "is_channel": True}],
                    "ims": [{"id": DM, "is_im": True, "user": "UAAAAAAAA1", "is_open": True}]}
        if method == "client.counts":
            return {"ok": True, "channels": [{"id": CID, "latest": ts(50)}], "ims": [{"id": DM, "latest": ts(50)}]}
        if method == "subscriptions.thread.getView":
            return {"ok": True, "threads": []}
        if method == "search.messages":
            self.searches = getattr(self, "searches", []) + [params]
            if self.search_error:
                raise self.search_error
            return {"ok": True, "messages": {"matches": self.search_matches, "paging": {"pages": 1}}}
        raise AssertionError(method)


@pytest.fixture
def inbox(tmp_path):
    creds = SlackCredentialStore(tmp_path / "creds.json")
    creds.save("xoxc-abc", "xoxd-def")
    slack = FakeSlack()
    inbox = SlackInbox(creds, cache_dir=tmp_path / "cache", client_factory=lambda c: slack)
    inbox._fake = slack
    return inbox


def test_mention_type_priority():
    assert mention_type(f"hi <@{ME}> and <!here>", ME, ["S1"]) == "direct"
    assert mention_type("ping <!subteam^S1|@infra> <!channel>", ME, ["S1"]) == "group"
    assert mention_type("ping <!subteam^S2|@other>", ME, ["S1"]) is None
    assert mention_type("<!here> standup", ME) == "channel"
    assert mention_type("<!everyone>", ME) == "channel"
    assert mention_type("<@UOTHER0001> hello", ME) is None


def test_mentions_since_filters_classifies_and_stays_read_only(inbox):
    inbox.db.upsert(CID, [
        {"ts": ts(1), "user": "UAAAAAAAA1", "text": f"old <@{ME}>"},
        {"ts": ts(10), "user": "UAAAAAAAA1", "text": f"<@{ME}> can you look?"},
        {"ts": ts(11), "user": "UAAAAAAAA1", "text": "<!here> lunch"},
        {"ts": ts(12), "user": ME, "text": "<!channel> my own broadcast"},
        {"ts": ts(13), "user": "UAAAAAAAA1", "text": "no mention",
         "attachments": [{"text": f"<@{ME}> only in a card"}]},
        {"ts": ts(14), "user": "UAAAAAAAA1", "text": "<!subteam^S0GROUP1|@infra> deploy"},
        {"ts": ts(15), "user": "UAAAAAAAA1", "text": f"reply <@{ME}>", "thread_ts": ts(10)},
    ], in_history=True)
    inbox.db.upsert(DM, [
        {"ts": ts(16), "user": "UAAAAAAAA1", "text": f"<@{ME}> dm"},
        {"ts": ts(17), "user": "UAAAAAAAA1", "text": "can you check this article?"},  # 私信里没 @ 也要报
        {"ts": ts(18), "user": ME, "text": "sure <!here>"},                           # 我自己发的不算
        {"ts": ts(19), "user": "UAAAAAAAA1", "subtype": "channel_join", "text": "joined"},
        {"ts": ts(21), "user": "UAAAAAAAA1", "text": "thread reply in dm", "thread_ts": ts(17)},
    ], in_history=True)
    inbox.db.mark_deleted(CID, [ts(11)])

    got = inbox.mentions_since(T0 + 5, group_ids=["S0GROUP1"])
    assert [(m["message_ts"], m["mention_type"]) for m in got] == [
        (ts(10), "direct"), (ts(14), "group"), (ts(15), "direct"),
        (ts(16), "dm"), (ts(17), "dm"), (ts(21), "dm"),
    ]
    first = got[0]
    assert first["conversation_name"] == "general"
    assert first["from_user"] == "Alice"
    assert first["text"] == "@Alice can you look?"
    assert first["time"].endswith("Z") and first["thread_ts"] is None
    assert got[2]["thread_ts"] == ts(10)
    assert got[3]["conversation_name"] == "Alice"
    assert got[5]["thread_ts"] == ts(17)

    # 没配用户组时 group 消息不返回
    assert [m["message_ts"] for m in inbox.mentions_since(T0 + 13)] == [ts(15), ts(16), ts(17), ts(21)]
    # 水位线之后没有新消息
    assert inbox.mentions_since(T0 + 21) == []
    # 只读：没改 Slack 已读，也没动 momo 本地已读
    assert not any("mark" in method for method in inbox._fake.calls)
    assert inbox.db.read_positions() == {}


def test_my_subteams_from_user_boot():
    from src.services.slack_inbox import _my_subteams
    assert _my_subteams({"subteams": {"self": ["S0GROUP1", {"id": "S0GROUP2"}, "bad", None], "all": ["S0OTHER1"]}}) \
        == ["S0GROUP1", "S0GROUP2"]
    assert _my_subteams({}) == []
    assert _my_subteams({"subteams": []}) == []


def test_auto_detected_groups_count_as_group_mentions(inbox, monkeypatch):
    monkeypatch.setattr(inbox, "my_groups", lambda: ["S0GROUP1"])
    inbox.db.upsert(CID, [{"ts": ts(20), "user": "UAAAAAAAA1", "text": "<!subteam^S0GROUP1|@infra> deploy"}],
                    in_history=True)
    assert [m["mention_type"] for m in inbox.mentions_since(T0 + 19)] == ["group"]


def test_translation_source_single_message_and_thread(inbox, monkeypatch):
    monkeypatch.setattr(inbox, "sync_thread", lambda *a, **k: None)
    monkeypatch.setattr(inbox, "sync_conversation", lambda *a, **k: 0)
    monkeypatch.setattr(inbox, "_latest_hint", lambda cid: None)
    inbox.db.upsert(CID, [
        {"ts": ts(30), "user": "UAAAAAAAA1", "text": "plz RT <@U0A8T7U5D7A>", "thread_ts": ts(30),
         "attachments": [{"service_name": "X (formerly Twitter)", "title": "vLLM",
                          "text": "We shipped 1.0 &lt;3 by <slack://user?team=T1&id=U2|Reyk>"}]},
    ], in_history=True)
    inbox.db.upsert(CID, [{"ts": ts(31), "user": "UAAAAAAAA1", "text": "will post", "thread_ts": ts(30)}],
                    in_history=False)

    one = inbox.translation_source(CID, ts(30))
    assert one["source_text"] == "plz RT @Alice\n\n[X (formerly Twitter)] vLLM\nWe shipped 1.0 <3 by Reyk"
    assert one["messages"] == 1

    whole = inbox.translation_source(CID, ts(31), with_thread=True)
    assert whole["messages"] == 2
    assert whole["source_text"].startswith("Alice: plz RT") and whole["source_text"].endswith("Alice: will post")
    assert f"p{ts(30).replace('.', '')}" in whole["permalink"]

    from src.services.slack_inbox import SlackInboxError
    with pytest.raises(SlackInboxError) as exc:
        inbox.translation_source(CID, ts(99))
    assert exc.value.status_code == 404
    with pytest.raises(SlackInboxError):
        inbox.translation_source("bad", ts(30))
    assert not any("mark" in method for method in inbox._fake.calls)


def _match(n, text, thread=None, channel=CID, user="UAAAAAAAA1"):
    link = f"https://team.slack.com/archives/{channel}/p{ts(n).replace('.', '')}"
    if thread is not None:
        link += f"?thread_ts={ts(thread)}&cid={channel}"
    return {"ts": ts(n), "user": user, "text": text, "channel": {"id": channel, "name": "general"},
            "permalink": link, "iid": "x", "team": "T"}


def test_search_fills_mentions_from_threads_not_synced_locally(inbox):
    # 我没参与的 thread 里的 @我：本地副本没有，靠搜索补上
    inbox._fake.search_matches = [
        _match(42, f"Thanks <@{ME}>", thread=40),
        _match(41, f"<@{ME}> local one"),          # 本地已经有了：不从搜索重复返回
        _match(-5000, f"<@{ME}> too old"),         # 早于 since - 回看窗口
        _match(43, f"<@{ME}> by me", user=ME),     # 自己发的
    ]
    inbox.db.upsert(CID, [{"ts": ts(41), "user": "UAAAAAAAA1", "text": f"<@{ME}> local one"}], in_history=True)

    got = inbox.mentions_since(T0 + 30)
    assert [(m["message_ts"], m["mention_type"], m["thread_ts"]) for m in got] == [
        (ts(41), "direct", None), (ts(42), "direct", ts(40)),
    ]
    query = inbox._fake.searches[-1]["query"]
    assert query.startswith(f"<@{ME}> after:")
    # 搜到的存进了本地副本（translate-slack 能直接找到），下次不再从搜索重复报
    assert inbox.db.message(CID, ts(42))["thread_ts"] == ts(40)
    assert inbox.mentions_since(T0 + 42) == []


def test_search_catches_late_indexed_mentions_once(inbox):
    # 上次查询时搜索还没索引到的消息（ts 早于这次的 since，但在回看窗口里）：补报一次
    inbox._fake.search_matches = [_match(100, f"<@{ME}> late", thread=90)]
    got = inbox.mentions_since(T0 + 200)
    assert [m["message_ts"] for m in got] == [ts(100)]
    assert inbox.mentions_since(T0 + 200) == []


def test_search_failure_falls_back_to_local(inbox):
    from src.services.slack_inbox import SlackInboxError
    inbox._fake.search_error = SlackInboxError("RATE_LIMITED", "too many", 429)
    inbox.db.upsert(CID, [{"ts": ts(60), "user": "UAAAAAAAA1", "text": f"<@{ME}> hi"}], in_history=True)
    assert [m["message_ts"] for m in inbox.mentions_since(T0 + 50)] == [ts(60)]


def test_activity_lists_threads_and_dms_by_latest_activity(inbox, monkeypatch):
    monkeypatch.setattr(inbox, "sync_conversation", lambda *a, **k: 0)
    inbox.db.upsert(CID, [
        {"ts": ts(100), "user": "UAAAAAAAA1", "text": "Elon post", "thread_ts": ts(100),
         "reply_count": 2, "latest_reply": ts(102)},
        {"ts": ts(40), "user": "UAAAAAAAA1", "text": "no replies here"},  # 没人回复的新帖也列出（2026-11-21）
    ], in_history=True)
    inbox.db.upsert(CID, [
        {"ts": ts(101), "user": "UBBBBBBBB2", "text": f"<@{ME}> pls check", "thread_ts": ts(100)},
        {"ts": ts(102), "user": "UCCCCCCCC3", "text": "ok will post", "thread_ts": ts(100)},
    ], in_history=False)
    inbox.db.upsert(DM, [{"ts": ts(50), "user": "UAAAAAAAA1", "text": "hey Felix"}], in_history=True)

    items = inbox.activity()["items"]
    assert [(i["type"], i["channel_id"], i.get("reply_count")) for i in items] == [
        ("thread", CID, 2), ("dm", DM, None), ("thread", CID, 0)]
    thread, dm, post = items
    assert post["thread_ts"] == ts(40) and post["root"]["text"] == "no replies here" and post["last"] is None
    assert thread["thread_ts"] == ts(100) and thread["reply_count"] == 2
    assert thread["root"]["text"] == "Elon post"
    assert thread["last"]["text"] == "ok will post"
    assert thread["participants"] == ["Alice"]  # 假 Slack 里所有人都叫 Alice，去重后一个
    assert thread["mentions_me"] is True and thread["channel_name"] == "general"
    assert dm["last"]["text"] == "hey Felix" and dm["channel_name"] == "Alice" and dm["thread_ts"] is None
    assert not any("mark" in method for method in inbox._fake.calls)


def test_mark_all_read_clears_activity_locally(inbox, monkeypatch):
    monkeypatch.setattr(inbox, "sync_conversation", lambda *a, **k: 0)
    inbox.db.upsert(CID, [{"ts": ts(40), "user": "UAAAAAAAA1", "text": "new post"}], in_history=True)
    inbox.db.upsert(DM, [{"ts": ts(50), "user": "UAAAAAAAA1", "text": "hey Felix"}], in_history=True)
    assert any(i["has_unreads"] for i in inbox.activity()["items"])
    assert inbox.mark_all_read()["marked"] >= 1
    assert not any(i["has_unreads"] for i in inbox.activity()["items"])
    assert not any("mark" in method for method in inbox._fake.calls)  # 不碰 Slack 的已读


def test_activity_marks_my_threads_and_marks_chosen_items_only(inbox, monkeypatch):
    from src.services.slack_inbox import SlackInboxError
    monkeypatch.setattr(inbox, "sync_conversation", lambda *a, **k: 0)
    inbox.db.upsert(CID, [
        {"ts": ts(40), "user": "UAAAAAAAA1", "text": "post a"},
        {"ts": ts(41), "user": "UAAAAAAAA1", "text": "post b"},
    ], in_history=True)
    items = {i["thread_ts"]: i for i in inbox.activity()["items"] if i["type"] == "thread"}
    assert items[ts(40)]["following"] is False  # 别人的新帖
    assert items[ts(40)]["has_unreads"] and items[ts(41)]["has_unreads"]

    inbox.mark_items_read([{"channel_id": CID, "ts": ts(40), "thread_ts": ts(40)}])
    items = {i["thread_ts"]: i for i in inbox.activity()["items"] if i["type"] == "thread"}
    assert items[ts(40)]["has_unreads"] is False and items[ts(41)]["has_unreads"] is True
    with pytest.raises(SlackInboxError):
        inbox.mark_items_read([{"channel_id": "C999999999", "ts": ts(40)}])
    assert not any("mark" in method for method in inbox._fake.calls)
