"""
Metadata Parser - 元信息解析器

识别和处理文档中的元信息（作者、日期、技术指标等）
"""

from typing import Optional, Dict, Any, List
import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class MetadataInfo:
    """元信息"""

    type: str  # author, date, tech_spec
    original: str
    translated: Optional[str] = None


class MetadataParser:
    """元信息解析器"""

    # 日期格式模式
    DATE_PATTERNS = [
        r"[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}",  # Oct 10, 2025
        r"\d{4}-\d{2}-\d{2}",  # 2025-10-10
        r"\d{1,2}/\d{1,2}/\d{4}",  # 10/10/2025
    ]

    # 人名模式（简化版）
    NAME_PATTERN = r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"

    # GPU型号模式
    GPU_PATTERN = r"\b(NVIDIA|AMD|Intel)\s+[A-Z0-9]+\b"

    # 技术指标模式
    TECH_SPEC_PATTERNS = [
        r"\b\w+\s+(per|token|tokens?|GPU|second|user)\b",
        r"\b(throughput|latency|performance|tok/s)\b",
    ]

    def detect_metadata_type(self, text: str) -> Optional[str]:
        """
        检测文本是否为元信息及其类型

        Returns:
            None | "author" | "date" | "tech_spec"
        """
        text_lower = text.lower()

        # 检测日期
        for pattern in self.DATE_PATTERNS:
            if re.search(pattern, text):
                return "date"

        # 检测人名（如果包含2-3个大写开头的单词）
        if re.findall(self.NAME_PATTERN, text):
            # 进一步检查：不应该是普通句子
            words = text.split()
            if len(words) <= 5 and sum(1 for w in words if w[0].isupper()) >= 2:
                return "author"

        # 检测技术指标
        for pattern in self.TECH_SPEC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "tech_spec"

        return None

    def translate_metadata(self, text: str, metadata_type: str) -> str:
        """
        翻译元信息

        Args:
            text: 原文
            metadata_type: 元信息类型

        Returns:
            翻译后的文本
        """
        if metadata_type == "author":
            # 人名保留原文
            return text

        elif metadata_type == "date":
            # 转换日期格式
            return self._translate_date(text)

        elif metadata_type == "tech_spec":
            # 技术指标：保留专有名词，翻译通用词
            return self._translate_tech_spec(text)

        return text

    def _translate_date(self, date_str: str) -> str:
        """转换日期为中文格式"""
        try:
            # 尝试解析常见格式
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    # 转换为中文格式：2025年10月10日
                    return f"{dt.year}年{dt.month}月{dt.day}日"
                except ValueError:
                    continue
        except Exception:
            pass

        # 如果解析失败，返回原文
        return date_str

    def _translate_tech_spec(self, text: str) -> str:
        """
        翻译技术指标

        策略：
        - GPU型号保留：NVIDIA GB200 NVL72
        - 单位保留：Token, GPU, tok/s
        - 通用词翻译：Throughput → 吞吐量
        """
        result = text

        # 保留GPU型号（已经是英文，无需处理）

        # 翻译通用技术词汇
        translations = {
            "Throughput": "吞吐量",
            "throughput": "吞吐量",
            "Latency": "延迟",
            "latency": "延迟",
            "Performance": "性能",
            "performance": "性能",
            "per GPU": "每GPU",
            "per User": "每用户",
            "per user": "每用户",
        }

        for en, zh in translations.items():
            result = result.replace(en, zh)

        return result


class HeadingParser:
    """标题解析器"""

    def detect_heading_level(self, html: str) -> Optional[int]:
        """
        从HTML检测标题层级

        Args:
            html: HTML标签字符串

        Returns:
            1-6 的标题层级，或None
        """
        match = re.match(r"<h([1-6])", html, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def build_heading_chain(
        self,
        current_heading: str,
        current_level: int,
        previous_headings: List[tuple],  # [(level, text), ...]
    ) -> List[str]:
        """
        构建标题链

        Args:
            current_heading: 当前标题
            current_level: 当前标题层级
            previous_headings: 之前的标题列表

        Returns:
            标题链 ["# 主标题", "## 二级标题", ...]
        """
        chain = []

        # 找到所有父级标题
        for level, text in previous_headings:
            if level < current_level:
                prefix = "#" * level
                chain.append(f"{prefix} {text}")

        # 添加当前标题
        prefix = "#" * current_level
        chain.append(f"{prefix} {current_heading}")

        return chain


# 辅助函数
def is_likely_heading(text: str, element_type: str = "p") -> bool:
    """
    判断文本是否可能是标题

    即使HTML标记为<p>，也可能实际上是标题
    """
    # 如果是h1-h6标签，肯定是标题
    if element_type.startswith("h") and element_type[1:].isdigit():
        return True

    # 其他启发式规则
    # 1. 文本较短（< 100字符）
    # 2. 全大写或首字母大写
    # 3. 没有句号结尾

    if len(text) > 100:
        return False

    if text.isupper() or (text[0].isupper() and not text.endswith(".")):
        # 进一步检查：不应该包含很多小写词
        words = text.split()
        if len(words) < 10:
            return True

    return False
