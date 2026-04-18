"""Shared typed errors for LLM provider transport failures."""

from __future__ import annotations

from dataclasses import dataclass

import requests

try:  # pragma: no cover - optional dependency guard
    import httpx  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    httpx = None

try:  # pragma: no cover - optional dependency guard
    from openai import APIConnectionError, APITimeoutError, APIError, RateLimitError  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    APIConnectionError = APITimeoutError = APIError = RateLimitError = None

try:  # pragma: no cover - optional dependency guard
    from google.genai import errors as genai_errors  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    genai_errors = None


class LLMError(RuntimeError):
    """Base class for typed LLM failures."""


class LLMConfigurationError(LLMError, ValueError):
    """Provider configuration is invalid."""


class LLMProxyConfigurationError(LLMConfigurationError):
    """A provider requires explicit proxy configuration but none was provided."""


class LLMTransportError(LLMError):
    """Base class for transport/network failures."""


class LLMConnectionError(LLMTransportError):
    """A request-layer connection failure occurred."""


class LLMProxyError(LLMTransportError):
    """A proxy connection failed."""


class LLMTLSError(LLMTransportError):
    """A TLS/SSL handshake or certificate failure occurred."""


class LLMTimeoutError(LLMTransportError):
    """A request timed out."""


class LLMUpstreamUnavailableError(LLMTransportError):
    """The upstream service was unavailable."""


@dataclass(frozen=True)
class NormalizedLLMError:
    error: LLMTransportError
    retryable: bool


def _error_text(exc: Exception) -> str:
    text = str(exc).strip()
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            payload = exc.response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error", {})
            if isinstance(error, dict):
                message = str(error.get("message", "")).strip()
                status = str(error.get("status", "")).strip()
                if message:
                    text = f"{text} | {message}"
                if status:
                    text = f"{text} | status={status}"
        body = (exc.response.text or "").strip()
        if body and body not in text:
            text = f"{text} | body={body[:300]}"
    return text


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value

    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    return None


def _is_genai_api_error(exc: Exception) -> bool:
    if exc.__class__.__module__.startswith("google.genai"):
        return True
    if genai_errors is None:
        return False
    return isinstance(exc, genai_errors.APIError)


def normalize_llm_transport_error(exc: Exception, *, provider_name: str) -> NormalizedLLMError | None:
    """Convert common transport exceptions into typed LLM errors."""

    if isinstance(exc, LLMTransportError):
        return NormalizedLLMError(error=exc, retryable=True)

    text = _error_text(exc)
    lower = text.lower()
    provider_label = provider_name.strip() or "LLM"
    status_code = _status_code(exc)
    is_genai_error = _is_genai_api_error(exc)

    if (
        isinstance(exc, requests.exceptions.ProxyError)
        or (httpx is not None and isinstance(exc, httpx.ProxyError))
        or "proxy" in lower
    ):
        return NormalizedLLMError(
            error=LLMProxyError(f"{provider_label} proxy connection failed: {text}"),
            retryable=True,
        )

    if (
        isinstance(exc, requests.exceptions.SSLError)
        or (httpx is not None and isinstance(exc, httpx.HTTPError) and "ssl" in lower)
        or "sslerror" in lower
        or "ssleoferror" in lower
        or "tls" in lower
        or "handshake" in lower
        or "certificate" in lower
        or "unexpected eof while reading" in lower
    ):
        return NormalizedLLMError(
            error=LLMTLSError(f"{provider_label} TLS failure: {text}"),
            retryable=True,
        )

    status_code = None
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        status_code = exc.response.status_code
    elif httpx is not None and isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
    elif is_genai_error and status_code is None:
        status_code = _status_code(exc)

    if (
        (RateLimitError is not None and isinstance(exc, RateLimitError))
        or
        status_code in {502, 503, 504}
        or status_code in {429, 500}
        or "service unavailable" in lower
        or "upstream" in lower
        or "bad gateway" in lower
        or "gateway timeout" in lower
        or "temporarily unavailable" in lower
        or "currently experiencing high demand" in lower
        or (is_genai_error and status_code in {429, 500, 502, 503, 504})
    ):
        return NormalizedLLMError(
            error=LLMUpstreamUnavailableError(
                f"{provider_label} upstream unavailable: {text}"
            ),
            retryable=True,
        )

    if (
        (APITimeoutError is not None and isinstance(exc, APITimeoutError))
        or
        isinstance(exc, requests.exceptions.Timeout)
        or (httpx is not None and isinstance(exc, httpx.TimeoutException))
        or "timed out" in lower
        or "timeout" in lower
        or "deadline exceeded" in lower
        or (is_genai_error and "deadline" in lower)
    ):
        return NormalizedLLMError(
            error=LLMTimeoutError(f"{provider_label} request timed out: {text}"),
            retryable=True,
        )

    if (
        (APIConnectionError is not None and isinstance(exc, APIConnectionError))
        or
        isinstance(exc, requests.exceptions.ConnectionError)
        or (httpx is not None and isinstance(exc, httpx.ConnectError))
        or (httpx is not None and isinstance(exc, httpx.ReadError))
        or (httpx is not None and isinstance(exc, httpx.RemoteProtocolError))
        or (httpx is not None and isinstance(exc, httpx.NetworkError))
        or "failed to establish a new connection" in lower
        or "connection aborted" in lower
        or "connection reset" in lower
        or "remote end closed connection without response" in lower
        or "network is unreachable" in lower
        or "name or service not known" in lower
        or "temporary failure in name resolution" in lower
        or "max retries exceeded with url" in lower
        or (is_genai_error and any(
            phrase in lower
            for phrase in [
                "connect",
                "connection",
                "network error",
                "network unreachable",
                "dns",
                "name resolution",
                "socket",
                "broken pipe",
                "reset by peer",
            ]
        ))
    ):
        return NormalizedLLMError(
            error=LLMConnectionError(f"{provider_label} connection failed: {text}"),
            retryable=True,
        )

    return None
