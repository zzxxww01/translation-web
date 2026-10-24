"""Substack 文章下载（含本人订阅的付费文章）与 SemiAnalysis 文章列表。

网站本身不需要登录，所以这里等于「服务器替任何访问者去请求一个链接」，必须防住
被借道访问内网：只允许 https/443，域名解析出的每个地址都必须是公网地址，重定向
逐跳重新校验；订阅 cookie 只发给它所属的那一个域名；下载结果必须是 Substack
文章页才会交给建项目流程，内网服务的响应不会变成项目被看到。
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup
from dotenv import dotenv_values

SEMIANALYSIS_BASE_URL = "https://newsletter.semianalysis.com"
DEFAULT_COOKIE_DOMAIN = "newsletter.semianalysis.com"
COOKIE_ENV_KEY = "SUBSTACK_COOKIE"
# 自定义域名下登录会话叫 connect.sid，*.substack.com 下叫 substack.sid
SESSION_COOKIE_NAMES = ("connect.sid", "substack.sid")

# 未登录/无权限时 Substack 在正文后渲染的付费墙块；订阅者看到的完整页面里没有它。
# 注意 `paywall-jump` 在订阅者的全文里也有，不能当截断信号。
PAYWALL_MARKER = 'data-testid="paywall"'
CONTENT_MARKER = 'class="available-content'

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
_HOSTNAME_PATTERN = re.compile(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
# Clash / Surge / sing-box 等代理的 fake-IP 模式把所有域名解析到 198.18.0.0/15
# （RFC 2544 基准测试段），真实流量由代理接管。服务器上这个段没有任何服务，放行它
# 不增加风险；而在开着这类代理的机器上，域名检查本来也拿不到真实地址。
_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
REQUEST_TIMEOUT_SECONDS = 30.0

Resolver = Callable[[str, int], Iterable[str]]


class SubstackError(Exception):
    """带错误码的用户可读错误；code 供前端分支处理（如弹出 cookie 输入框）。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FetchedArticle:
    url: str
    slug: str
    title: str
    html: str


@dataclass(frozen=True)
class ArchivePost:
    title: str
    subtitle: str
    slug: str
    url: str
    post_date: str
    is_paid: bool
    cover_image: Optional[str]
    wordcount: Optional[int]
    # 文章开头一段（列表接口自带，免费预览部分），用来生成中文摘要和搜索
    excerpt: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_article_url(url: str) -> str:
    """补全协议、统一成 https，去掉分享链接常带的 query/fragment 和末尾斜杠。"""
    value = (url or "").strip()
    if not value:
        raise SubstackError("INVALID_URL", "请粘贴文章链接")
    if "://" not in value:
        value = f"https://{value}"
    try:
        parsed = httpx.URL(value)
    except Exception as exc:
        raise SubstackError("INVALID_URL", f"不是有效的文章链接：{url}") from exc
    if (
        parsed.scheme not in ("http", "https")
        or not _HOSTNAME_PATTERN.fullmatch(parsed.raw_host.decode("ascii", errors="replace"))
    ):
        raise SubstackError("INVALID_URL", f"不是有效的文章链接：{url}")
    path = parsed.path.rstrip("/")
    return str(httpx.URL(scheme="https", host=parsed.host, port=parsed.port, path=path or "/"))


def article_key(url: Optional[str]) -> Optional[str]:
    """比对「是不是同一篇文章」用的键：小写域名 + 去掉末尾斜杠的路径。"""
    if not url:
        return None
    try:
        parsed = httpx.URL(url.strip())
    except Exception:
        return None
    if not parsed.host:
        return None
    return f"{parsed.host.lower()}{parsed.path.rstrip('/')}"


def extract_session_cookie(raw: str, domain: str = DEFAULT_COOKIE_DOMAIN) -> Optional[str]:
    """从粘贴内容里挑出登录会话那一项，返回 `name=value`。

    接受整行请求头（可带 `cookie:` 前缀）、单个 `name=value` 或裸值。统计、
    Cloudflare 等其余 cookie 很快过期且与登录无关，一律丢掉。
    """
    text = (raw or "").strip().strip("'\"")
    if text.lower().startswith("cookie:"):
        text = text[len("cookie:"):].strip()
    if not text:
        return None
    if "=" not in text and ";" not in text and not any(ch.isspace() for ch in text):
        name = "substack.sid" if domain.lower().endswith(".substack.com") else "connect.sid"
        return f"{name}={text}"
    for part in text.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name.strip() in SESSION_COOKIE_NAMES and value.strip():
            return f"{name.strip()}={value.strip()}"
    return None


