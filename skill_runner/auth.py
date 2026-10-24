"""单用户口令登录。

整个服务等于让 Claude 在服务器上执行命令、消耗订阅额度，所以除登录接口外全部要求有效 cookie；
口令未配置时一律拒绝（fail closed），而不是放行。
"""

from __future__ import annotations

import hashlib
import hmac
import time

COOKIE_NAME = "skill_runner_session"
SESSION_TTL_S = 30 * 24 * 3600


def check_password(expected: str, given: str) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), given.encode("utf-8"))


def _sign(secret: bytes, issued: int) -> str:
    return hmac.new(secret, f"v1.{issued}".encode("ascii"), hashlib.sha256).hexdigest()


def issue_token(secret: bytes, now: float | None = None) -> str:
    issued = int(time.time() if now is None else now)
    return f"{issued}.{_sign(secret, issued)}"


def verify_token(secret: bytes, token: str | None, now: float | None = None) -> bool:
    if not token or "." not in token:
        return False
    issued_raw, signature = token.split(".", 1)
    if not issued_raw.isdigit():
        return False
    issued = int(issued_raw)
    current = time.time() if now is None else now
    if issued > current + 60 or current - issued > SESSION_TTL_S:
        return False
    return hmac.compare_digest(signature, _sign(secret, issued))


class LoginLimiter:
    """连续失败 max_failures 次后锁定 lockout_s 秒；成功一次即清零。只有一个用户，不按 IP 区分。"""

    def __init__(self, max_failures: int = 5, lockout_s: float = 60.0):
        self.max_failures = max_failures
        self.lockout_s = lockout_s
        self._failures = 0
        self._locked_until = 0.0

    def locked_for(self, now: float | None = None) -> float:
        current = time.monotonic() if now is None else now
        return max(0.0, self._locked_until - current)

    def record(self, success: bool, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        if success:
            self._failures = 0
            return
        self._failures += 1
        if self._failures >= self.max_failures:
            self._locked_until = current + self.lockout_s
            self._failures = 0
