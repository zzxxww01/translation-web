import json

import httpx
import pytest

from src.services import substack_service
from src.services.substack_service import (
    SubstackClient,
    SubstackCookieStore,
    SubstackError,
    article_key,
    extract_session_cookie,
    normalize_article_url,
)

COOKIE_DOMAIN = "newsletter.semianalysis.com"
ARTICLE_HTML = (
    "<html><head><title>Demo - by Someone</title></head><body>"
    '<h1 class="post-title">Demo Title</h1>'
    '<div class="available-content"><p>full body</p><div class="paywall-jump"></div></div>'
    "</body></html>"
)
PAYWALLED_HTML = (
    '<html><body><div class="available-content"><p>preview</p></div>'
    '<div class="paywall" data-testid="paywall"></div></body></html>'
)


def _public_resolver(host, port):
    return ["93.184.216.34"]


def _client(tmp_path, handler, *, resolver=_public_resolver, cookie=None):
    store = SubstackCookieStore(cookie_file=tmp_path / "cookie.txt", domain=COOKIE_DOMAIN)
    if cookie:
        store.save(cookie)
    return SubstackClient(store, transport=httpx.MockTransport(handler), resolver=resolver)


@pytest.fixture(autouse=True)
def _no_env_cookie(monkeypatch):
    monkeypatch.delenv("SUBSTACK_COOKIE", raising=False)


# ---------- URL 与 cookie 解析 ----------


def test_normalize_article_url_adds_https_and_drops_tracking():
    assert (
        normalize_article_url(" newsletter.semianalysis.com/p/demo/?utm_source=x#top ")
        == "https://newsletter.semianalysis.com/p/demo"
    )
    assert normalize_article_url("http://x.substack.com/p/a") == "https://x.substack.com/p/a"


@pytest.mark.parametrize("bad", ["", "   ", "ftp://example.com/p/a", "not a url at all/../"])
def test_normalize_article_url_rejects_invalid(bad):
    with pytest.raises(SubstackError) as exc_info:
        normalize_article_url(bad)
    assert exc_info.value.code in {"INVALID_URL", "BLOCKED_URL"}


def test_article_key_ignores_case_and_trailing_slash():
    assert article_key("https://Newsletter.SemiAnalysis.com/p/demo/") == article_key(
        "https://newsletter.semianalysis.com/p/demo"
    )
    assert article_key(None) is None


def test_extract_session_cookie_keeps_only_session_entry():
    raw = "cookie: _ga=GA1; connect.sid=s%3Aabc.def; __cf_bm=zzz; ajs_anonymous_id=%22x%22"
    assert extract_session_cookie(raw, COOKIE_DOMAIN) == "connect.sid=s%3Aabc.def"
    assert extract_session_cookie("substack.sid=v1", COOKIE_DOMAIN) == "substack.sid=v1"


def test_extract_session_cookie_names_bare_value_by_domain():
    assert extract_session_cookie("s%3Abare", COOKIE_DOMAIN) == "connect.sid=s%3Abare"
    assert extract_session_cookie("s%3Abare", "x.substack.com") == "substack.sid=s%3Abare"


def test_extract_session_cookie_returns_none_without_session_cookie():
    assert extract_session_cookie("_ga=1; __cf_bm=2", COOKIE_DOMAIN) is None
    assert extract_session_cookie("", COOKIE_DOMAIN) is None


