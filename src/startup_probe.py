"""Helpers for deciding whether the local Translation Agent is already running."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def _fetch_json(url: str, timeout: float) -> dict:
    with urlopen(url, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def is_translation_agent_running(port: int, timeout: float = 2.0) -> bool:
    """Return True when the target port already serves this app."""
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        payload = _fetch_json(url, timeout)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False

    return (
        payload.get("status") == "healthy"
        and payload.get("service") == "Translation Agent API"
    )
