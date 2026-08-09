import json

import pytest

from src.api.middleware.upload_limit import LimitUploadSize


def _scope(headers=()):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": list(headers),
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }


async def _invoke(*, headers=(), chunks=(), limit=5):
    sent = []
    consumed = []
    messages = [
        {
            "type": "http.request",
            "body": body,
            "more_body": index < len(chunks) - 1,
        }
        for index, body in enumerate(chunks)
    ] or [{"type": "http.request", "body": b"", "more_body": False}]

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    async def endpoint(_scope, receive_body, send_response):
        while True:
            message = await receive_body()
            consumed.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        await send_response(
            {"type": "http.response.start", "status": 200, "headers": []}
        )
        await send_response({"type": "http.response.body", "body": b"ok"})

    middleware = LimitUploadSize(endpoint, max_request_size=limit)
    await middleware(_scope(headers), receive, send)
    status = next(
        message["status"]
        for message in sent
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return status, body, consumed


@pytest.mark.asyncio
async def test_rejects_oversized_declared_body_before_endpoint_runs() -> None:
    status, body, consumed = await _invoke(
        headers=[(b"content-length", b"6")],
        chunks=[b"123456"],
    )

    assert status == 413
    assert json.loads(body) == {
        "detail": "Request body too large (max 5 bytes)"
    }
    assert consumed == []


@pytest.mark.asyncio
async def test_rejects_invalid_content_length_as_bad_request() -> None:
    status, body, consumed = await _invoke(
        headers=[(b"content-length", b"not-a-number")],
        chunks=[b"abc"],
    )

    assert status == 400
    assert json.loads(body) == {"detail": "Invalid Content-Length header"}
    assert consumed == []


@pytest.mark.asyncio
async def test_enforces_limit_when_content_length_is_missing() -> None:
    status, body, consumed = await _invoke(chunks=[b"123", b"456"])

    assert status == 413
    assert json.loads(body) == {
        "detail": "Request body too large (max 5 bytes)"
    }
    assert consumed == [b"123"]


@pytest.mark.asyncio
async def test_allows_body_at_exact_limit() -> None:
    status, body, consumed = await _invoke(
        headers=[(b"content-length", b"5")],
        chunks=[b"12", b"345"],
    )

    assert status == 200
    assert body == b"ok"
    assert consumed == [b"12", b"345"]
