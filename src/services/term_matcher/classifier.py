"""
术语分类器

根据术语特征自动分类，为不同类型的术语提供相应的匹配策略。
"""

import re
from enum import Enum
from typing import Dict, Any


class TermType(str, Enum):
    """术语类型"""
    SHORT_ACRONYM = "short_acronym"      # 2-4字符缩写：AI, HBM, GPU
    MIXED_CASE = "mixed_case"            # 驼峰/混合大小写：CoWoS, HBM3E, iPhone
    COMMON_WORD = "common_word"          # 普通词：memory, chip, process
    SPECIAL_CHAR = "special_char"        # 包含特殊字符：C++, .NET, 3D-IC
    CHINESE = "chinese"                  # 中文术语：芯片、内存


class TermClassifier:
    """术语分类器"""

    @staticmethod
    def classify(term: str) -> TermType:
        """
        分类术语

        Args:
            term: 术语原文

        Returns:
            术语类型
        """
        if not term:
            return TermType.COMMON_WORD

        # 1. 检测中文
        if re.search(r'[\u4e00-\u9fff]', term):
            return TermType.CHINESE

        # 2. 检测特殊字符
        if re.search(r'[+\-./]', term):
            return TermType.SPECIAL_CHAR

        # 3. 检测短缩写（2-4字符，全大写，不含数字）
        if 2 <= len(term) <= 4 and term.isupper() and not re.search(r'\d', term):
            return TermType.SHORT_ACRONYM

        # 4. 检测驼峰/混合大小写
        # 匹配模式：小写后跟大写（如 iPhone）或大写-小写-大写（如 CoWoS）
        if re.search(r'[a-z][A-Z]', term) or re.search(r'[A-Z][a-z][A-Z]', term):
            return TermType.MIXED_CASE
        # 检测数字与字母混合（如 HBM3E）
        if re.search(r'\d', term) and re.search(r'[A-Za-z]', term):
            return TermType.MIXED_CASE

        # 5. 默认为普通词
        return TermType.COMMON_WORD

    @staticmethod
    def get_matching_strategy(term_type: TermType) -> Dict[str, Any]:
        """
        获取匹配策略配置

        Args:
            term_type: 术语类型

        Returns:
            匹配策略配置字典
        """
        strategies = {
            TermType.SHORT_ACRONYM: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": True,  # 需要回溯验证
                "min_context_chars": 1
            },
            TermType.MIXED_CASE: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": False
            },
            TermType.COMMON_WORD: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": False,
                "support_inflection": True  # 支持词形变化
            },
            TermType.SPECIAL_CHAR: {
                "case_sensitive": False,
                "word_boundary": False,  # 特殊字符本身就是边界
                "backtrack_validation": False
            },
            TermType.CHINESE: {
                "case_sensitive": True,
                "word_boundary": False,
                "backtrack_validation": False,
                "use_regex": False  # 中文不用正则
            }
        }
        return strategies[term_type]