class SubstackCookieStore:
    """订阅 cookie 的读写。

    读取优先级：网页上保存的文件 → 现读 .env → 环境变量。systemd 只在启动时
    载入 .env，若只读环境变量，改完 .env 还得重启服务才生效。
    """

    def __init__(
        self,
        cookie_file: Path,
        env_file: Optional[Path] = None,
        domain: str = DEFAULT_COOKIE_DOMAIN,
    ):
        self.cookie_file = Path(cookie_file)
        self.env_file = Path(env_file) if env_file else None
        self.domain = domain.lower()

    def load(self) -> str:
        candidates = [self._read_cookie_file(), self._read_env_file(), os.environ.get(COOKIE_ENV_KEY)]
        for raw in candidates:
            cookie = extract_session_cookie(raw or "", self.domain)
            if cookie:
                return cookie
        return ""

    def is_configured(self) -> bool:
        return bool(self.load())

    def save(self, raw: str) -> None:
        cookie = extract_session_cookie(raw, self.domain)
        if not cookie:
            raise SubstackError(
                "INVALID_COOKIE",
                "没找到登录 cookie：请复制请求头里包含 connect.sid（或 substack.sid）的那一整行",
            )
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.cookie_file.with_name(self.cookie_file.name + ".tmp")
        tmp_path.write_text(cookie, encoding="utf-8")
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass
        os.replace(tmp_path, self.cookie_file)

    def _read_cookie_file(self) -> Optional[str]:
        try:
            return self.cookie_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def _read_env_file(self) -> Optional[str]:
        if not self.env_file or not self.env_file.is_file():
            return None
        return dotenv_values(self.env_file).get(COOKIE_ENV_KEY)


