"""
术语匹配器

提供统一的术语匹配接口，整合分类、编译和验证功能。
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any

from src.models.terminology import Term
from .classifier import TermClassifier, TermType
from .pattern_compiler import PatternCompiler
from .validator import MatchValidator


@dataclass
class MatchResult:
    """匹配结果"""
    term: Term
    matched_text: str
    start: int
    end: int
    context: str  # 前后各 20 字符


class TermMatcher:
    """术语匹配器"""

    def __init__(self, terms: List[Term]):
        """
        初始化匹配器

        Args:
            terms: 术语列表
        """
        self.terms = terms
        self.classifier = TermClassifier()
        self.compiler = PatternCompiler()
        self.validator = MatchValidator()

        # 预编译所有术语
        self._compiled_terms = self._precompile_terms()

    def _precompile_terms(self) -> List[Tuple[Term, TermType, Optional[re.Pattern], dict]]:
        """
        预编译所有术语

        Returns:
            编译后的术语列表：(Term, TermType, Pattern, strategy)
        """
        compiled = []
        for term in self.terms:
            term_type = self.classifier.classify(term.original)
            strategy = self.classifier.get_matching_strategy(term_type)
            pattern = self.compiler.compile_pattern(term.original, term_type, strategy)
            compiled.append((term, term_type, pattern, strategy))
        return compiled

    def match_all(self, text: str) -> List[MatchResult]:
        """
        匹配文本中的所有术语

        Args:
            text: 待匹配的文本

        Returns:
            匹配结果列表，按位置排序
        """
        results = []

        for term, term_type, pattern, strategy in self._compiled_terms:
            if term_type == TermType.CHINESE:
                # 中文直接子串匹配
                matches = self._match_chinese(term.original, text)
            else:
                # 使用正则匹配
                if pattern is None:
                    continue
                matches = pattern.finditer(text)

            for match in matches:
                # 验证匹配
                if self.validator.validate_match(term.original, text, match, term_type):
                    start, end = match.span()
                    context = self._extract_context(text, start, end)
                    results.append(MatchResult(
                        term=term,
                        matched_text=text[start:end],
                        start=start,
                        end=end,
                        context=context
                    ))

        # 按位置排序
        results.sort(key=lambda r: r.start)
        return results

    def match_term(self, term: Term, text: str) -> List[MatchResult]:
        """
        匹配单个术语

        Args:
            term: 术语
            text: 待匹配的文本

        Returns:
            匹配结果列表
        """
        results = []

        # 分类和编译
        term_type = self.classifier.classify(term.original)
        strategy = self.classifier.get_matching_strategy(term_type)
        pattern = self.compiler.compile_pattern(term.original, term_type, strategy)

        if term_type == TermType.CHINESE:
            # 中文直接子串匹配
            matches = self._match_chinese(term.original, text)
        else:
            # 使用正则匹配
            if pattern is None:
                return results
            matches = pattern.finditer(text)

        for match in matches:
            # 验证匹配
            if self.validator.validate_match(term.original, text, match, term_type):
                start, end = match.span()
                context = self._extract_context(text, start, end)
                results.append(MatchResult(
                    term=term,
                    matched_text=text[start:end],
                    start=start,
                    end=end,
                    context=context
                ))

        return results

    def count_occurrences(self, term: Term, text: str) -> int:
        """
        统计术语出现次数

        Args:
            term: 术语
            text: 待匹配的文本

        Returns:
            出现次数
        """
        return len(self.match_term(term, text))

    def _match_chinese(self, term: str, text: str) -> List[Any]:
        """
        中文子串匹配

        Args:
            term: 中文术语
            text: 待匹配的文本

        Returns:
            伪 Match 对象列表
        """
        matches = []
        start = 0
        while True:
            pos = text.find(term, start)
            if pos == -1:
                break
            # 创建伪 Match 对象
            # 使用闭包捕获当前的 pos 和 term 值
            def make_match(position, text_match):
                class FakeMatch:
                    def span(self):
                        return (position, position + len(text_match))
                    def group(self):
                        return text_match
                return FakeMatch()

            matches.append(make_match(pos, term))
            start = pos + 1
        return matches

    def _extract_context(self, text: str, start: int, end: int, window: int = 20) -> str:
        """
        提取上下文

        Args:
            text: 原文本
            start: 匹配开始位置
            end: 匹配结束位置
            window: 上下文窗口大小

        Returns:
            上下文字符串
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
