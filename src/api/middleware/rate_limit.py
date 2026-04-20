"""
Rate limiting middleware for public-facing APIs.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 使用 IP 地址作为限流标识
limiter = Limiter(key_func=get_remote_address)