def test_cookie_store_prefers_saved_file_then_env_file_then_environ(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    store = SubstackCookieStore(cookie_file=tmp_path / "c.txt", env_file=env_file, domain=COOKIE_DOMAIN)
    assert store.load() == ""
    assert store.is_configured() is False

    monkeypatch.setenv("SUBSTACK_COOKIE", "connect.sid=from-environ")
    assert store.load() == "connect.sid=from-environ"

    env_file.write_text("OTHER=1\nSUBSTACK_COOKIE='_ga=1; connect.sid=from-env-file'\n", encoding="utf-8")
    assert store.load() == "connect.sid=from-env-file"

    store.save("_ga=1; connect.sid=from-web; __cf_bm=2")
    assert store.load() == "connect.sid=from-web"
    assert (tmp_path / "c.txt").read_text(encoding="utf-8") == "connect.sid=from-web"


def test_cookie_store_save_rejects_paste_without_session_cookie(tmp_path):
    store = SubstackCookieStore(cookie_file=tmp_path / "c.txt", domain=COOKIE_DOMAIN)
    with pytest.raises(SubstackError) as exc_info:
        store.save("_ga=1; __cf_bm=2")
    assert exc_info.value.code == "INVALID_COOKIE"
    assert not (tmp_path / "c.txt").exists()


# ---------- 下载文章 ----------


def test_fetch_article_returns_full_page_and_title(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html=ARTICLE_HTML))
    article = client.fetch_article("https://newsletter.semianalysis.com/p/demo?utm=1")
    assert article.url == "https://newsletter.semianalysis.com/p/demo"
    assert article.slug == "demo"
    assert article.title == "Demo Title"
    assert article.html == ARTICLE_HTML


def test_cookie_is_sent_only_to_cookie_domain(tmp_path):
    seen = {}

    def handler(request):
        seen[request.url.host] = request.headers.get("cookie")
        return httpx.Response(200, html=ARTICLE_HTML)

    client = _client(tmp_path, handler, cookie="connect.sid=secret")
    client.fetch_article("https://newsletter.semianalysis.com/p/demo")
    client.fetch_article("https://other.substack.com/p/demo")
    assert seen == {"newsletter.semianalysis.com": "connect.sid=secret", "other.substack.com": None}


def test_cookie_is_not_forwarded_across_redirect_to_other_host(tmp_path):
    seen = []

    def handler(request):
        seen.append((request.url.host, request.headers.get("cookie")))
        if request.url.host == COOKIE_DOMAIN:
            return httpx.Response(302, headers={"location": "https://elsewhere.example/p/demo"})
        return httpx.Response(200, html=ARTICLE_HTML)

    client = _client(tmp_path, handler, cookie="connect.sid=secret")
    article = client.fetch_article("https://newsletter.semianalysis.com/p/demo")
    assert article.url == "https://elsewhere.example/p/demo"
    assert seen == [(COOKIE_DOMAIN, "connect.sid=secret"), ("elsewhere.example", None)]


def test_paywalled_page_without_cookie_asks_for_cookie(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html=PAYWALLED_HTML))
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://newsletter.semianalysis.com/p/paid")
    assert exc_info.value.code == "COOKIE_MISSING"


def test_paywalled_page_with_cookie_reports_expired_cookie(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html=PAYWALLED_HTML), cookie="connect.sid=old")
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://newsletter.semianalysis.com/p/paid")
    assert exc_info.value.code == "COOKIE_EXPIRED"


def test_paywalled_page_on_other_publication_is_not_a_cookie_problem(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html=PAYWALLED_HTML), cookie="connect.sid=ok")
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://other.substack.com/p/paid")
    assert exc_info.value.code == "PAYWALLED"


def test_non_substack_page_is_rejected(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html="<html><body>hi</body></html>"))
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://example.com/p/demo")
    assert exc_info.value.code == "NOT_SUBSTACK_ARTICLE"


@pytest.mark.parametrize(
    "status_code, code",
    [(404, "ARTICLE_NOT_FOUND"), (500, "UPSTREAM_ERROR"), (403, "UPSTREAM_ERROR")],
)
def test_http_errors_map_to_codes(tmp_path, status_code, code):
    client = _client(tmp_path, lambda request: httpx.Response(status_code))
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com/p/demo")
    assert exc_info.value.code == code


def test_network_error_maps_to_upstream_error(tmp_path):
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    client = _client(tmp_path, handler)
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com/p/demo")
    assert exc_info.value.code == "UPSTREAM_ERROR"


def test_oversized_page_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(substack_service, "MAX_RESPONSE_BYTES", 100)
    client = _client(tmp_path, lambda request: httpx.Response(200, html=ARTICLE_HTML + "x" * 200))
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com/p/demo")
    assert exc_info.value.code == "TOO_LARGE"


