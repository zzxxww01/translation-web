"""ASGI request-body size enforcement.

The reverse proxy rejects oversized public uploads, but the application must
also protect direct/local access and requests without a Content-Length header.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _RequestBodyTooLarge(Exception):
    pass


class LimitUploadSize:
    """Reject oversized mutation bodies before or while they are streamed."""

    BODY_METHODS = {"POST", "PUT", "PATCH"}

    def __init__(self, app: ASGIApp, *, max_request_size: int) -> None:
        if max_request_size <= 0:
            raise ValueError("max_request_size must be positive")
        self.app = app
        self.max_request_size = max_request_size
        if max_request_size >= 1024 * 1024:
            display_limit = f"{max_request_size / (1024 * 1024):g}MB"
        else:
            display_limit = f"{max_request_size} bytes"
        self._too_large_detail = f"Request body too large (max {display_limit})"

    async def _respond(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        detail: str,
    ) -> None:
        response = JSONResponse({"detail": detail}, status_code=status_code)
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope.get("type") != "http"
            or str(scope.get("method", "")).upper() not in self.BODY_METHODS
        ):
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value.strip()
            for key, value in scope.get("headers", [])
            if key.lower() == b"content-length"
        ]
        if content_lengths:
            if len(content_lengths) != 1 or not content_lengths[0].isdigit():
                await self._respond(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    detail="Invalid Content-Length header",
                )
                return
            declared_size = int(content_lengths[0])
            if declared_size > self.max_request_size:
                await self._respond(
                    scope,
                    receive,
                    send,
                    status_code=413,
                    detail=self._too_large_detail,
                )
                return

        received_size = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_size
            message = await receive()
            if message.get("type") == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_request_size:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            # Body-parsing endpoints consume the request before starting their
            # response. If an unusual ASGI app has already sent headers, a
            # second response would violate the protocol, so let the server
            # close that response instead.
            if response_started:
                raise
            await self._respond(
                scope,
                receive,
                send,
                status_code=413,
                detail=self._too_large_detail,
            )
