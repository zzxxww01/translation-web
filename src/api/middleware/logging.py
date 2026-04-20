"""
Logging Middleware - 请求日志中间件

记录所有 HTTP 请求的详细信息。
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)

# 慢请求阈值（秒）
SLOW_REQUEST_THRESHOLD = 5.0


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录请求方法、路径、处理时间、状态码等信息
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""

        # 跳过健康检查端点的日志
        if request.url.path == "/api/health":
            return await call_next(request)

        # 记录请求开始
        start_time = time.time()

        # 记录请求信息
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 检查慢请求
            if process_time > SLOW_REQUEST_THRESHOLD:
                logger.warning(
                    f"SLOW REQUEST: {request.method} {request.url.path} "
                    f"took {process_time:.3f}s (threshold: {SLOW_REQUEST_THRESHOLD}s)"
                )

            # 记录响应信息
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"status={response.status_code} "
                f"time={process_time:.3f}s"
            )

            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 记录错误
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} "
                f"time={process_time:.3f}s"
            )
            raise
