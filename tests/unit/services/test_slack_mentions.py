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
        if method == "client.userBoot":
            return {"ok": True, "channels": [], "ims": []}  # 没有 subteams：只靠手配的用户组
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
    inbox.db.upsert(DM, [{"ts": ts(16), "user": "UAAAAAAAA1", "text": f"<@{ME}> dm"}], in_history=True)
    inbox.db.mark_deleted(CID, [ts(11)])

    got = inbox.mentions_since(T0 + 5, group_ids=["S0GROUP1"])
    assert [(m["message_ts"], m["mention_type"]) for m in got] == [
        (ts(10), "direct"), (ts(14), "group"), (ts(15), "direct"), (ts(16), "direct"),
    ]
    first = got[0]
    assert first["conversation_name"] == "general"
    assert first["from_user"] == "Alice"
    assert first["text"] == "@Alice can you look?"
    assert first["time"].endswith("Z") and first["thread_ts"] is None
    assert got[2]["thread_ts"] == ts(10)
    assert got[3]["conversation_name"] == "Alice"

    # 没配用户组时 group 消息不返回
    assert [m["message_ts"] for m in inbox.mentions_since(T0 + 13)] == [ts(15), ts(16)]
    # 水位线之后没有新消息
    assert inbox.mentions_since(T0 + 16) == []
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
         "attachments": [{"service_name": "X (formerly Twitter)", "title": "vLLM", "text": "We shipped 1.0"}]},
    ], in_history=True)
    inbox.db.upsert(CID, [{"ts": ts(31), "user": "UAAAAAAAA1", "text": "will post", "thread_ts": ts(30)}],
                    in_history=False)

    one = inbox.translation_source(CID, ts(30))
    assert one["source_text"] == "plz RT @Alice\n\n[X (formerly Twitter)] vLLM\nWe shipped 1.0"
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