def test_too_many_redirects_stop(tmp_path):
    client = _client(
        tmp_path,
        lambda request: httpx.Response(302, headers={"location": "https://x.substack.com/p/loop"}),
    )
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com/p/demo")
    assert exc_info.value.code == "UPSTREAM_ERROR"


# ---------- 防止被借道访问内网 ----------


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "192.168.1.2", "169.254.169.254", "100.64.0.1", "::1", "::ffff:127.0.0.1", "fd00::1"],
)
def test_private_addresses_are_blocked_before_any_request(tmp_path, address):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, html=ARTICLE_HTML)

    client = _client(tmp_path, handler, resolver=lambda host, port: [address])
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://internal.example/p/demo")
    assert exc_info.value.code == "BLOCKED_URL"
    assert requests == []


def test_proxy_fake_ip_range_is_allowed(tmp_path):
    client = _client(
        tmp_path,
        lambda request: httpx.Response(200, html=ARTICLE_HTML),
        resolver=lambda host, port: ["198.18.0.45"],
    )
    assert client.fetch_article("https://x.substack.com/p/demo").title == "Demo Title"


def test_host_with_any_private_address_is_blocked(tmp_path):
    client = _client(
        tmp_path,
        lambda request: httpx.Response(200, html=ARTICLE_HTML),
        resolver=lambda host, port: ["93.184.216.34", "127.0.0.1"],
    )
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://mixed.example/p/demo")
    assert exc_info.value.code == "BLOCKED_URL"


def test_redirect_to_private_host_is_blocked(tmp_path):
    def resolver(host, port):
        return ["127.0.0.1"] if host == "localhost" else ["93.184.216.34"]

    requested_hosts = []

    def handler(request):
        requested_hosts.append(request.url.host)
        return httpx.Response(302, headers={"location": "https://localhost/admin"})

    client = _client(tmp_path, handler, resolver=resolver)
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com/p/demo")
    assert exc_info.value.code == "BLOCKED_URL"
    assert requested_hosts == ["x.substack.com"]


def test_non_default_port_is_blocked(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, html=ARTICLE_HTML))
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://x.substack.com:8443/p/demo")
    assert exc_info.value.code == "BLOCKED_URL"


def test_unresolvable_host_is_upstream_error(tmp_path):
    def resolver(host, port):
        raise OSError("no such host")

    client = _client(tmp_path, lambda request: httpx.Response(200), resolver=resolver)
    with pytest.raises(SubstackError) as exc_info:
        client.fetch_article("https://nope.example/p/demo")
    assert exc_info.value.code == "UPSTREAM_ERROR"


# ---------- 文章列表 ----------


def test_list_archive_maps_posts_and_passes_search(tmp_path):
    captured = {}
    items = [
        {
            "slug": "paid-post",
            "title": "Paid",
            "subtitle": "Sub",
            "canonical_url": "https://newsletter.semianalysis.com/p/paid-post",
            "post_date": "2026-10-23T19:06:44.981Z",
            "audience": "only_paid",
            "cover_image": "https://img/1.png",
            "wordcount": 3308,
        },
        {"slug": "free-post", "title": "Free", "audience": "everyone", "description": "Desc"},
        {"title": "no slug is skipped"},
    ]

    def handler(request):
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=items)

    client = _client(tmp_path, handler)
    posts = client.list_archive(offset=24, limit=12, search=" TSMC ")
    assert captured == {"sort": "new", "offset": "24", "limit": "12", "search": "TSMC"}
    assert [p.slug for p in posts] == ["paid-post", "free-post"]
    assert posts[0].is_paid is True and posts[0].wordcount == 3308
    assert posts[1].is_paid is False
    assert posts[1].url == "https://newsletter.semianalysis.com/p/free-post"
    assert posts[1].subtitle == "Desc"
    assert posts[1].cover_image is None


def test_list_archive_rejects_malformed_payload(tmp_path):
    client = _client(tmp_path, lambda request: httpx.Response(200, text=json.dumps({"error": 1})))
    with pytest.raises(SubstackError) as exc_info:
        client.list_archive()
    assert exc_info.value.code == "UPSTREAM_ERROR"
