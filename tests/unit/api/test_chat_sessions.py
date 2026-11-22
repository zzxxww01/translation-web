"""Chatbot 会话（存在服务器上）和联网回答：模型、搜索都用假的。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import register_error_handlers
from src.api.middleware.rate_limit import limiter
from src.api.routers import tools as tools_router
from src.api.routers import tools_chat
from src.services.chat_sessions import ChatSessionStore


def make_client(monkeypatch, tmp_path, *, search=None, reply="普通回答", calls=None):
    calls = calls if calls is not None else []

    async def fake_generate(prompt, *, task_type, model=None, **kwargs):
        calls.append({"kind": "plain", "prompt": prompt, "model": model})
        if isinstance(reply, Exception):
            raise reply
        return f" {reply} "

    def fake_search(prompt, alias, timeout):
        calls.append({"kind": "search", "prompt": prompt, "model": alias})
        if isinstance(search, Exception):
            raise search
        return search

    store = ChatSessionStore(tmp_path / "chat")
    monkeypatch.setattr(tools_chat, "get_chat_store", lambda: store)
    monkeypatch.setattr(tools_chat, "generate_with_fallback_budget", fake_generate)
    monkeypatch.setattr(tools_chat, "generate_with_web_search", fake_search)
    monkeypatch.setattr(tools_chat, "get_task_model_alias", lambda task: "gpt-6.2-sol")
    app = FastAPI()
    app.state.limiter = limiter
    register_error_handlers(app)
    app.include_router(tools_router.router, prefix="/api")
    return TestClient(app), calls


def test_sessions_are_listed_newest_first_renamed_and_deleted(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path, search=None)
    first = client.post("/api/tools/chat/sessions", json={}).json()
    second = client.post("/api/tools/chat/sessions", json={}).json()
    client.post(f"/api/tools/chat/sessions/{first['id']}/messages", json={"content": "HBM 是什么？\n第二行"})
    listed = client.get("/api/tools/chat/sessions").json()["sessions"]
    assert [s["id"] for s in listed] == [first["id"], second["id"]]
    assert listed[0]["title"] == "HBM 是什么？" and listed[0]["count"] == 2

    assert client.patch(f"/api/tools/chat/sessions/{first['id']}", json={"title": "内存"}).json()["title"] == "内存"
    # 改过的标题不会被后面的话覆盖
    client.post(f"/api/tools/chat/sessions/{first['id']}/messages", json={"content": "再问一句"})
    assert client.get(f"/api/tools/chat/sessions/{first['id']}").json()["title"] == "内存"

    assert client.delete(f"/api/tools/chat/sessions/{second['id']}").json() == {"deleted": True}
    assert client.get(f"/api/tools/chat/sessions/{second['id']}").status_code == 404
    assert client.get("/api/tools/chat/sessions/../etc").status_code == 404
    assert client.get("/api/tools/chat/sessions/c_bad").status_code == 400


def test_pinned_sessions_come_first_and_pinning_does_not_count_as_activity(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path, search=None)
    old = client.post("/api/tools/chat/sessions", json={}).json()
    new = client.post("/api/tools/chat/sessions", json={}).json()
    client.post(f"/api/tools/chat/sessions/{new['id']}/messages", json={"content": "最近聊的"})
    pinned = client.put(f"/api/tools/chat/sessions/{old['id']}/pin", json={"pinned": True}).json()
    assert pinned["pinned_at"] and pinned["updated_at"] == old["updated_at"]
    listed = client.get("/api/tools/chat/sessions").json()["sessions"]
    assert [s["id"] for s in listed] == [old["id"], new["id"]] and listed[0]["pinned_at"]

    client.put(f"/api/tools/chat/sessions/{old['id']}/pin", json={"pinned": False})
    listed = client.get("/api/tools/chat/sessions").json()["sessions"]
    assert [s["id"] for s in listed] == [new["id"], old["id"]] and listed[1]["pinned_at"] is None


def test_old_browser_conversation_is_imported(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path)
    doc = client.post("/api/tools/chat/sessions", json={"messages": [
        {"role": "user", "content": "最近有什么新闻"}, {"role": "assistant", "content": "我没法联网"}]}).json()
    assert doc["title"] == "最近有什么新闻"
    assert [m["role"] for m in doc["messages"]] == ["user", "assistant"]


def test_web_search_answer_keeps_sources_and_history(monkeypatch, tmp_path):
    search = {"text": " 今天的新闻… ", "sources": [{"title": "FT", "url": "https://ft.com/x"}, {"title": "坏的", "url": "javascript:1"}]}
    client, calls = make_client(monkeypatch, tmp_path, search=search)
    sid = client.post("/api/tools/chat/sessions", json={}).json()["id"]
    doc = client.post(f"/api/tools/chat/sessions/{sid}/messages", json={"content": "最近有什么新闻"}).json()
    reply = doc["messages"][-1]
    assert reply["role"] == "assistant" and reply["content"] == "今天的新闻…"
    assert reply["sources"] == [{"title": "FT", "url": "https://ft.com/x"}] and "note" not in reply
    assert calls[0]["kind"] == "search" and calls[0]["model"] == "gpt-6.2-sol"
    assert "你可以联网搜索" in calls[0]["prompt"] and "今天是 " in calls[0]["prompt"]

    client.post(f"/api/tools/chat/sessions/{sid}/messages", json={"content": "第二条", "web_search": False})
    assert calls[-1]["kind"] == "plain" and "你可以联网搜索" not in calls[-1]["prompt"]
    assert calls[-1]["prompt"].index("最近有什么新闻") < calls[-1]["prompt"].index("第二条")


def test_models_without_search_and_failed_search_answer_offline_with_a_note(monkeypatch, tmp_path):
    client, calls = make_client(monkeypatch, tmp_path, search=None)
    sid = client.post("/api/tools/chat/sessions", json={}).json()["id"]
    doc = client.post(f"/api/tools/chat/sessions/{sid}/messages", json={"content": "hi", "model": "qwen-plus"}).json()
    assert doc["messages"][-1]["note"] == tools_chat.NOTE_NO_SEARCH_MODEL
    assert calls[-1] == {"kind": "plain", "prompt": calls[-1]["prompt"], "model": "qwen-plus"}

    client2, _ = make_client(monkeypatch, tmp_path / "b", search=RuntimeError("boom"))
    sid = client2.post("/api/tools/chat/sessions", json={}).json()["id"]
    doc = client2.post(f"/api/tools/chat/sessions/{sid}/messages", json={"content": "hi"}).json()
    assert doc["messages"][-1]["content"] == "普通回答" and doc["messages"][-1]["note"] == tools_chat.NOTE_SEARCH_FAILED


def test_failed_reply_keeps_the_question_and_reply_endpoint_retries_and_regenerates(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch, tmp_path, search=RuntimeError("down"), reply=RuntimeError("down"))
    sid = client.post("/api/tools/chat/sessions", json={}).json()["id"]
    res = client.post(f"/api/tools/chat/sessions/{sid}/messages", json={"content": "问题"})
    assert res.status_code == 503
    doc = client.get(f"/api/tools/chat/sessions/{sid}").json()
    assert [m["content"] for m in doc["messages"]] == ["问题"]  # 问题没丢

    client, _ = make_client(monkeypatch, tmp_path, search={"text": "答案一", "sources": []})
    doc = client.post(f"/api/tools/chat/sessions/{sid}/reply", json={}).json()
    assert [m["content"] for m in doc["messages"]] == ["问题", "答案一"]
    client, _ = make_client(monkeypatch, tmp_path, search={"text": "答案二", "sources": []})
    doc = client.post(f"/api/tools/chat/sessions/{sid}/reply", json={}).json()
    assert [m["content"] for m in doc["messages"]] == ["问题", "答案二"]  # 重新回答替换掉旧回复
