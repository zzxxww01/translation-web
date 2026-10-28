import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

from skill_runner.app import PREFIX, create_app
from skill_runner.auth import COOKIE_NAME

from skill_runner_fakes import FakeFactory, make_config


@pytest.fixture
def setup(tmp_path):
    config = make_config(tmp_path)
    factory = FakeFactory()
    app = create_app(config, session_factory=factory)
    with TestClient(app) as client:
        yield client, factory, app.state.runner


def login(client, password="s3cret"):
    return client.post(f"{PREFIX}/login", json={"password": password})


def test_everything_but_login_requires_cookie(setup):
    client, _, _ = setup
    for method, path in [("get", "/me"), ("get", "/runs"), ("get", "/catalog"), ("post", "/runs"),
                         ("get", "/runtime"), ("post", "/runtime/check"), ("post", "/runtime/codex/update"),
                         ("get", "/runs/20260101-000000-abcdef/events"), ("post", "/runs/20260101-000000-abcdef/stop"),
                         ("delete", "/runs/20260101-000000-abcdef")]:
        assert getattr(client, method)(PREFIX + path).status_code == 401, path
    client.cookies.set(COOKIE_NAME, "123.forged", path=PREFIX)
    assert client.get(f"{PREFIX}/me").status_code == 401


def test_login_sets_strict_httponly_cookie_and_logout_clears_it(setup):
    client, _, _ = setup
    assert login(client, "wrong").status_code == 401
    response = login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and f"Path={PREFIX}" in cookie
    assert client.get(f"{PREFIX}/me").json()["ok"] is True
    client.post(f"{PREFIX}/logout")
    assert client.get(f"{PREFIX}/me").status_code == 401


def test_stop_closes_run_without_deleting_history(setup):
    client, factory, _ = setup
    login(client)
    meta = client.post(f"{PREFIX}/runs", data={"message": "translate"}).json()
    response = client.post(f"{PREFIX}/runs/{meta['id']}/stop")
    assert response.status_code == 200
    assert response.json()['status'] == 'error'
    assert factory.last.closed
    assert client.get(f"{PREFIX}/runs/{meta['id']}").status_code == 200


def test_runtime_routes_check_versions_and_reject_updates_during_work(setup, monkeypatch):
    client, _, runner = setup
    login(client)
    service = client.app.state.runtime_updates

    async def current(_harness):
        return "1.0.0"

    async def install_command(_harness, _target):
        return ["unused-test-installer"]

    monkeypatch.setattr(service, "_current", current)
    monkeypatch.setattr(service, "_install_command", install_command)
    monkeypatch.setattr("skill_runner.runtime_updates._latest_version", lambda _: "1.1.0")
    assert client.post(f"{PREFIX}/runtime/unknown/update").status_code == 400
    assert client.post(f"{PREFIX}/runtime/codex/update").status_code == 400
    checked = client.post(f"{PREFIX}/runtime/check")
    assert checked.status_code == 200
    assert all(item["current"] == "1.0.0" and item["latest"] == "1.1.0"
               and item["can_update"] for item in checked.json()["runtimes"])
    assert client.get(f"{PREFIX}/runtime").json() == checked.json()
    assert client.post(f"{PREFIX}/runs", data={"message": "working"}).status_code == 200
    blocked = client.post(f"{PREFIX}/runtime/codex/update")
    assert blocked.status_code == 409
    assert "正在运行" in blocked.json()["detail"]
    assert not service.active
    assert not runner._runtime_maintenance


def test_login_locks_after_repeated_failures(setup):
    client, _, _ = setup
    for _ in range(5):
        assert login(client, "nope").status_code == 401
    locked = login(client)
    assert locked.status_code == 429


def test_login_refused_when_password_unconfigured(tmp_path):
    app = create_app(make_config(tmp_path, password=""), session_factory=FakeFactory())
    with TestClient(app) as client:
        assert login(client, "").status_code == 503


