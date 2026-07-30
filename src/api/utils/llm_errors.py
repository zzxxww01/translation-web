"""Helpers for presenting typed LLM failures at the API boundary."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import NoReturn

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


logger = logging.getLogger(__name__)


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

    # BE-06：未识别异常不再把 str(exc) 原样回传给客户端（会泄露异常类型、属性名等
    # 内部实现细节）。对外只给一个关联 id，真实异常写日志，排查时按 ref 检索。
    ref = uuid.uuid4().hex[:8]
    logger.error(
        "%s failed with unexpected error (ref=%s)",
        operation,
        ref,
        exc_info=exc,
    )
    return f"{operation} failed: unexpected server error (ref={ref})."


def raise_llm_service_unavailable(
    *,
    operation: str,
    exc: Exception,
    timeout_s: int | None = None,
) -> NoReturn:
    """永不返回。

    调用方（如 translate_posts）依赖这一点：`except` 块之后紧跟着对
    `translation` 之类局部变量的使用，若本函数存在任何早返回路径，那里会
    直接 NameError。用 NoReturn 让类型检查器替我们守住这个契约。
    """
    raise ServiceUnavailableException(
        detail=format_llm_exception(exc, operation=operation, timeout_s=timeout_s),
        error_code="LLM_UNAVAILABLE",
    ) from exc
