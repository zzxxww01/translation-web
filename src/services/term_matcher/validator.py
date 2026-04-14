"""
匹配验证器

回溯验证短缩写匹配，过滤误报。
"""

import re
from typing import Match

from .classifier import TermType


class MatchValidator:
    """匹配验证器"""

    @staticmethod
    def validate_match(
        term: str, text: str, match: Match, term_type: TermType
    ) -> bool:
        """
        验证匹配是否有效

        Args:
            term: 术语原文
            text: 被匹配的文本
            match: 正则匹配对象
            term_type: 术语类型

        Returns:
            匹配是否有效
        """
        if term_type != TermType.SHORT_ACRONYM:
            return True  # 非短缩写直接通过

        # 短缩写需要回溯验证
        start, end = match.span()

        # 检查前后字符
        before = text[start - 1] if start > 0 else ' '
        after = text[end] if end < len(text) else ' '

        # 规则：前后必须是非字母字符
        if before.isalpha() or after.isalpha():
            return False

        # 额外验证：避免 "AI" 匹配到 "DRAM" 中的 "AI"
        # 检查是否在一个更大的全大写单词中
        # 向前扩展（包括大写字母和数字）
        extended_start = start
        while extended_start > 0 and (text[extended_start - 1].isupper() or text[extended_start - 1].isdigit()):
            extended_start -= 1

        # 向后扩展（包括大写字母和数字）
        extended_end = end
        while extended_end < len(text) and (text[extended_end].isupper() or text[extended_end].isdigit()):
            extended_end += 1

        # 如果扩展后的词比原术语长，说明是误报
        extended_word = text[extended_start:extended_end]
        if len(extended_word) > len(term) and extended_word.upper() != term.upper():
            return False

        return True

    @staticmethod
    def validate_context(
        term: str, text: str, match: Match, min_context_chars: int = 10
    ) -> bool:
        """
        验证上下文（可选）

        Args:
            term: 术语原文
            text: 被匹配的文本
            match: 正则匹配对象
            min_context_chars: 最小上下文字符数

        Returns:
            上下文是否有效
        """
        start, end = match.span()

        # 提取上下文
        context_start = max(0, start - min_context_chars)
        context_end = min(len(text), end + min_context_chars)
        context = text[context_start:context_end]

        # 这里可以添加更复杂的上下文验证逻辑
        # 例如：检查是否在代码块、URL、邮箱中

        return True