def test_billing_override_env_is_stripped_on_startup(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example")
    app = create_app(make_config(tmp_path), session_factory=FakeFactory())
    with TestClient(app):
        assert "ANTHROPIC_API_KEY" not in os.environ
        assert "ANTHROPIC_BASE_URL" not in os.environ


def test_create_run_saves_upload_and_dispatches_skill(setup):
    client, factory, runner = setup
    login(client)
    response = client.post(
        f"{PREFIX}/runs",
        data={"skill": "four-step-translate", "message": "精翻这篇"},
        files=[("files", ("../article.html", b"<html>x</html>", "text/html"))],
    )
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "running" and run["title"] == "精翻这篇"
    assert factory.last.sent[0].startswith("/four-step-translate 精翻这篇")
    assert "- input/article.html" in factory.last.sent[0]
    saved = runner.store.run_dir(run["id"]) / "input" / "article.html"
    assert saved.read_bytes() == b"<html>x</html>"
    listed = client.get(f"{PREFIX}/runs").json()
    assert [r["id"] for r in listed] == [run["id"]]


def test_catalog_lists_chat_first_with_agent_cards(setup):
    client, _, _ = setup
    login(client)
    catalog = client.get(f"{PREFIX}/catalog").json()
    assert catalog[0]["name"] == "" and catalog[0]["title"] == "通用 Agent"
    assert [a["name"] for a in catalog[1:]] == ["four-step-translate", "podcast-cn-dubber"]
    assert all({"title", "icon", "hint", "examples", "available"} <= a.keys() for a in catalog)


def test_create_run_without_skill_is_plain_chat(setup):
    client, factory, _ = setup
    login(client)
    response = client.post(f"{PREFIX}/runs", data={"message": "解释一下 HBM"})
    assert response.status_code == 200, response.text
    assert response.json()["skill"] == ""
    assert factory.last.sent == ["解释一下 HBM"]


def test_create_run_validation(setup):
    client, _, _ = setup
    login(client)
    assert client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate"}).status_code == 400
    unknown = client.post(f"{PREFIX}/runs", data={"skill": "evil", "message": "x"})
    assert unknown.status_code == 400 and "未启用" in unknown.json()["detail"]


def test_oversized_upload_is_rejected_and_run_discarded(tmp_path):
    config = make_config(tmp_path, max_upload_bytes=4)
    app = create_app(config, session_factory=FakeFactory())
    with TestClient(app) as client:
        login(client)
        response = client.post(
            f"{PREFIX}/runs",
            data={"skill": "four-step-translate", "message": "x"},
            files=[("files", ("a.mp4", b"12345", "video/mp4"))],
        )
        assert response.status_code == 413
        assert client.get(f"{PREFIX}/runs").json() == []
        log = (config.home / "deleted" / "deleted.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(log[-1])["reason"] == "upload_failed"


def test_message_answer_interrupt_and_delete_endpoints(setup):
    client, factory, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]
    reply = client.post(f"{PREFIX}/runs/{run_id}/messages", data={"message": "顺便译标题"})
    assert reply.status_code == 200
    assert factory.last.sent[-1] == "顺便译标题"
    assert client.post(f"{PREFIX}/runs/{run_id}/answer", json={"qid": "nope", "answers": {"q": "a"}}).status_code == 409
    assert client.post(f"{PREFIX}/runs/{run_id}/interrupt").status_code == 200
    assert factory.last.interrupted
    assert client.delete(f"{PREFIX}/runs/{run_id}").status_code == 409  # 还在运行
    assert client.get(f"{PREFIX}/runs/20260101-000000-abcdef").status_code == 404


def test_file_listing_and_download_guard_paths(setup):
    client, _, runner = setup
    login(client)
    run_id = client.post(
        f"{PREFIX}/runs",
        data={"skill": "four-step-translate", "message": "go"},
        files=[("files", ("a.html", b"<p>", "text/html"))],
    ).json()["id"]
    out = runner.store.run_dir(run_id) / "zh.md"
    out.write_text("译文", encoding="utf-8")
    files = client.get(f"{PREFIX}/runs/{run_id}/files").json()
    assert [f["path"] for f in files] == ["input/a.html", "zh.md"]
    download = client.get(f"{PREFIX}/runs/{run_id}/files/zh.md")
    assert download.status_code == 200 and download.content.decode("utf-8") == "译文"
    assert "attachment" in download.headers["content-disposition"]
    for bad in ("meta.json", "events.jsonl", "..%2F..%2Fsecret", "input/../../x"):
        assert client.get(f"{PREFIX}/runs/{run_id}/files/{bad}").status_code == 404, bad


def test_event_stream_replays_after_last_event_id(setup):
    client, _, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]

    # 真实的流不会自己结束；这里在订阅后立刻塞一个结束信号，让 TestClient 能读完整个响应
    original = runner.subscribe

    def subscribe_then_end(rid, after_seq=0):
        backlog, queue = original(rid, after_seq)
        queue.put_nowait(None)
        return backlog, queue

    runner.subscribe = subscribe_then_end
    response = client.get(f"{PREFIX}/runs/{run_id}/events", headers={"Last-Event-ID": "1"})
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    frames = [f for f in response.text.split("\n\n") if f.startswith("id: ")]
    events = [json.loads(f.split("data: ", 1)[1]) for f in frames]
    assert [e["seq"] for e in events] == [2]
    assert events[0]["type"] == "status" and events[0]["status"] == "running"


