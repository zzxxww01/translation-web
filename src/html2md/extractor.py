from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .dom_cleanup import prepare_body
from .metadata import extract_metadata
from .models import ArticleMetadata


def extract_article(html_path: Path) -> tuple[ArticleMetadata, Tag]:
    document = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    article = document.select_one("article.newsletter-post.post")
    if article is None:
        raise ValueError(f"Could not locate article node in {html_path}")

    metadata = extract_metadata(document)

    body = article.select_one("div.available-content div.body.markup")
    if body is None:
        body = article.select_one("div.available-content")
    body_clone = BeautifulSoup(str(body), "html.parser").find() if body else None

    if body_clone is None:
        preloads_html = _extract_preloads_body_html(document)
        if preloads_html:
            body_clone = BeautifulSoup(
                f'<div class="body markup">{preloads_html}</div>',
                "html.parser",
            ).find()

    if body_clone is None:
        raise ValueError(f"Could not locate article body in {html_path}")

    return metadata, prepare_body(body_clone, html_path)


def _extract_preloads_body_html(document: BeautifulSoup) -> str | None:
    for script in document.find_all("script"):
        text = script.string or ""
        if "window._preloads" not in text:
            continue
        data = _parse_preloads_json(text)
        if data is None:
            continue
        body_html = _deep_find_str(data, "body_html")
        if body_html:
            return body_html
    return None


def _parse_preloads_json(text: str) -> dict | None:
    decoder = json.JSONDecoder()

    match = re.search(r"JSON\.parse\(", text)
    if match:
        try:
            outer_str, _ = decoder.raw_decode(text, match.end())
            return json.loads(outer_str)
        except (json.JSONDecodeError, ValueError):
            pass

    match = re.search(r"window\._preloads\s*=\s*", text)
    if match:
        try:
            data, _ = decoder.raw_decode(text, match.end())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _deep_find_str(data: object, key: str) -> str | None:
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        for child in data.values():
            result = _deep_find_str(child, key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = _deep_find_str(item, key)
            if result is not None:
                return result
    return None
