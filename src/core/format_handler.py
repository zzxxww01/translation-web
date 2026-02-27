"""
Format Consistency - 格式一致性处理

保留HTML结构，确保输出格式与原文一致
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re


@dataclass
class HtmlStructure:
    """HTML结构信息"""

    tag: str  # 标签名：p, div, li等
    classes: List[str]  # CSS类
    attributes: Dict[str, str]  # 属性
    is_list_item: bool = False
    list_type: Optional[str] = None  # ul, ol
    nesting_level: int = 0  # 嵌套层级


class HtmlStructureExtractor:
    """HTML结构提取器"""

    def extract_structure(self, html: str) -> HtmlStructure:
        """
        从HTML提取结构信息

        Args:
            html: HTML字符串

        Returns:
            HtmlStructure对象
        """
        soup = BeautifulSoup(html, "html.parser")

        # 找到主要元素
        main_element = soup.find()

        if not main_element:
            # 默认为段落
            return HtmlStructure(tag="p", classes=[], attributes={})

        # 提取信息
        tag = main_element.name
        classes = main_element.get("class", [])

        # 提取所有属性
        attributes = {}
        for key, value in main_element.attrs.items():
            if key != "class":
                if isinstance(value, list):
                    attributes[key] = " ".join(value)
                else:
                    attributes[key] = str(value)

        # 检查是否是列表项
        is_list_item = tag in ["li"]
        list_type = None

        if is_list_item and main_element.parent:
            list_type = main_element.parent.name  # ul or ol

        return HtmlStructure(
            tag=tag,
            classes=classes if isinstance(classes, list) else [classes],
            attributes=attributes,
            is_list_item=is_list_item,
            list_type=list_type,
        )

    def extract_text(self, html: str) -> str:
        """提取纯文本"""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text().strip()


class MarkdownExporter:
    """Markdown导出器"""

    def __init__(self):
        self.structure_extractor = HtmlStructureExtractor()

    def export_paragraph(
        self,
        translation: str,
        structure: Optional[HtmlStructure] = None,
        preserve_html: bool = False,
    ) -> str:
        """
        导出段落为Markdown

        Args:
            translation: 翻译后的文本
            structure: HTML结构信息
            preserve_html: 是否保留HTML标签

        Returns:
            Markdown格式的文本
        """
        if not structure:
            # 没有结构信息，直接返回
            return translation

        # 如果要保留HTML
        if preserve_html:
            return self._wrap_in_html(translation, structure)

        # 转换为Markdown
        return self._convert_to_markdown(translation, structure)

    def _wrap_in_html(self, text: str, structure: HtmlStructure) -> str:
        """包装为HTML"""
        # 构建开始标签
        tag = structure.tag
        attrs = []

        if structure.classes:
            attrs.append(f'class="{" ".join(structure.classes)}"')

        for key, value in structure.attributes.items():
            attrs.append(f'{key}="{value}"')

        attr_str = " " + " ".join(attrs) if attrs else ""

        return f"<{tag}{attr_str}>{text}</{tag}>"

    def _convert_to_markdown(self, text: str, structure: HtmlStructure) -> str:
        """转换为Markdown格式"""
        # 列表项
        if structure.is_list_item:
            if structure.list_type == "ol":
                return f"1. {text}"
            else:
                return f"- {text}"

        # 标题
        if structure.tag.startswith("h") and len(structure.tag) == 2:
            level = int(structure.tag[1])
            return f"{'#' * level} {text}"

        # 引用
        if structure.tag == "blockquote":
            lines = text.split("\n")
            return "\n".join(f"> {line}" for line in lines)

        # 代码块
        if structure.tag == "pre" or structure.tag == "code":
            return f"```\n{text}\n```"

        # 普通段落
        return text

    def export_section(
        self, paragraphs: List[Dict[str, Any]], preserve_html: bool = False
    ) -> str:
        """
        导出整个章节

        Args:
            paragraphs: 段落列表，每个包含translation和structure
            preserve_html: 是否保留HTML

        Returns:
            完整的Markdown文本
        """
        lines = []

        for para in paragraphs:
            translation = para.get("translation", "")
            structure = para.get("structure")

            markdown = self.export_paragraph(translation, structure, preserve_html)
            lines.append(markdown)

        return "\n\n".join(lines)


class FormatValidator:
    """格式验证器"""

    def validate_structure(
        self, original_html: str, translated_markdown: str
    ) -> Dict[str, Any]:
        """
        验证翻译后的格式是否保持一致

        Args:
            original_html: 原始HTML
            translated_markdown: 翻译后的Markdown

        Returns:
            {
                "valid": bool,
                "issues": [...]
            }
        """
        issues = []

        # 提取原始结构
        extractor = HtmlStructureExtractor()
        structure = extractor.extract_structure(original_html)

        # 检查列表项
        if structure.is_list_item:
            if not (
                translated_markdown.startswith("- ")
                or translated_markdown.startswith("* ")
                or re.match(r"^\d+\.\s", translated_markdown)
            ):
                issues.append({"type": "list_format", "message": "列表项格式丢失"})

        # 检查标题
        if structure.tag.startswith("h"):
            level = int(structure.tag[1])
            expected_prefix = "#" * level
            if not translated_markdown.startswith(expected_prefix):
                issues.append(
                    {
                        "type": "heading_format",
                        "message": f"标题层级不匹配（期望H{level}）",
                    }
                )

        # 检查段落是否为空
        if not translated_markdown.strip():
            issues.append({"type": "empty_paragraph", "message": "译文为空"})

        return {"valid": len(issues) == 0, "issues": issues}


# 辅助函数
def preserve_original_format(
    original_html: str, translation: str, output_format: str = "markdown"
) -> str:
    """
    保留原始格式导出

    Args:
        original_html: 原始HTML
        translation: 翻译文本
        output_format: 输出格式 ("markdown" or "html")

    Returns:
        格式化后的文本
    """
    extractor = HtmlStructureExtractor()
    exporter = MarkdownExporter()

    structure = extractor.extract_structure(original_html)

    if output_format == "html":
        return exporter._wrap_in_html(translation, structure)
    else:
        return exporter._convert_to_markdown(translation, structure)
