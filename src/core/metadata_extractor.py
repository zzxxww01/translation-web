"""
Metadata Extractor — extract article metadata (authors, dates, subtitles, etc.)
from parsed HTML (BeautifulSoup) objects.

Extracted from parser.py to follow the Single Responsibility Principle.
"""

from typing import List, Optional

from bs4 import BeautifulSoup

from .models import ArticleMetadata


class MetadataExtractor:
    """Extract article metadata from a BeautifulSoup document."""

    # 元信息容器选择器（Substack 特定）
    METADATA_SELECTORS = [
        'div.post-header',
        'div.pencraft.pc-display-flex',
        'div.frontend-pencraft-Box-module__reset',
    ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, soup: BeautifulSoup) -> Optional[ArticleMetadata]:
        """
        提取文章元信息（作者、日期等）

        Returns:
            ArticleMetadata if any meaningful field was found, else None.
        """
        metadata = ArticleMetadata()

        authors = self._extract_authors(soup)
        if authors:
            metadata.authors = authors

        date = self._extract_date(soup)
        if date:
            metadata.published_date = date

        subtitle = self._extract_subtitle(soup)
        if subtitle:
            metadata.subtitle = subtitle

        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            metadata.original_url = og_url['content']

        site_name = soup.find('meta', property='og:site_name')
        if site_name and site_name.get('content'):
            metadata.publication = site_name['content']

        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            metadata.cover_image = og_image['content']

        return metadata if any([
            metadata.authors, metadata.published_date,
            metadata.subtitle, metadata.original_url
        ]) else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_authors(self, soup: BeautifulSoup) -> List[str]:
        """提取作者列表"""
        authors: List[str] = []

        author_selectors = [
            'a.frontend-pencraft-Text-module__decoration-hover-underline--BEYAn',
            'a[data-testid="post-author-link"]',
            'span.author-name',
            'a.author',
            'meta[name="author"]',
        ]

        for selector in author_selectors:
            if selector.startswith('meta'):
                meta = soup.find('meta', attrs={'name': 'author'})
                if meta and meta.get('content'):
                    authors.append(meta['content'])
                    break
            else:
                elements = soup.select(selector)
                for el in elements:
                    name = el.get_text().strip()
                    if name and name not in authors:
                        authors.append(name)
                if authors:
                    break

        return authors

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """提取发布日期"""
        time_tag = soup.find('time')
        if time_tag:
            return time_tag.get('datetime') or time_tag.get_text().strip()

        date_meta = soup.find('meta', property='article:published_time')
        if date_meta and date_meta.get('content'):
            return date_meta['content']

        return None

    def _extract_subtitle(self, soup: BeautifulSoup) -> Optional[str]:
        """提取副标题"""
        subtitle_selectors = [
            'h3.subtitle',
            'p.subtitle',
            'div.subtitle',
        ]

        for selector in subtitle_selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text().strip()

        return None
