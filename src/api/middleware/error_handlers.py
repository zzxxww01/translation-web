"""
Error Handlers - 统一异常处理

提供全局异常处理中间件和自定义异常类。
"""

from typing import Any, Dict, Optional, Union
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


# ============ 自定义异常类 ============


class APIException(Exception):
    """API 基础异常类"""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Internal server error",
        error_code: Optional[str] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


class NotFoundException(APIException):
    """资源未找到异常"""

    def __init__(self, detail: str = "Resource not found", error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code or "NOT_FOUND",
        )


class BadRequestException(APIException):
    """错误请求异常"""

    def __init__(self, detail: str = "Bad request", error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code or "BAD_REQUEST",
        )


class UnauthorizedException(APIException):
    """未授权异常"""

    def __init__(self, detail: str = "Unauthorized", error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code or "UNAUTHORIZED",
        )


class ServiceUnavailableException(APIException):
    """服务不可用异常"""

    def __init__(self, detail: str = "Service unavailable", error_code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code or "SERVICE_UNAVAILABLE",
        )


# ============ 错误响应格式 ============


def create_error_response(
    status_code: int,
    detail: str,
    error_code: Optional[str] = None,
    path: Optional[str] = None,
) -> JSONResponse:
    """创建标准错误响应"""
    content: Dict[str, Any] = {"detail": detail}
    if error_code:
        content["error_code"] = error_code
    if path:
        content["path"] = path

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


# ============ 异常处理器 ============


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """处理自定义 API 异常"""
    logger.error(f"API Exception: {exc.detail} at {request.url.path}")
    return create_error_response(
        status_code=exc.status_code,
        detail=exc.detail,
        error_code=exc.error_code,
        path=request.url.path,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """处理 HTTP 异常"""
    logger.warning(f"HTTP Exception: {exc.detail} at {request.url.path}")
    return create_error_response(
        status_code=exc.status_code,
        detail=str(exc.detail),
        path=request.url.path,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证异常"""
    errors = exc.errors()
    error_details = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in errors
    ]

    logger.warning(f"Validation error at {request.url.path}: {error_details}")
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request validation failed",
        path=request.url.path,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常"""
    logger.exception(f"Unhandled exception at {request.url.path}: {exc}")
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
        error_code="INTERNAL_ERROR",
        path=request.url.path,
    )


# ============ 中间件注册函数 ============


def register_error_handlers(app: FastAPI) -> None:
    """注册所有异常处理器到 FastAPI 应用"""

    # 自定义 API 异常
    app.add_exception_handler(APIException, api_exception_handler)

    # HTTP 异常（FastAPI 内置）
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 请求验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 通用异常捕获（生产环境应谨慎使用）
    app.add_exception_handler(Exception, general_exception_handler)
