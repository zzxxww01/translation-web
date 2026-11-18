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
