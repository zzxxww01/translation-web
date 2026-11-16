"""
Rate limiting middleware for public-facing APIs.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# app.py 从这里统一拿限流器、异常类型和默认处理器，所以后两者是有意的再导出
__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler"]

# 使用 IP 地址作为限流标识
limiter = Limiter(key_func=get_remote_address, default_limits=[])
