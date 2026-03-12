from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .utils import collapse_ws, join_markdown_authors


def prepare_body(root: Tag, html_path: Path) -> Tag:
    _remove_noise(root)
    _rewrite_digest_embeds(root)
    _rewrite_figures(root, html_path)
    _rewrite_fake_bullets(root)
    _rewrite_heading_anchors(root)
    _normalize_links(root)
    _downgrade_headings(root)
    return root


def _remove_noise(root: Tag) -> None:
    for selector in [
        "script",
        "style",
        "iframe",
        "button",
        "svg",
        ".image-link-expand",
        ".header-anchor-parent",
        ".available-content > .visibility-check",
    ]:
        for node in root.select(selector):
            node.decompose()


def _rewrite_digest_embeds(root: Tag) -> None:
    soup = root if isinstance(root, BeautifulSoup) else root.find_parent()
    for embed in list(root.select('div[class*="digestPostEmbed"]')):
        link = embed.select_one('a[href^="http"]')
        title_node = embed.select_one("h4, h3")
        meta_nodes = embed.select("div.meta-EgzBVA")

        title = collapse_ws(title_node.get_text(" ", strip=True) if title_node else "")
        href = collapse_ws(link.get("href") if link else "")
        meta_parts = []
        if meta_nodes:
            authors = _extract_embed_authors(meta_nodes[0])
            if authors:
                meta_parts.append(authors)
        if len(meta_nodes) > 1:
            date_text = collapse_ws(meta_nodes[1].get_text(" ", strip=True))
            if date_text:
                meta_parts.append(date_text)

        item = soup.new_tag("li")
        item["data-digest-embed"] = "1"
        if href and title:
            anchor = soup.new_tag("a", href=href)
            anchor.string = title
            item.append(anchor)
        else:
            item.append(title or embed.get_text(" ", strip=True))
        if meta_parts:
            item.append(f" - {' · '.join(meta_parts)}")
        embed.replace_with(item)

    _group_digest_embed_items(root, soup)


def _rewrite_figures(root: Tag, html_path: Path) -> None:
    soup = root if isinstance(root, BeautifulSoup) else root.find_parent()

    for container in list(root.select("div.captioned-image-container")):
        figure = container.find("figure")
        if figure:
            _replace_with_simple_figure(figure, container, soup, html_path)
        else:
            container.decompose()

    for figure in list(root.find_all("figure")):
        if figure.find_parent("div", class_="captioned-image-container"):
            continue
        _replace_with_simple_figure(figure, figure, soup, html_path)


def _replace_with_simple_figure(
    source_figure: Tag,
    replace_node: Tag,
    soup: Tag,
    html_path: Path,
) -> None:
    image = source_figure.find("img")
    if not image:
        replace_node.decompose()
        return

    normalized_src = _preferred_image_source(image, html_path)
    if not normalized_src:
        replace_node.decompose()
        return

    new_figure = soup.new_tag("figure")
    new_image = copy.deepcopy(image)
    new_image.attrs = {
        key: value for key, value in new_image.attrs.items() if key in {"alt", "title"}
    }
    new_image["src"] = normalized_src
    if "alt" in new_image.attrs:
        cleaned_alt = _clean_image_text(new_image["alt"])
        if cleaned_alt:
            new_image["alt"] = cleaned_alt
        else:
            new_image.attrs.pop("alt", None)
    if "title" in new_image.attrs:
        cleaned_title = _clean_image_text(new_image["title"])
        if not cleaned_title or cleaned_title == new_image.attrs.get("alt", ""):
            new_image.attrs.pop("title", None)
        else:
            new_image["title"] = cleaned_title
    new_figure.append(new_image)

    caption = source_figure.find("figcaption")
    if caption:
        new_caption = copy.deepcopy(caption)
        for node in new_caption.select("button, svg"):
            node.decompose()
        if collapse_ws(new_caption.get_text(" ", strip=True)):
            new_figure.append(new_caption)

    replace_node.replace_with(new_figure)


def _rewrite_heading_anchors(root: Tag) -> None:
    for heading in root.select(".header-anchor-post"):
        for child in list(heading.select(".header-anchor-parent, button, svg")):
            child.decompose()
        heading.string = collapse_ws(heading.get_text(" ", strip=True))


def _normalize_links(root: Tag) -> None:
    for link in root.find_all("a"):
        href = collapse_ws(link.get("href"))
        if not href:
            link.unwrap()
            continue
        link.attrs = {"href": href}


def _downgrade_headings(root: Tag) -> None:
    for node in root.find_all("h1"):
        node.name = "h2"


_MIDDLE_DOT = "\u00b7"


