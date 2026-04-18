"""Helpers for presenting typed LLM failures at the API boundary."""

from __future__ import annotations

import asyncio

from src.llm.errors import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProxyConfigurationError,
    LLMProxyError,
    LLMTLSError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)

from ..middleware import ServiceUnavailableException


def format_llm_exception(exc: Exception, *, operation: str, timeout_s: int | None = None) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        if timeout_s is not None:
            return f"{operation} failed: request timed out after {timeout_s}s."
        return f"{operation} failed: request timed out."

    if isinstance(exc, LLMProxyConfigurationError):
        return (
            f"{operation} failed: required proxy configuration is missing. "
            "Check the provider network settings and Gemini proxy env vars."
        )

    if isinstance(exc, LLMProxyError):
        return (
            f"{operation} failed: proxy connection failed. "
            "Check Clash/mihomo status, proxy port, and current outbound node."
        )

    if isinstance(exc, LLMTLSError):
        return (
            f"{operation} failed: upstream TLS handshake was interrupted. "
            "This is usually a proxy or outbound route issue."
        )

    if isinstance(exc, LLMTimeoutError):
        if timeout_s is not None:
            return f"{operation} failed: upstream request timed out after {timeout_s}s."
        return f"{operation} failed: upstream request timed out."

    if isinstance(exc, LLMConnectionError):
        return f"{operation} failed: upstream connection could not be established."

    if isinstance(exc, LLMUpstreamUnavailableError):
        return f"{operation} failed: upstream service is temporarily unavailable."

    if isinstance(exc, LLMConfigurationError):
        return f"{operation} failed: LLM configuration is invalid."

    text = str(exc).strip()
    if text:
        return f"{operation} failed: {text}"
    return f"{operation} failed."


def raise_llm_service_unavailable(
    *,
    operation: str,
    exc: Exception,
    timeout_s: int | None = None,
) -> None:
    raise ServiceUnavailableException(
        detail=format_llm_exception(exc, operation=operation, timeout_s=timeout_s),
        error_code="LLM_UNAVAILABLE",
    ) from exc
