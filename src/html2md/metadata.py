from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from .models import ArticleMetadata, Author
from .utils import collapse_ws, join_markdown_authors


def extract_metadata(document: BeautifulSoup) -> ArticleMetadata:
    json_ld = _load_news_article(document)
    header = document.select_one("article.newsletter-post.post .post-header")

    title = _get_header_text(header, "h1") or _get_json_ld_value(json_ld, "headline")
    subtitle = _get_header_text(header, ".subtitle") or _get_json_ld_value(
        json_ld, "description"
    )
    authors = _extract_authors(json_ld, header)
    byline_markdown = _extract_byline_markdown(header, authors)
    date_text = _extract_date_text(json_ld, header)
    access_text = _extract_access_text(json_ld, header)
    canonical_url = (
        _get_json_ld_value(json_ld, "url")
        or _meta_content(document, "property", "og:url")
        or ""
    )
    publication = _meta_content(document, "property", "og:site_name")
    cover_image = _meta_content(document, "property", "og:image")

    return ArticleMetadata(
        title=title,
        subtitle=subtitle,
        authors=authors,
        byline_markdown=byline_markdown,
        date_text=date_text,
        access_text=access_text,
        canonical_url=canonical_url,
        publication=publication,
        cover_image=cover_image,
    )


def _load_news_article(document: BeautifulSoup) -> dict:
    for node in document.select('script[type="application/ld+json"]'):
        raw = (node.string or node.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "NewsArticle":
            return data
    return {}


def _get_json_ld_value(data: dict, key: str) -> str:
    value = data.get(key)
    return collapse_ws(value) if isinstance(value, str) else ""


def _get_header_text(header: Tag | None, selector: str) -> str:
    if not header:
        return ""
    node = header.select_one(selector)
    if not node:
        return ""
    return collapse_ws(node.get_text(" ", strip=True))


def _extract_authors(json_ld: dict, header: Tag | None) -> list[Author]:
    if header:
        authors = _extract_header_authors(header)
        if authors:
            return authors
    return _extract_json_ld_authors(json_ld)


def _extract_json_ld_authors(json_ld: dict) -> list[Author]:
    authors: list[Author] = []
    raw_authors = json_ld.get("author", [])
    if isinstance(raw_authors, dict):
        raw_authors = [raw_authors]
    for item in raw_authors:
        if not isinstance(item, dict):
            continue
        name = collapse_ws(item.get("name"))
        url = collapse_ws(item.get("url"))
        if name:
            authors.append(Author(name=name, url=url or None))
    return authors


def _extract_header_authors(header: Tag) -> list[Author]:
    authors: list[Author] = []
    author_line = _find_author_line(header)
    if not author_line:
        return authors

    seen: set[str] = set()
    for node in author_line.select("a[href]"):
        name = collapse_ws(node.get_text(" ", strip=True))
        href = collapse_ws(node.get("href"))
        if name and name not in seen:
            seen.add(name)
            authors.append(Author(name=name, url=href or None))
    return authors


def _extract_byline_markdown(header: Tag | None, authors: list[Author]) -> str:
    if not header:
        return _authors_to_markdown(authors)

    author_line = _find_author_line(header)
    if not author_line:
        return _authors_to_markdown(authors)

    parts = []
    for author in _extract_header_authors(header):
        parts.append(f"[{author.name}]({author.url})" if author.url else author.name)

    author_text = collapse_ws(author_line.get_text(" ", strip=True))
    others_match = _OTHERS_RE.search(author_text)
    if others_match:
        parts.append(others_match.group(1))

    return join_markdown_authors(parts)


def _authors_to_markdown(authors: list[Author]) -> str:
    parts = [
        f"[{author.name}]({author.url})" if author.url else author.name
        for author in authors
    ]
    return join_markdown_authors(parts)


def _find_author_line(header: Tag) -> Tag | None:
    byline_wrapper = header.select_one(".byline-wrapper")
    if not byline_wrapper:
        return None
    meta_nodes = byline_wrapper.select("div.meta-EgzBVA")
    return meta_nodes[0] if meta_nodes else None


def _extract_date_text(json_ld: dict, header: Tag | None) -> str:
    raw = collapse_ws(json_ld.get("datePublished"))
    if raw:
        try:
            return datetime.fromisoformat(raw).strftime("%b %d, %Y")
        except ValueError:
            pass

    if not header:
        return ""
    byline_wrapper = header.select_one(".byline-wrapper")
    if not byline_wrapper:
        return ""
    meta_texts = [
        collapse_ws(node.get_text(" ", strip=True))
        for node in byline_wrapper.select("div")
        if collapse_ws(node.get_text(" ", strip=True))
    ]
    for text in meta_texts:
        if "," in text and any(month in text for month in _MONTHS):
            return text
    return ""


def _extract_access_text(json_ld: dict, header: Tag | None) -> str:
    is_free = json_ld.get("isAccessibleForFree")
    if is_free is False:
        return "Paid"
    if is_free is True:
        return "Free"

    if not header:
        return ""
    byline_wrapper = header.select_one(".byline-wrapper")
    if not byline_wrapper:
        return ""
    for node in byline_wrapper.select("div"):
        text = collapse_ws(node.get_text(" ", strip=True))
        if text in {"Paid", "Free"}:
            return text
    return ""


def _meta_content(document: BeautifulSoup, attr_name: str, attr_value: str) -> str:
    node = document.find("meta", attrs={attr_name: attr_value})
    return collapse_ws(node.get("content")) if node else ""


_OTHERS_RE = re.compile(r"(\d+\s+others)")
_MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}
