"""
正则模式编译器

预编译术语的正则表达式模式，提升匹配性能。
"""

import re
from functools import lru_cache
from typing import Optional, List, Dict, Any

from .classifier import TermType


class PatternCompiler:
    """正则模式编译器"""

    def __init__(self):
        """初始化编译器"""
        self._cache: Dict[str, re.Pattern] = {}

    def compile_pattern(
        self, term: str, term_type: TermType, strategy: Dict[str, Any]
    ) -> Optional[re.Pattern]:
        """
        编译术语匹配模式

        Args:
            term: 术语原文
            term_type: 术语类型
            strategy: 匹配策略配置

        Returns:
            编译后的正则模式，中文术语返回 None
        """
        # 创建缓存键（将 strategy 转为可哈希的元组）
        cache_key = (
            term,
            term_type,
            strategy.get("case_sensitive", False),
            strategy.get("word_boundary", True),
            strategy.get("support_inflection", False),
        )

        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 编译模式
        pattern = self._compile_pattern_impl(term, term_type, strategy)

        # 存入缓存
        self._cache[cache_key] = pattern
        return pattern

    def _compile_pattern_impl(
        self, term: str, term_type: TermType, strategy: Dict[str, Any]
    ) -> Optional[re.Pattern]:
        """
        编译模式的实际实现

        Args:
            term: 术语原文
            term_type: 术语类型
            strategy: 匹配策略配置

        Returns:
            编译后的正则模式
        """
        if term_type == TermType.CHINESE:
            # 中文不使用正则
            return None

        if not term:
            # 空术语返回一个不匹配任何内容的模式
            return re.compile(r'(?!.*)')

        # 转义特殊字符
        escaped = re.escape(term)

        # 构建模式
        if term_type == TermType.SHORT_ACRONYM:
            # 短缩写：严格词边界
            pattern = rf'\b{escaped}\b'

        elif term_type == TermType.MIXED_CASE:
            # 驼峰词：词边界
            pattern = rf'\b{escaped}\b'

        elif term_type == TermType.COMMON_WORD:
            # 普通词：支持词形变化
            if strategy.get("support_inflection"):
                variants = self._generate_inflection_variants(term)
                pattern = rf'\b(?:{"|".join(re.escape(v) for v in variants)})\b'
            else:
                pattern = rf'\b{escaped}\b'

        elif term_type == TermType.SPECIAL_CHAR:
            # 特殊字符：不需要词边界
            pattern = escaped

        else:
            # 默认：词边界
            pattern = rf'\b{escaped}\b'

        # 编译（大小写敏感性）
        flags = 0 if strategy.get("case_sensitive") else re.IGNORECASE
        return re.compile(pattern, flags)

    def _generate_inflection_variants(self, word: str) -> List[str]:
        """
        生成词形变体

        Args:
            word: 原始单词

        Returns:
            词形变体列表（包含原词）
        """
        variants = [word]

        # 复数形式
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            # memory -> memories
            variants.append(word[:-1] + 'ies')
        elif word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            # process -> processes
            variants.append(word + 'es')
        else:
            # chip -> chips
            variants.append(word + 's')

        # 过去式（简单规则）
        if word.endswith('e'):
            # use -> used
            variants.append(word + 'd')
        else:
            # process -> processed
            variants.append(word + 'ed')

        # 进行时
        if word.endswith('e') and len(word) > 1:
            # use -> using
            variants.append(word[:-1] + 'ing')
        else:
            # process -> processing
            variants.append(word + 'ing')

        return variants
