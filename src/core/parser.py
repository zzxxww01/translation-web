"""
Translation Agent - HTML Parser

Parse HTML files (especially Substack/SemiAnalysis articles) into sections and paragraphs.
Delegates metadata extraction to MetadataExtractor, image handling to ImageDownloader.
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from slugify import slugify

from .models import Section, Paragraph, ElementType, InlineElement, ArticleMetadata
from .metadata_extractor import MetadataExtractor
from .image_downloader import ImageDownloader


class HTMLParser:
    """
    HTML 解析器，将 HTML 文件解析为章节和段落

    增强功能：
    - 提取内联元素（链接、强调等）
    - 提取元信息（作者、日期）
    - 优化分段（800字符，短段落合并）
    - 图片下载到本地
    """

    # Substack 文章内容的常见容器类名
    CONTENT_SELECTORS = [
        "div.body",
        "div.available-content",
        "div.post-content",
        "article",
        "div.markup",
    ]

    # 需要提取的元素类型
    CONTENT_ELEMENTS = [
        "h1",
        "h2",
        "h3",
        "h4",
        "p",
        "li",
        "blockquote",
        "pre",
        "table",
        "img",
    ]

    # 段落最大长度（优化：从500增加到800）
    MAX_PARAGRAPH_LENGTH = 800

    # 短段落阈值（低于此长度的段落可能需要合并）
    SHORT_PARAGRAPH_THRESHOLD = 150

    # 需要保留 HTML 的元素（图片、代码块等）
    PRESERVE_HTML_ELEMENTS = ["img", "pre", "code", "table"]

    def __init__(
        self,
        max_paragraph_length: int = 800,
        merge_short_paragraphs: bool = True,
        download_images: bool = True,
        images_dir: Optional[str] = None,
    ):
        """
        初始化 HTML 解析器

        Args:
            max_paragraph_length: 段落最大长度（默认800）
            merge_short_paragraphs: 是否合并短段落
            download_images: 是否下载图片到本地
            images_dir: 图片保存目录
        """
        self.max_paragraph_length = max_paragraph_length
        self.merge_short_paragraphs = merge_short_paragraphs
        self.download_images = download_images
        self.images_dir = images_dir
        self._source_dir: Optional[Path] = None
        self._base_url: Optional[str] = None

        # Delegates
        self._metadata_extractor = MetadataExtractor()
        self._image_downloader: Optional[ImageDownloader] = None

    def parse_file(
        self, file_path: str
    ) -> Tuple[str, List[Section], Optional[ArticleMetadata]]:
        """
        解析 HTML 文件

        Returns:
            Tuple[str, List[Section], Optional[ArticleMetadata]]:
                (文章标题, 章节列表, 元信息)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        self._source_dir = Path(file_path).parent

        if self.download_images and not self.images_dir:
            self.images_dir = str(Path(file_path).parent / "images")

        return self.parse_html(html_content)

    def parse_html(
        self, html_content: str, base_url: Optional[str] = None
    ) -> Tuple[str, List[Section], Optional[ArticleMetadata]]:
        """
        解析 HTML 内容

        Args:
            html_content: HTML 内容
            base_url: 基础 URL（用于解析相对链接）

        Returns:
            Tuple[str, List[Section], Optional[ArticleMetadata]]:
                (文章标题, 章节列表, 元信息)
        """
        soup = BeautifulSoup(html_content, "lxml")
        self._base_url = base_url or self._extract_base_url(soup)

        # Build image downloader for this parse run
        if self.download_images and self.images_dir:
            self._image_downloader = ImageDownloader(
                images_dir=self.images_dir,
                source_dir=self._source_dir,
                base_url=self._base_url,
            )
        else:
            self._image_downloader = None

        title, title_html = self._extract_title(soup)
        metadata = self._metadata_extractor.extract(soup)

        content = self._find_content(soup)
        if not content:
            content = soup

        elements = self._extract_elements(content)
        sections = self._split_into_sections(elements, title)

        if self.merge_short_paragraphs:
            sections = self._merge_short_paragraphs(sections)

        return title, sections, metadata

    def _extract_base_url(self, soup: BeautifulSoup) -> Optional[str]:
        """从 HTML 中提取基础 URL"""
        # 尝试从 og:url 获取
        og_url = soup.find("meta", property="og:url")
        if og_url and og_url.get("content"):
            return og_url["content"]

        # 尝试从 canonical link 获取
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            return canonical["href"]

        return None

    def _extract_title(self, soup: BeautifulSoup) -> Tuple[str, Optional[str]]:
        """
        Extract article title.

        Returns:
            Tuple[str, Optional[str]]: (title text, raw HTML if available)
        """
        title_html = None

        # Prefer the first h1 with non-empty text
        for h1 in soup.find_all("h1"):
            text = h1.get_text().strip()
            if text:
                title_html = str(h1)
                return text, title_html

        # Fallback to <title>
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text().strip(), None

        # Fallback to og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip(), None

        return "Untitled", None

    def _find_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """找到文章主体内容容器"""
        for selector in self.CONTENT_SELECTORS:
            if "." in selector:
                tag, class_name = selector.split(".")
                content = soup.find(tag, class_=class_name)
            else:
                content = soup.find(selector)
            if content:
                return content
        return None

    def _extract_elements(
        self, content: Tag
    ) -> List[Tuple[str, str, str, Optional[List[InlineElement]]]]:
        """
        提取所有内容元素

        Returns:
            List[Tuple[str, str, str, Optional[List[InlineElement]]]]:
                [(element_type, text, html, inline_elements), ...]
        """
        elements = []

        for el in content.find_all(self.CONTENT_ELEMENTS):
            # 跳过嵌套元素（如 li 中的 p）
            if el.find_parent(self.CONTENT_ELEMENTS):
                continue

            el_type = el.name

            # 特殊处理图片
            if el_type == "img":
                html = str(el)
                src = el.get("src", "")
                if not src:
                    continue

                # 委托 ImageDownloader 处理
                if self._image_downloader:
                    local_path = self._image_downloader.download(src)
                    if local_path:
                        src = local_path
                        el["src"] = local_path
                        if el.has_attr("srcset"):
                            del el["srcset"]

                html = str(el)
                elements.append(("img", src, html, None))
                continue

            text = el.get_text().strip()
            html = str(el)

            # 跳过空元素
            if not text:
                continue

            # 跳过导航、页脚等非内容元素
            if self._is_non_content(el):
                continue

            # 提取内联元素（链接、强调等）
            inline_elements = self._extract_inline_elements(el, text)

            elements.append((el_type, text, html, inline_elements))

        return elements

    def _extract_inline_elements(
        self, el: Tag, text: str
    ) -> Optional[List[InlineElement]]:
        """
        提取元素中的内联格式（链接、强调等）

        Args:
            el: HTML 元素
            text: 元素的纯文本内容

        Returns:
            Optional[List[InlineElement]]: 内联元素列表
        """
        inline_elements = []

        # 提取链接
        for link in el.find_all("a"):
            href = link.get("href", "")
            link_text = link.get_text().strip()
            title = link.get("title", "")

            if not link_text or not href:
                continue

            # 解析相对 URL
            if self._base_url and not href.startswith(("http://", "https://", "#")):
                href = urljoin(self._base_url, href)

            # 找到链接文本在原文中的位置
            start = text.find(link_text)
            if start >= 0:
                inline_elements.append(
                    InlineElement(
                        type="link",
                        text=link_text,
                        start=start,
                        end=start + len(link_text),
                        href=href,
                        title=title if title else None,
                    )
                )

        # 提取强调（<strong>, <b>）
        for strong in el.find_all(["strong", "b"]):
            strong_text = strong.get_text().strip()
            if not strong_text:
                continue
            start = text.find(strong_text)
            if start >= 0:
                inline_elements.append(
                    InlineElement(
                        type="strong",
                        text=strong_text,
                        start=start,
                        end=start + len(strong_text),
                    )
                )

        # 提取斜体（<em>, <i>）
        for em in el.find_all(["em", "i"]):
            em_text = em.get_text().strip()
            if not em_text:
                continue
            start = text.find(em_text)
            if start >= 0:
                inline_elements.append(
                    InlineElement(
                        type="em", text=em_text, start=start, end=start + len(em_text)
                    )
                )

        # 提取行内代码（<code>）
        for code in el.find_all("code"):
            # 跳过代码块中的 code（父元素是 pre）
            if code.find_parent("pre"):
                continue
            code_text = code.get_text().strip()
            if not code_text:
                continue
            start = text.find(code_text)
            if start >= 0:
                inline_elements.append(
                    InlineElement(
                        type="code",
                        text=code_text,
                        start=start,
                        end=start + len(code_text),
                    )
                )

        # 按位置排序
        inline_elements.sort(key=lambda x: x.start)

        return inline_elements if inline_elements else None

    def _is_non_content(self, el: Tag) -> bool:
        """判断是否为非内容元素（导航、页脚等）"""
        # 检查父元素的类名
        for parent in el.parents:
            if parent.name in ["nav", "footer", "header", "aside"]:
                return True
            classes = parent.get("class", [])
            if any(
                c in str(classes).lower()
                for c in ["nav", "footer", "header", "menu", "sidebar"]
            ):
                return True
        return False

    def _split_into_sections(
        self,
        elements: List[Tuple[str, str, str, Optional[List[InlineElement]]]],
        title: str,
    ) -> List[Section]:
        """按 H2 分割成章节"""
        sections = []
        current_section = None
        paragraph_counter = 0

        for el_type, text, html, inline_elements in elements:
            # 遇到 H2，创建新章节
            if el_type == "h2":
                if current_section:
                    sections.append(current_section)

                section_id = f"{len(sections):02d}-{slugify(text[:30])}"
                current_section = Section(
                    section_id=section_id,
                    title=text,
                    title_source=html,  # 保存原始标题HTML
                    paragraphs=[],
                )
                paragraph_counter = 0
                continue

            # 如果还没有章节，创建一个"引言"章节
            if current_section is None:
                current_section = Section(
                    section_id="00-intro", title="Introduction", paragraphs=[]
                )

            # 处理段落
            paragraphs = self._process_paragraph(
                el_type, text, html, paragraph_counter, inline_elements
            )

            for p in paragraphs:
                current_section.paragraphs.append(p)
                paragraph_counter += 1

        # 添加最后一个章节
        if current_section and current_section.paragraphs:
            sections.append(current_section)

        return sections

    def _process_paragraph(
        self,
        el_type: str,
        text: str,
        html: str,
        start_index: int,
        inline_elements: Optional[List[InlineElement]] = None,
    ) -> List[Paragraph]:
        """
        处理段落，如果太长则按句子拆分

        Returns:
            List[Paragraph]: 段落列表（可能是拆分后的多个段落）
        """
        element_type = self._get_element_type(el_type)

        # 图片和表格不需要拆分，直接返回
        if element_type in [ElementType.IMAGE, ElementType.TABLE]:
            return [
                Paragraph(
                    id=f"p{start_index:03d}",
                    index=start_index,
                    source=text,
                    source_html=html,
                    element_type=element_type,
                )
            ]

        # 如果段落不太长，直接返回（包含内联元素）
        if len(text) <= self.max_paragraph_length:
            return [
                Paragraph(
                    id=f"p{start_index:03d}",
                    index=start_index,
                    source=text,
                    source_html=html,
                    element_type=element_type,
                    inline_elements=inline_elements,
                )
            ]

        # 按句子拆分长段落
        sentences = self._split_sentences(text)
        paragraphs = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            if (
                current_length + len(sentence) > self.max_paragraph_length
                and current_chunk
            ):
                # 保存当前块
                chunk_text = " ".join(current_chunk)
                # 提取属于当前块的内联元素
                chunk_inline = (
                    self._extract_chunk_inline_elements(inline_elements, chunk_text)
                    if inline_elements
                    else None
                )

                paragraphs.append(
                    Paragraph(
                        id=f"p{start_index + len(paragraphs):03d}",
                        index=start_index + len(paragraphs),
                        source=chunk_text,
                        source_html=None,  # 拆分后不保留原始 HTML
                        element_type=element_type,
                        inline_elements=chunk_inline,
                    )
                )
                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_length += len(sentence)

        # 保存最后一块
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_inline = (
                self._extract_chunk_inline_elements(inline_elements, chunk_text)
                if inline_elements
                else None
            )

            paragraphs.append(
                Paragraph(
                    id=f"p{start_index + len(paragraphs):03d}",
                    index=start_index + len(paragraphs),
                    source=chunk_text,
                    source_html=None,
                    element_type=element_type,
                    inline_elements=chunk_inline,
                )
            )

        return paragraphs

    def _extract_chunk_inline_elements(
        self, inline_elements: List[InlineElement], chunk_text: str
    ) -> Optional[List[InlineElement]]:
        """
        提取属于特定文本块的内联元素

        Args:
            inline_elements: 原始内联元素列表
            chunk_text: 当前块的文本

        Returns:
            属于当前块的内联元素列表
        """
        if not inline_elements:
            return None

        chunk_inline = []
        for el in inline_elements:
            # 检查内联元素的文本是否在当前块中
            if el.text in chunk_text:
                # 重新计算在块中的位置
                new_start = chunk_text.find(el.text)
                if new_start >= 0:
                    chunk_inline.append(
                        InlineElement(
                            type=el.type,
                            text=el.text,
                            start=new_start,
                            end=new_start + len(el.text),
                            href=el.href,
                            title=el.title,
                        )
                    )

        return chunk_inline if chunk_inline else None

    def _merge_short_paragraphs(self, sections: List[Section]) -> List[Section]:
        """
        合并短段落

        连续的短段落（< SHORT_PARAGRAPH_THRESHOLD）会被合并，
        以减少碎片化，提高翻译上下文连贯性。
        """
        for section in sections:
            if len(section.paragraphs) <= 1:
                continue

            merged_paragraphs = []
            current_merge = None
            current_merge_inline = []

            for p in section.paragraphs:
                # 跳过特殊元素（图片、代码、标题等）
                if p.element_type in [
                    ElementType.IMAGE,
                    ElementType.TABLE,
                    ElementType.CODE,
                    ElementType.H3,
                    ElementType.H4,
                ]:
                    if current_merge:
                        merged_paragraphs.append(current_merge)
                        current_merge = None
                        current_merge_inline = []
                    merged_paragraphs.append(p)
                    continue

                # 如果当前段落很短
                if len(p.source) < self.SHORT_PARAGRAPH_THRESHOLD:
                    if current_merge is None:
                        # 开始新的合并
                        current_merge = Paragraph(
                            id=p.id,
                            index=p.index,
                            source=p.source,
                            source_html=p.source_html,
                            element_type=p.element_type,
                            inline_elements=(
                                list(p.inline_elements) if p.inline_elements else []
                            ),
                        )
                        if p.inline_elements:
                            current_merge_inline = list(p.inline_elements)
                    else:
                        # 合并到当前
                        new_source = current_merge.source + " " + p.source
                        # 更新内联元素位置
                        if p.inline_elements:
                            offset = len(current_merge.source) + 1
                            for el in p.inline_elements:
                                current_merge_inline.append(
                                    InlineElement(
                                        type=el.type,
                                        text=el.text,
                                        start=el.start + offset,
                                        end=el.end + offset,
                                        href=el.href,
                                        title=el.title,
                                    )
                                )
                        current_merge.source = new_source
                        current_merge.inline_elements = (
                            current_merge_inline if current_merge_inline else None
                        )

                        # 如果合并后超过阈值，停止合并
                        if len(current_merge.source) >= self.SHORT_PARAGRAPH_THRESHOLD:
                            merged_paragraphs.append(current_merge)
                            current_merge = None
                            current_merge_inline = []
                else:
                    # 正常长度段落，先保存之前的合并
                    if current_merge:
                        merged_paragraphs.append(current_merge)
                        current_merge = None
                        current_merge_inline = []
                    merged_paragraphs.append(p)

            # 保存最后的合并
            if current_merge:
                merged_paragraphs.append(current_merge)

            # 重新编号
            for i, p in enumerate(merged_paragraphs):
                p.id = f"p{i:03d}"
                p.index = i

            section.paragraphs = merged_paragraphs

        return sections

    def _split_sentences(self, text: str) -> List[str]:
        """按句子拆分文本"""
        # 简单的句子分割：按 . ! ? 分割，但保留缩写
        # 这是一个简化版本，可以根据需要改进
        sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_element_type(self, el_type: str) -> ElementType:
        """将 HTML 元素类型转换为 ElementType 枚举"""
        mapping = {
            "h1": ElementType.H1,
            "h2": ElementType.H2,
            "h3": ElementType.H3,
            "h4": ElementType.H4,
            "p": ElementType.P,
            "li": ElementType.LI,
            "blockquote": ElementType.BLOCKQUOTE,
            "pre": ElementType.CODE,
            "code": ElementType.CODE,
            "table": ElementType.TABLE,
            "img": ElementType.IMAGE,
        }
        return mapping.get(el_type, ElementType.P)

    def to_markdown(
        self,
        sections: List[Section],
        include_translation: bool = False,
        restore_inline_elements: bool = True,
        title: Optional[str] = None,
        title_translation: Optional[str] = None,
        metadata: Optional[ArticleMetadata] = None,
    ) -> str:
        """
        将章节列表转换为 Markdown

        Args:
            sections: 章节列表
            include_translation: 是否包含译文
            restore_inline_elements: 是否恢复内联元素（链接等）
            title: 文章标题
            title_translation: 文章标题翻译
            metadata: 文章元信息

        Returns:
            str: Markdown 文本
        """
        lines = []

        # 添加文章标题
        if title:
            article_title = (
                title_translation
                if include_translation and title_translation
                else title
            )
            lines.append(f"# {article_title}\n")

        # 添加元信息
        if metadata:
            meta_lines = []
            if metadata.authors:
                authors_str = ", ".join(metadata.authors)
                meta_lines.append(
                    f"**作者**: {authors_str}"
                    if include_translation
                    else f"**Author**: {authors_str}"
                )
            if metadata.published_date:
                meta_lines.append(
                    f"**日期**: {metadata.published_date}"
                    if include_translation
                    else f"**Date**: {metadata.published_date}"
                )
            if metadata.subtitle:
                meta_lines.append(f"*{metadata.subtitle}*")
            if meta_lines:
                lines.extend(meta_lines)
                lines.append("")

        for section in sections:
            # 章节标题
            section_title = (
                section.title_translation
                if include_translation and section.title_translation
                else section.title
            )
            lines.append(f"## {section_title}\n")

            for p in section.paragraphs:
                text = p.confirmed if include_translation and p.confirmed else p.source

                # 恢复内联元素
                if (
                    restore_inline_elements
                    and p.inline_elements
                    and not include_translation
                ):
                    text = self._restore_inline_elements(text, p.inline_elements)

                # 根据元素类型格式化
                if p.element_type == ElementType.H3:
                    lines.append(f"### {text}\n")
                elif p.element_type == ElementType.H4:
                    lines.append(f"#### {text}\n")
                elif p.element_type == ElementType.LI:
                    lines.append(f"- {text}")
                elif p.element_type == ElementType.BLOCKQUOTE:
                    lines.append(f"> {text}\n")
                elif p.element_type == ElementType.CODE:
                    lines.append(f"```\n{text}\n```\n")
                elif p.element_type == ElementType.IMAGE:
                    # 图片处理
                    lines.append(f"![image]({text})\n")
                else:
                    lines.append(f"{text}\n")

            lines.append("")  # 章节间空行

        return "\n".join(lines)

    def _restore_inline_elements(
        self, text: str, inline_elements: List[InlineElement]
    ) -> str:
        """
        将内联元素恢复到文本中（Markdown 格式）

        Args:
            text: 原始文本
            inline_elements: 内联元素列表

        Returns:
            带有 Markdown 格式的文本
        """
        if not inline_elements:
            return text

        # 按位置倒序排列（从后往前替换，避免位置偏移）
        sorted_elements = sorted(inline_elements, key=lambda x: x.start, reverse=True)

        result = text
        for el in sorted_elements:
            # 确保位置有效
            if el.start < 0 or el.end > len(result):
                continue

            original_text = result[el.start : el.end]
            if original_text != el.text:
                # 位置不匹配，尝试查找
                actual_start = result.find(el.text)
                if actual_start < 0:
                    continue
                el.start = actual_start
                el.end = actual_start + len(el.text)

            if el.type == "link" and el.href:
                replacement = f"[{el.text}]({el.href})"
            elif el.type == "strong":
                replacement = f"**{el.text}**"
            elif el.type == "em":
                replacement = f"*{el.text}*"
            elif el.type == "code":
                replacement = f"`{el.text}`"
            else:
                continue

            result = result[: el.start] + replacement + result[el.end :]

        return result


def parse_html_file(
    file_path: str, max_paragraph_length: int = 800, merge_short_paragraphs: bool = True
) -> Tuple[str, List[Section], Optional[ArticleMetadata]]:
    """
    便捷函数：解析 HTML 文件

    Returns:
        Tuple[str, List[Section], Optional[ArticleMetadata]]:
            (文章标题, 章节列表, 元信息)
    """
    parser = HTMLParser(
        max_paragraph_length=max_paragraph_length,
        merge_short_paragraphs=merge_short_paragraphs,
    )
    return parser.parse_file(file_path)
