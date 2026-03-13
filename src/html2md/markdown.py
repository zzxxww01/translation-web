from __future__ import annotations

import re
from typing import Match

from markdownify import MarkdownConverter

from .models import ArticleMetadata
from .utils import collapse_ws, join_markdown_authors


class SemiAnalysisMarkdownConverter(MarkdownConverter):
    def convert_a(self, el, text, parent_tags):
        href = collapse_ws(el.get("href"))
        if not href:
            return text
        if el.find("img") and not collapse_ws(el.get_text(" ", strip=True)):
            return text
        return super().convert_a(el, text, parent_tags)

    def convert_figure(self, el, text, parent_tags):
        return f"\n\n{text.strip()}\n\n"

    def convert_figcaption(self, el, text, parent_tags):
        text = text.strip()
        if not text:
            return "\n\n"
        if text.startswith("Source:"):
            return f"\n\n{text}\n\n"
        return f"\n\n*{text}*\n\n"

    def convert_img(self, el, text, parent_tags):
        # 1. 优先尝试获取懒加载原图地址
        src = collapse_ws(el.get("data-src")) or collapse_ws(el.get("data-original"))

        # 2. 如果没有，尝试解析 srcset (从图片本身或父级 picture)
        if not src:
            srcset = collapse_ws(el.get("srcset"))
            if not srcset and el.parent and el.parent.name == "picture":
                sources = el.parent.find_all("source")
                for source in sources:
                    if collapse_ws(source.get("srcset")):
                        srcset = collapse_ws(source.get("srcset"))
                        break

            if srcset:
                best_url = None
                max_width = -1
                for part in srcset.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    tokens = part.split()
                    url = tokens[0]
                    width = 0
                    if len(tokens) >= 2 and tokens[1].endswith("w"):
                        try:
                            width = int(tokens[1][:-1])
                        except ValueError:
                            pass
                    if width >= max_width:
                        max_width = width
                        best_url = url
                if best_url:
                    src = best_url

        # 3. 最后回退到普通的 src 属性
        if not src:
            src = collapse_ws(el.get("src"))

        if not src:
            return ""

        alt = collapse_ws(el.get("alt"))
        title = collapse_ws(el.get("title"))
        title_part = f' "{title}"' if title else ""
        return f"![{alt}]({src}{title_part})"


def render_markdown(body_html: str, metadata: ArticleMetadata) -> str:
    converter = SemiAnalysisMarkdownConverter(heading_style="ATX")
    body_markdown = converter.convert(body_html)
    parts: list[str] = []

    if metadata.title:
        parts.append(f"# {metadata.title}")
    if metadata.subtitle:
        parts.append(f"### {metadata.subtitle}")
    if metadata.byline_markdown:
        parts.append(f"By {metadata.byline_markdown}")
    elif metadata.authors:
        authors = [
            f"[{author.name}]({author.url})" if author.url else author.name
            for author in metadata.authors
        ]
        parts.append(f"By {join_markdown_authors(authors)}")

    meta_line = " · ".join(
        item for item in [metadata.date_text, metadata.access_text] if item
    )
    if meta_line:
        parts.append(meta_line)

    body_markdown = _postprocess_markdown(body_markdown)
    if body_markdown:
        parts.append(body_markdown)

    markdown = "\n\n".join(part.strip() for part in parts if part.strip()).strip()
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown + "\n"


def _postprocess_markdown(markdown: str) -> str:
    markdown = markdown.replace("\r\n", "\n")
    markdown = re.sub(r"<((?:https?://|mailto:)[^>]+)>", r"[\1](\1)", markdown)
    markdown = re.sub(r"<(?!https?://|mailto:)([^>\n]+)>", r"`<\1>`", markdown)
    markdown = _normalize_markdown_links(markdown)
    markdown = _linkify_bare_urls(markdown)
    markdown = _strip_punctuation_only_emphasis(markdown)
    markdown = re.sub(r"(?<=\))\s+([.,;:?])", r"\1", markdown)
    markdown = re.sub(r"(?<=\))\.([,;:])", r"\1", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"(?m)^(#+)\s+", lambda m: f"{m.group(1)} ", markdown)
    return markdown.strip()


_PROTECTED_TOKEN = "\ufff0"
_URL_TRAILING_PUNCTUATION = ".,;:!?\"'”’"
_BARE_URL_RE = re.compile(
    rf"(?P<url>(?:https?://|mailto:)[^\s<>\"{_PROTECTED_TOKEN}]+|www\.[^\s<>\"{_PROTECTED_TOKEN}]+)"
)


def _normalize_markdown_links(markdown: str) -> str:
    def fix(match: Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        trimmed = url.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = url[len(trimmed) :]
        if not trimmed:
            return match.group(0)
        return f"[{label}]({trimmed}){trailing}"

    return re.sub(r"(?<!\!)\[([^\]]+)\]\(([^)\n]+)\)", fix, markdown)


def _linkify_bare_urls(markdown: str) -> str:
    protected: list[str] = []

    def stash(match: Match[str]) -> str:
        protected.append(match.group(0))
        return f"{_PROTECTED_TOKEN}{len(protected) - 1}{_PROTECTED_TOKEN}"

    markdown = re.sub(r"!\[[^\]]*\]\([^)]+\)", stash, markdown)
    markdown = re.sub(r"(?<!\!)\[[^\]]+\]\([^)]+\)", stash, markdown)
    markdown = re.sub(r"`[^`]*`", stash, markdown)

    def replace(match: Match[str]) -> str:
        raw_url = match.group("url")
        prefix = "https://" if raw_url.startswith("www.") else ""
        trimmed = raw_url.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = raw_url[len(trimmed) :]
        if not trimmed:
            return raw_url
        return f"[{trimmed}]({prefix}{trimmed}){trailing}"

    markdown = _BARE_URL_RE.sub(replace, markdown)
    for index, value in enumerate(protected):
        markdown = markdown.replace(
            f"{_PROTECTED_TOKEN}{index}{_PROTECTED_TOKEN}", value
        )
    return markdown


def _strip_punctuation_only_emphasis(markdown: str) -> str:
    markdown = re.sub(r"\*\*([.,;:!?\"'”’]+)\*\*", r"\1", markdown)
    markdown = re.sub(r"\*([.,;:!?\"'”’]+)\*", r"\1", markdown)
    return markdown
