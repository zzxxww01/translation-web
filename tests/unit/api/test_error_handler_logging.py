import logging

import pytest
from starlette.requests import Request

from src.api.middleware.error_handlers import (
    BadRequestException,
    NotFoundException,
    ServiceUnavailableException,
    api_exception_handler,
)


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/missing",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "expected_level"),
    [
        (NotFoundException(), logging.DEBUG),
        (BadRequestException(), logging.WARNING),
        (ServiceUnavailableException(), logging.ERROR),
    ],
)
async def test_api_exception_log_level_matches_failure_class(
    exception,
    expected_level: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="src.api.middleware.error_handlers")

    response = await api_exception_handler(_request(), exception)

    assert response.status_code == exception.status_code
    matching = [
        record
        for record in caplog.records
        if record.name == "src.api.middleware.error_handlers"
    ]
    assert matching[-1].levelno == expected_level