def _rewrite_fake_bullets(root: Tag) -> None:
    soup = root if isinstance(root, BeautifulSoup) else root.find_parent()
    for blockquote in list(root.find_all("blockquote")):
        ps = blockquote.find_all("p", recursive=False)
        bullet_ids = {id(p) for p in ps if p.get_text().lstrip().startswith(_MIDDLE_DOT)}
        if len(bullet_ids) < 2:
            continue

        current_group: list[Tag] = []
        for child in list(blockquote.children):
            if isinstance(child, Tag) and child.name == "p" and id(child) in bullet_ids:
                current_group.append(child)
            elif isinstance(child, Tag) or (not isinstance(child, Tag) and str(child).strip()):
                if len(current_group) >= 2:
                    _wrap_fake_bullet_group(current_group, soup)
                current_group = []
        if len(current_group) >= 2:
            _wrap_fake_bullet_group(current_group, soup)


def _wrap_fake_bullet_group(paragraphs: list[Tag], soup: Tag) -> None:
    ul = soup.new_tag("ul")
    paragraphs[0].insert_before(ul)
    for paragraph in paragraphs:
        li = soup.new_tag("li")
        _strip_bullet_marker(paragraph)
        for child in list(paragraph.children):
            child.extract()
            li.append(child)
        paragraph.extract()
        ul.append(li)


def _strip_bullet_marker(paragraph: Tag) -> None:
    for child in list(paragraph.children):
        if isinstance(child, Tag):
            text = child.get_text()
            if _MIDDLE_DOT in text:
                for sub in list(child.children):
                    if not isinstance(sub, Tag) and _MIDDLE_DOT in str(sub):
                        cleaned = str(sub).replace(_MIDDLE_DOT, "", 1).lstrip()
                        if cleaned:
                            sub.replace_with(cleaned)
                        else:
                            sub.extract()
                        break
                if not child.get_text(strip=True):
                    child.extract()
                return
            if text.strip():
                return
        else:
            text = str(child)
            if _MIDDLE_DOT in text:
                cleaned = text.replace(_MIDDLE_DOT, "", 1).lstrip()
                if cleaned:
                    child.replace_with(cleaned)
                else:
                    child.extract()
                return
            if text.strip():
                return


def _extract_embed_authors(meta_node: Tag) -> str:
    linked_names = [
        collapse_ws(link.get_text(" ", strip=True))
        for link in meta_node.select("a[href]")
        if collapse_ws(link.get_text(" ", strip=True))
    ]
    text = collapse_ws(meta_node.get_text(" ", strip=True))
    suffix = ""
    if "others" in text:
        suffix = text
        for name in linked_names:
            suffix = suffix.replace(name, "")
        suffix = collapse_ws(suffix).replace(" ,", ",").strip(", ")
    return _join_author_names_and_suffix(linked_names, suffix)


def _join_author_names_and_suffix(names: list[str], suffix: str) -> str:
    suffix = collapse_ws(suffix)
    if not suffix:
        return join_markdown_authors(names)
    if not names:
        return suffix
    if len(names) == 1:
        return f"{names[0]} {suffix}".strip()
    return f"{', '.join(names)}, {suffix}".strip()


def _group_digest_embed_items(root: Tag, soup: Tag) -> None:
    parents = {item.parent for item in root.select('li[data-digest-embed="1"]') if item.parent}
    for parent in parents:
        current_group: list[Tag] = []
        for child in list(parent.children):
            if isinstance(child, Tag) and child.name == "li" and child.get("data-digest-embed") == "1":
                current_group.append(child)
                continue
            if current_group:
                _wrap_digest_group(current_group, soup)
                current_group = []
        if current_group:
            _wrap_digest_group(current_group, soup)


def _wrap_digest_group(items: list[Tag], soup: Tag) -> None:
    wrapper = soup.new_tag("ul")
    items[0].insert_before(wrapper)
    for item in items:
        item.extract()
        item.attrs.pop("data-digest-embed", None)
        wrapper.append(item)


def _clean_image_text(text: str) -> str:
    text = collapse_ws(text)
    text = re.sub(r"\s*AI-generated content may be incorrect\.?", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+\.", ".", text)
    text = text.strip(" -\n\t")
    text = text.strip(". ")
    return collapse_ws(text)


def _preferred_image_source(image: Tag, html_path: Path) -> str:
    candidates: list[str] = []
    for attr in ("src", "data-src", "data-lazy-src"):
        value = collapse_ws(image.get(attr))
        if value:
            candidates.append(value)

    data_attrs = image.get("data-attrs")
    if data_attrs:
        try:
            payload = json.loads(data_attrs)
        except json.JSONDecodeError:
            payload = {}
        for key in ("src", "srcNoWatermark"):
            value = collapse_ws(payload.get(key))
            if value:
                candidates.append(value)

    srcset = collapse_ws(image.get("srcset"))
    if srcset:
        for part in srcset.split(","):
            token = collapse_ws(part.split(" ")[0])
            if token:
                candidates.append(token)

    for candidate in candidates:
        if candidate.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (html_path.parent / candidate).resolve()
        if resolved.exists():
            return candidate.replace("\\", "/")

    for candidate in candidates:
        if candidate.startswith(("http://", "https://")):
            return candidate

    for candidate in candidates:
        if candidate and not candidate.startswith("mailto:"):
            return candidate.replace("\\", "/")
    return ""
