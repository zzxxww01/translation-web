"""翻译稿（翻译记录）存储、Slack 帖子流程（提取 → 翻译 → 标题）、@我 自动翻译、我的待办接口。"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import register_error_handlers
from src.api.routers import post_drafts as drafts_router
from src.api.routers import slack_inbox as slack_router
from src.services.post_drafts import DraftError, PostDraftStore, slack_draft_id

CID = "C07BZ1KFT29"
TS = "1794780836.689789"


def run(coro):
    return asyncio.run(coro)


def state(text="Hello", versions=None):
    return {"originalText": text, "sourceRevision": 1, "versions": versions or [], "currentVersionId": None,
            "versionMetadata": {}, "generatedTitles": [], "selectedTitle": "", "titleContentIdentity": ""}


def test_store_saves_with_rev_check_lists_and_indexes(tmp_path):
    store = PostDraftStore(tmp_path)
    doc = store.save("m_0123456789ab", {"state": state("Nvidia ships GB300")}, rev=None)
    assert doc["rev"] == 1 and doc["source"] == "manual" and doc["status"] == "draft"
    with pytest.raises(DraftError) as exc:
        store.save("m_0123456789ab", {"state": state("x")}, rev=None)  # 没带 rev = 会覆盖别人
    assert exc.value.code == "DRAFT_CONFLICT"
    v = [{"id": "v1", "content": "英伟达开始出货 GB300", "versionNumber": 1}]
    doc = store.save("m_0123456789ab", {"state": {**state("Nvidia ships GB300", v), "currentVersionId": "v1",
                                                  "generatedTitles": ["GB300 开始出货"]},
                                        "status": "done", "source": "slack"}, rev=1)
    assert doc["rev"] == 2 and doc["source"] == "manual"  # 前端改不了来源
    slack = store.put_system({"id": slack_draft_id(CID, TS), "source": "slack",
                              "slack": {"channel_id": CID, "thread_ts": TS, "title": "AI Racks"},
                              "state": state("AI racks"), "images": [{"id": "F0001234", "name": "a.png"}],
                              "status": "draft", "auto": True, "seen": False})
    chat = store.put_system({"id": slack_draft_id(CID, "1794780000.000001"), "source": "slack",
                             "slack": {"channel_id": CID, "thread_ts": "1794780000.000001"},
                             "extraction": {"has_post": False}, "state": state("")})
    items = store.list()
    assert [i["id"] for i in items] == [slack["id"], "m_0123456789ab"]  # 纯讨论的不进记录
    assert items[1]["title"] == "GB300 开始出货" and items[1]["preview"] == "英伟达开始出货 GB300"
    assert items[0]["image_count"] == 1 and items[0]["auto"] and not items[0]["seen"]
    assert [i["id"] for i in store.list("gb300 出货")] == ["m_0123456789ab"]
    assert [i["id"] for i in store.list(source="slack")] == [slack["id"]]
    index = store.slack_index()
    assert index[f"{CID}:{TS}"]["auto"] and index[f"{CID}:1794780000.000001"]["no_post"]
    assert chat["rev"] == 1 and store.delete("m_0123456789ab") and store.get("m_0123456789ab") is None
    with pytest.raises(DraftError):
        store.get("../../etc/passwd")


class FakeInbox:
    def __init__(self):
        self.store = SimpleNamespace(load=lambda: {"token": "x"})
        self.threads = [(CID, TS)]

    def post_material(self, channel_id, thread_ts):
        return {
            "thread": [{"n": 1, "text": "@用户组 AI Racks Are Heavy", "images": []},
                       {"n": 2, "text": "*1/* old", "images": ["F0000001"]},
                       {"n": 3, "text": "*1/* AI racks are heavy", "images": ["F0000002"]}],
            "images": [{"id": "F0000001", "name": "old.png"}, {"id": "F0000002", "name": "new.png"}],
            "message_ts": ["1.1", "2.2", "3.3"],
            "title": "AI Racks Are Heavy", "channel_name": "social", "permalink": "https://p", "latest_ts": "3.3",
        }

    def direct_mention_threads(self):
        return self.threads


class FakeAI:
    def __init__(self, has_post=True):
        self.calls = []
        self.has_post = has_post

    async def extract_post(self, thread, allowed, instruction=None):
        self.calls.append(instruction)
        if not self.has_post:
            return {"has_post": False, "source_text": "", "note": "纯讨论", "message_ids": [], "image_ids": [], "candidates": []}
        return {"has_post": True, "source_text": "AI racks are heavy", "note": "用的是重发版",
                "message_ids": [3], "image_ids": ["F0000002"],
                "candidates": [{"label": "第一版", "source_text": "old", "message_ids": [2], "image_ids": []}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    store = PostDraftStore(tmp_path / "drafts")
    inbox, ai = FakeInbox(), FakeAI()
    calls = {"translate": 0, "title": 0}

    async def translate(request, body):
        calls["translate"] += 1
        return SimpleNamespace(translation=f"AI 机柜太重了（{calls['translate']}）", model_used="gpt-6.2-sol")

    async def title(request, body):
        calls["title"] += 1
        return SimpleNamespace(title="AI 机柜太重\n老机房扛不住")

    monkeypatch.setattr(drafts_router, "get_draft_store", lambda: store)
    monkeypatch.setattr(drafts_router, "get_slack_inbox", lambda: inbox)
    monkeypatch.setattr(drafts_router, "get_slack_ai", lambda: ai)
    monkeypatch.setattr(drafts_router, "translate_post", SimpleNamespace(__wrapped__=translate))
    monkeypatch.setattr(drafts_router, "generate_title", SimpleNamespace(__wrapped__=title))
    monkeypatch.setattr(drafts_router, "read_slack_settings", lambda: {"auto_translate_mentions": True})
    monkeypatch.setattr(drafts_router, "_save_attempts", lambda attempts: None)
    return SimpleNamespace(store=store, inbox=inbox, ai=ai, calls=calls)


def test_pipeline_extracts_translates_titles_and_appends_on_rerun(env):
    doc = run(drafts_router.run_slack_pipeline(CID, TS))
    st = doc["state"]
    assert st["originalText"] == "AI racks are heavy" and len(st["versions"]) == 1
    v = st["versions"][0]
    assert v["sourceText"] == "AI racks are heavy" and v["isCurrent"] and st["currentVersionId"] == v["id"]
    assert st["generatedTitles"] == ["AI 机柜太重", "老机房扛不住"]
    assert st["titleContentIdentity"] == f"version:{v['id']}:{v['content']}"  # 和前端一致，标题不算过期
    assert doc["images"] == [{"id": "F0000002", "name": "new.png"}]
    assert doc["extraction"]["message_ts"] == ["3.3"] and doc["extraction"]["candidates"][0]["message_ts"] == ["2.2"]
    assert doc["slack"]["title"] == "AI Racks Are Heavy" and not doc["auto"] and doc["seen"]
    again = run(drafts_router.run_slack_pipeline(CID, TS, instruction="用第一版"))
    assert env.ai.calls == [None, "用第一版"]
    assert [x["versionNumber"] for x in again["state"]["versions"]] == [1, 2]  # 旧版本保留
    assert again["state"]["versions"][1]["instruction"] == "用第一版" and again["rev"] == 4


def test_pipeline_without_post_saves_note_only(env):
    env.ai.has_post = False
    doc = run(drafts_router.run_slack_pipeline(CID, TS))
    assert doc["extraction"]["has_post"] is False and doc["extraction"]["note"] == "纯讨论"
    assert doc["state"]["versions"] == [] and env.calls["translate"] == 0


def test_auto_translate_runs_once_per_thread(env):
    attempts = {}
    assert run(drafts_router.auto_translate_once(attempts)) == 1
    doc = env.store.get(slack_draft_id(CID, TS))
    assert doc["auto"] and doc["seen"] is False and len(doc["state"]["versions"]) == 1
    assert run(drafts_router.auto_translate_once(attempts)) == 0  # 已经有稿子
    env.store.delete(slack_draft_id(CID, TS))
    assert run(drafts_router.auto_translate_once(attempts)) == 0  # 一小时内不重试


def test_auto_translate_respects_setting(env, monkeypatch):
    monkeypatch.setattr(drafts_router, "read_slack_settings", lambda: {"auto_translate_mentions": False})
    assert run(drafts_router.auto_translate_once({})) == 0 and env.calls["translate"] == 0


def test_draft_routes_round_trip(env):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(drafts_router.router, prefix="/api")
    with TestClient(app) as client:
        created = client.post("/api/post-drafts", json={"state": state("Manual post")}).json()
        assert created["id"].startswith("m_") and created["rev"] == 1
        saved = client.put(f"/api/post-drafts/{created['id']}", json={"state": state("Edited"), "rev": 1}).json()
        assert saved["rev"] == 2
        stale = client.put(f"/api/post-drafts/{created['id']}", json={"state": state("Old"), "rev": 1})
        assert stale.status_code == 409
        assert client.get(f"/api/post-drafts/slack/{CID}/{TS}").json() == {"draft": None}
        ran = client.post(f"/api/post-drafts/slack/{CID}/{TS}/run", json={}).json()
        assert ran["id"] == slack_draft_id(CID, TS)
        assert client.get(f"/api/post-drafts/slack/{CID}/{TS}").json()["draft"]["rev"] == ran["rev"]
        listed = client.get("/api/post-drafts", params={"q": "机柜"}).json()["items"]
        assert [i["id"] for i in listed] == [ran["id"]]
        assert client.get("/api/post-drafts/bad-id").status_code == 400
        # 翻译记录不提供删除（2026-11-22 用户要求）
        assert client.delete(f"/api/post-drafts/{created['id']}").status_code == 405
        assert client.get(f"/api/post-drafts/{created['id']}").status_code == 200


def test_todos_route_sends_only_direct_items_and_sorts(monkeypatch, tmp_path):
    material = [
        {"kind": "mention", "channel_id": CID, "channel_name": "social", "conversation_kind": "channel",
         "thread_ts": TS, "title": "AI Racks", "root_text": "AI racks", "direct": True,
         "messages": [{"from": "Daksh", "time": "t", "text": "@felix sch 11/18"}], "latest_ts": "1794780900.000000"},
        {"kind": "mention", "channel_id": CID, "channel_name": "social", "conversation_kind": "channel",
         "thread_ts": "1794780000.000001", "title": "Elon post", "root_text": "", "direct": False,
         "messages": [{"from": "Reyk", "time": "t", "text": "@用户组 hi"}], "latest_ts": "1794780950.000000"},
        {"kind": "dm", "channel_id": "D0A7WQCA8NP", "channel_name": "Michelle", "conversation_kind": "im",
         "thread_ts": None, "title": "Michelle", "root_text": "", "direct": True,
         "messages": [{"from": "Michelle", "time": "t", "text": "can I use the numbers?"}], "latest_ts": "1794780800.000000"},
    ]
    sent = []

    class AI:
        async def todo_tasks(self, items):
            sent.extend(items)
            return [{"task": "Daksh 让你翻这篇", "action": "read"}, {"task": "Michelle 在等你回复", "action": "reply"}]

    monkeypatch.setattr(slack_router, "get_slack_inbox", lambda: SimpleNamespace(todo_material=lambda: material))
    monkeypatch.setattr(slack_router, "get_slack_ai", lambda: AI())
    monkeypatch.setattr(slack_router, "_draft_index", lambda: {f"{CID}:{TS}": {"id": "s_x", "status": "draft"}})
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(slack_router.router, prefix="/api")
    with TestClient(app) as client:
        data = client.get("/api/slack-inbox/todos").json()
    assert [s["where"] for s in sent] == ["#social", "私信 · Michelle"] and "root" in sent[0] and "root" not in sent[1]
    assert [i["task"] for i in data["items"]] == ["Michelle 在等你回复", "Daksh 让你翻这篇"]  # 要回复的在前
    assert data["items"][1]["draft"] == {"id": "s_x", "status": "draft"}
    assert data["items"][1]["mark"] == {"channel_id": CID, "ts": "1794780900.000000", "thread_ts": TS}
    assert data["items"][0]["mark"] == {"channel_id": "D0A7WQCA8NP", "ts": "1794780800.000000"}
    assert [f["title"] for f in data["fyi"]] == ["Elon post"]


def test_settings_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(slack_router.settings, "slack_cache_dir", str(tmp_path))
    app = FastAPI()
    app.include_router(slack_router.router, prefix="/api")
    with TestClient(app) as client:
        assert client.get("/api/slack-inbox/settings").json() == {"auto_translate_mentions": True}
        assert client.put("/api/slack-inbox/settings", json={"auto_translate_mentions": False}).json() == {
            "auto_translate_mentions": False}
        assert client.get("/api/slack-inbox/settings").json() == {"auto_translate_mentions": False}
        assert client.get("/api/slack-inbox/conversations/D0A7WQCA8NP/reply-state").json() == {"state": None}
        client.put("/api/slack-inbox/conversations/D0A7WQCA8NP/reply-state", json={"state": {"groups": [1]}})
        assert client.get("/api/slack-inbox/conversations/D0A7WQCA8NP/reply-state").json() == {"state": {"groups": [1]}}
        assert client.get("/api/slack-inbox/conversations/../reply-state").status_code in (400, 404)