def test_event_stream_sends_named_ping_when_idle(setup, monkeypatch):
    client, _, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]
    monkeypatch.setattr("skill_runner.app.SSE_PING_S", 0.05)
    original = runner.subscribe

    def subscribe_then_end_later(rid, after_seq=0):
        backlog, queue = original(rid, after_seq)
        asyncio.get_running_loop().call_later(0.3, queue.put_nowait, None)
        return backlog, queue

    runner.subscribe = subscribe_then_end_later
    body = client.get(f"{PREFIX}/runs/{run_id}/events?after=99").text
    # 心跳是具名事件（页面脚本收得到），不是 SSE 注释
    assert "event: ping\ndata: {}\n\n" in body
    assert not any(line.startswith(":") for line in body.splitlines())


def test_session_renews_once_a_day_so_regular_use_never_asks_again(tmp_path):
    import time

    from skill_runner import auth

    config = make_config(tmp_path)
    app = create_app(config, session_factory=FakeFactory())
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, auth.issue_token(config.session_secret, now=time.time() - 2 * 24 * 3600), path=PREFIX)
        renewed = client.get(f"{PREFIX}/me")
        assert renewed.status_code == 200
        assert f"Max-Age={auth.SESSION_TTL_S}" in renewed.headers["set-cookie"]
        assert "set-cookie" not in client.get(f"{PREFIX}/me").headers  # 刚续过，不再下发


def test_delete_endpoint_archives_and_records_the_caller(setup):
    client, factory, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]
    assert client.post(f"{PREFIX}/runs/{run_id}/stop").json()["status"] == "error"  # 停下来才能删

    response = client.delete(f"{PREFIX}/runs/{run_id}", headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"})

    assert response.status_code == 200
    assert client.get(f"{PREFIX}/runs/{run_id}").status_code == 404
    assert run_id not in [r["id"] for r in client.get(f"{PREFIX}/runs").json()]
    record = json.loads((runner.store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert (record["run_id"], record["client_ip"]) == (run_id, "203.0.113.9")


@pytest.mark.parametrize("headers, expected", [
    ({"CF-Connecting-IP": "198.51.100.5", "X-Forwarded-For": "203.0.113.9"}, "198.51.100.5"),
    ({"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}, "203.0.113.9"),
    ({}, "testclient"),
])
def test_delete_records_caller_ip_by_header_precedence(setup, headers, expected):
    client, factory, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]
    client.post(f"{PREFIX}/runs/{run_id}/stop")

    assert client.delete(f"{PREFIX}/runs/{run_id}", headers=headers).status_code == 200

    record = json.loads((runner.store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["client_ip"] == expected
