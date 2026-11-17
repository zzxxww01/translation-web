"""CLI 调本机翻译服务时不走代理。

.env 和 skill-runner 的环境里有给外网用的 HTTP(S)_PROXY；urllib 默认连 127.0.0.1 也走它，
代理回 503，翻译就失败了。本机地址直连，其余照旧按环境变量走代理。
"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener
from urllib.request import urlopen as _urlopen

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_direct = build_opener(ProxyHandler({}))


def urlopen(request: Request | str, timeout: float | None = None):
    url = request.full_url if isinstance(request, Request) else request
    if (urlparse(url).hostname or "") in _LOCAL_HOSTS:
        return _direct.open(request, timeout=timeout)
    return _urlopen(request, timeout=timeout)