def _resolve_host(host: str, port: int) -> List[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def _is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if ip in _FAKE_IP_NETWORK:
        return True
    return ip.is_global and not ip.is_multicast


def _extract_title(soup: BeautifulSoup) -> str:
    for candidate in (
        soup.select_one("h1.post-title"),
        soup.find("meta", attrs={"property": "og:title"}),
        soup.title,
    ):
        if candidate is None:
            continue
        text = candidate.get("content") if candidate.name == "meta" else candidate.get_text(" ", strip=True)
        if text and text.strip():
            return text.strip()
    return ""


class SubstackClient:
    def __init__(
        self,
        cookie_store: SubstackCookieStore,
        *,
        transport: Optional[httpx.BaseTransport] = None,
        resolver: Resolver = _resolve_host,
        archive_base_url: str = SEMIANALYSIS_BASE_URL,
    ):
        self.cookie_store = cookie_store
        self._transport = transport
        self._resolver = resolver
        self._archive_base_url = archive_base_url.rstrip("/")

    def fetch_article(self, url: str) -> FetchedArticle:
        final_url, html = self._get_text(
            normalize_article_url(url), accept="text/html,application/xhtml+xml"
        )
        if CONTENT_MARKER not in html:
            raise SubstackError("NOT_SUBSTACK_ARTICLE", "这个链接不是 Substack 文章页（没找到正文）")
        host = httpx.URL(final_url).host.lower()
        if PAYWALL_MARKER in html:
            raise self._paywall_error(host)

        slug = httpx.URL(final_url).path.rstrip("/").rsplit("/", 1)[-1] or host
        title = _extract_title(BeautifulSoup(html, "lxml")) or slug
        return FetchedArticle(url=final_url, slug=slug, title=title, html=html)

    def list_archive(self, *, offset: int = 0, limit: int = 24, search: str = "") -> List[ArchivePost]:
        params = {"sort": "new", "offset": offset, "limit": limit}
        if search.strip():
            params["search"] = search.strip()
        _, body = self._get_text(
            f"{self._archive_base_url}/api/v1/archive?{urlencode(params)}",
            accept="application/json",
        )
        try:
            items = json.loads(body)
        except ValueError as exc:
            raise SubstackError("UPSTREAM_ERROR", "文章列表返回的数据格式异常") from exc
        if not isinstance(items, list):
            raise SubstackError("UPSTREAM_ERROR", "文章列表返回的数据格式异常")
        return [self._to_archive_post(item) for item in items if isinstance(item, dict) and item.get("slug")]

    def _to_archive_post(self, item: dict) -> ArchivePost:
        slug = str(item["slug"])
        wordcount = item.get("wordcount")
        return ArchivePost(
            title=str(item.get("title") or slug),
            subtitle=str(item.get("subtitle") or item.get("description") or ""),
            slug=slug,
            url=str(item.get("canonical_url") or f"{self._archive_base_url}/p/{slug}"),
            post_date=str(item.get("post_date") or ""),
            is_paid=item.get("audience") == "only_paid",
            cover_image=item.get("cover_image") or None,
            wordcount=wordcount if isinstance(wordcount, int) else None,
            excerpt=str(item.get("truncated_body_text") or ""),
        )

    def _paywall_error(self, host: str) -> SubstackError:
        if host != self.cookie_store.domain:
            return SubstackError(
                "PAYWALLED",
                f"这是付费文章，目前只能用订阅 cookie 下载 {self.cookie_store.domain} 的付费文章",
            )
        if self.cookie_store.is_configured():
            return SubstackError("COOKIE_EXPIRED", "订阅 cookie 已失效，请重新复制一份填进来")
        return SubstackError("COOKIE_MISSING", "这是付费文章，需要先填写订阅 cookie")

    def _check_url(self, url: str) -> httpx.URL:
        try:
            parsed = httpx.URL(url)
        except Exception as exc:
            raise SubstackError("INVALID_URL", f"不是有效的链接：{url}") from exc
        if parsed.scheme != "https" or not parsed.host:
            raise SubstackError("BLOCKED_URL", "只能导入 https 开头的公网文章链接")
        if parsed.port not in (None, 443):
            raise SubstackError("BLOCKED_URL", "只能导入 https 开头的公网文章链接")
        try:
            addresses = list(self._resolver(parsed.host, 443))
        except OSError as exc:
            raise SubstackError("UPSTREAM_ERROR", f"找不到这个网站：{parsed.host}") from exc
        if not addresses or not all(_is_public_address(address) for address in addresses):
            raise SubstackError("BLOCKED_URL", "只能导入 https 开头的公网文章链接")
        return parsed

    def _get_text(self, url: str, *, accept: str) -> Tuple[str, str]:
        """逐跳校验地发 GET，返回 (最终 URL, 响应文本)。"""
        current = url
        with httpx.Client(
            transport=self._transport,
            trust_env=False,  # .env 里的 HTTP(S)_PROXY 可能早已失效，直连
            follow_redirects=False,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                parsed = self._check_url(current)
                headers = {
                    "User-Agent": USER_AGENT,
                    "Accept": accept,
                    "Accept-Language": "en-US,en;q=0.9",
                }
                if parsed.host.lower() == self.cookie_store.domain:
                    cookie = self.cookie_store.load()
                    if cookie:
                        headers["Cookie"] = cookie
                try:
                    with client.stream("GET", parsed, headers=headers) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise SubstackError("UPSTREAM_ERROR", "网站返回了无效的跳转")
                            current = str(parsed.join(location))
                            continue
                        if response.status_code == 404:
                            raise SubstackError("ARTICLE_NOT_FOUND", "文章不存在（404），请检查链接")
                        if response.status_code >= 400:
                            raise SubstackError(
                                "UPSTREAM_ERROR", f"网站返回错误 {response.status_code}，请稍后重试"
                            )
                        body = self._read_limited(response)
                        return str(parsed), body.decode(response.charset_encoding or "utf-8", errors="replace")
                except httpx.HTTPError as exc:
                    raise SubstackError("UPSTREAM_ERROR", f"下载失败：{exc}") from exc
        raise SubstackError("UPSTREAM_ERROR", "跳转次数过多，已放弃下载")

    @staticmethod
    def _read_limited(response: httpx.Response) -> bytes:
        chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise SubstackError("TOO_LARGE", "页面超过 20 MB，已放弃下载")
            chunks.append(chunk)
        return b"".join(chunks)
