"""
术语匹配引擎

提供高精度的术语匹配功能，支持多种术语类型的智能识别和验证。
"""

from .classifier import TermClassifier, TermType
from .pattern_compiler import PatternCompiler
from .validator import MatchValidator
from .matcher import TermMatcher, MatchResult

__all__ = [
    "TermClassifier",
    "TermType",
    "PatternCompiler",
    "MatchValidator",
    "TermMatcher",
    "MatchResult",
]
