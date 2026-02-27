"""
Inline Element Handler - 内联元素处理器

使用占位符策略保留Markdown内联元素（链接、粗体、斜体、代码等）
"""

from typing import List, Tuple, Optional
import re
from dataclasses import dataclass


@dataclass
class InlineElement:
    """内联元素"""

    type: str  # "link", "bold", "italic", "code"
    text: str  # 原始文本内容
    start: int  # 在原文中的起始位置
    end: int  # 结束位置

    # 链接专用
    href: Optional[str] = None
    title: Optional[str] = None

    # 占位符相关
    placeholder: Optional[str] = None
    text_translation: Optional[str] = None


class InlineElementExtractor:
    """内联元素提取器"""

    # Markdown模式
    PATTERNS = {
        # 链接: [text](url "title")
        "link": r'\[([^\]]+)\]\(([^\s\)]+)(?:\s+"([^"]+)")?\)',
        # 粗体: **text** 或 __text__
        "bold": r"\*\*([^\*]+)\*\*|__([^_]+)__",
        # 斜体: *text* 或 _text_
        "italic": r"\*([^\*]+)\*|_([^_]+)_",
        # 行内代码: `code`
        "code": r"`([^`]+)`",
    }

    def extract_from_markdown(self, markdown: str) -> Tuple[str, List[InlineElement]]:
        """
        从Markdown文本中提取内联元素

        Args:
            markdown: Markdown文本

        Returns:
            (纯文本, 内联元素列表)
        """
        elements = []

        # 按优先级提取（链接 > 粗体 > 斜体 > 代码）
        # 使用综合正则表达式一次性匹配所有类型

        combined_pattern = (
            r'\[([^\]]+)\]\(([^\s\)]+)(?:\s+"([^"]+)")?\)|'  # 链接
            r"\*\*([^\*]+)\*\*|"  # 粗体**
            r"__([^_]+)__|"  # 粗体__
            r"(?<!\*)\*(?!\*)([^\*]+)\*(?!\*)|"  # 斜体* (避免与粗体冲突)
            r"(?<!_)_(?!_)([^_]+)_(?!_)|"  # 斜体_ (避免与粗体冲突)
            r"`([^`]+)`"  # 代码
        )

        for match in re.finditer(combined_pattern, markdown):
            start = match.start()
            end = match.end()

            # 判断匹配类型
            if match.group(1):  # 链接
                elem = InlineElement(
                    type="link",
                    text=match.group(1),
                    start=start,
                    end=end,
                    href=match.group(2),
                    title=match.group(3),
                )
            elif match.group(4):  # 粗体**
                elem = InlineElement(
                    type="bold", text=match.group(4), start=start, end=end
                )
            elif match.group(5):  # 粗体__
                elem = InlineElement(
                    type="bold", text=match.group(5), start=start, end=end
                )
            elif match.group(6):  # 斜体*
                elem = InlineElement(
                    type="italic", text=match.group(6), start=start, end=end
                )
            elif match.group(7):  # 斜体_
                elem = InlineElement(
                    type="italic", text=match.group(7), start=start, end=end
                )
            elif match.group(8):  # 代码
                elem = InlineElement(
                    type="code", text=match.group(8), start=start, end=end
                )
            else:
                continue

            elements.append(elem)

        # 提取纯文本（移除所有Markdown标记）
        plain_text = self._extract_plain_text(markdown, elements)

        return plain_text, elements

    def _extract_plain_text(self, markdown: str, elements: List[InlineElement]) -> str:
        """提取纯文本"""
        # 简化实现：直接替换所有内联元素为其文本内容
        result = markdown

        # 从后往前替换，避免位置偏移
        for elem in sorted(elements, key=lambda e: e.start, reverse=True):
            result = result[: elem.start] + elem.text + result[elem.end :]

        return result


class PlaceholderHandler:
    """占位符处理器"""

    PLACEHOLDER_FORMAT = "{{{{{}|{}}}}}"  # {{TYPE_N|text}}

    def insert_placeholders(
        self, text: str, elements: List[InlineElement]
    ) -> Tuple[str, List[InlineElement]]:
        """
        插入占位符

        Args:
            text: 原文本（已移除Markdown标记）
            elements: 内联元素列表

        Returns:
            (带占位符的文本, 更新后的元素列表)
        """
        if not elements:
            return text, elements

        # 按位置排序
        sorted_elements = sorted(elements, key=lambda e: e.start)

        # 生成占位符
        type_counters = {}
        for elem in sorted_elements:
            elem_type = elem.type.upper()
            type_counters[elem_type] = type_counters.get(elem_type, 0) + 1
            elem.placeholder = f"{elem_type}_{type_counters[elem_type]}"

        # 从后往前替换，避免位置偏移
        result = text
        for elem in reversed(sorted_elements):
            placeholder_text = self.PLACEHOLDER_FORMAT.format(
                elem.placeholder, elem.text
            )
            result = result[: elem.start] + placeholder_text + result[elem.end :]

        return result, sorted_elements

    def restore_elements(
        self, translated_text: str, elements: List[InlineElement]
    ) -> str:
        """
        从翻译后的文本还原内联元素

        Args:
            translated_text: 翻译后的文本（含占位符）
            elements: 原始元素列表

        Returns:
            还原后的Markdown文本
        """
        if not elements:
            return translated_text

        result = translated_text

        for elem in elements:
            if not elem.placeholder:
                continue

            # 匹配占位符: {{LINK_1|translated_text}}
            pattern = r"\{\{" + re.escape(elem.placeholder) + r"\|([^}]+)\}\}"

            def replace_func(match):
                # 提取翻译后的文本
                translated_elem_text = match.group(1)
                elem.text_translation = translated_elem_text

                # 重建Markdown
                if elem.type == "link":
                    if elem.title:
                        return f'[{translated_elem_text}]({elem.href} "{elem.title}")'
                    else:
                        return f"[{translated_elem_text}]({elem.href})"
                elif elem.type == "bold":
                    return f"**{translated_elem_text}**"
                elif elem.type == "italic":
                    return f"*{translated_elem_text}*"
                elif elem.type == "code":
                    # 代码不翻译，保持原文
                    return f"`{elem.text}`"
                else:
                    return translated_elem_text

            result = re.sub(pattern, replace_func, result)

        return result


# 辅助函数
def process_inline_elements(markdown: str) -> Tuple[str, List[InlineElement], str]:
    """
    完整的内联元素处理流程

    Args:
        markdown: 原始Markdown文本

    Returns:
        (纯文本, 元素列表, 带占位符的文本)
    """
    extractor = InlineElementExtractor()
    handler = PlaceholderHandler()

    # 提取
    plain_text, elements = extractor.extract_from_markdown(markdown)

    # 插入占位符
    text_with_placeholders, updated_elements = handler.insert_placeholders(
        plain_text, elements
    )

    return plain_text, updated_elements, text_with_placeholders
