from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Author:
    name: str
    url: str | None = None


@dataclass(slots=True)
class ArticleMetadata:
    title: str = ""
    subtitle: str = ""
    authors: list[Author] = field(default_factory=list)
    byline_markdown: str = ""
    date_text: str = ""
    access_text: str = ""
    canonical_url: str = ""
    publication: str = ""
    cover_image: str = ""
