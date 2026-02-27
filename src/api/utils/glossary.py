"""
Glossary Utilities - 术语表工具函数
"""

from src.core.glossary import GlossaryManager
from src.core.models import Glossary
from typing import List, Optional

# Global glossary manager
_gm = GlossaryManager(projects_path="projects")


def get_glossary_manager() -> GlossaryManager:
    """获取术语表管理器实例"""
    return _gm


def build_glossary_context(max_terms: int = 30) -> str:
    """
    构建术语表上下文字符串

    Args:
        max_terms: 最大术语数量限制

    Returns:
        格式化的术语表字符串，如果没有术语则返回空字符串
    """
    try:
        glossary = _gm.load_global("semiconductor")
        if glossary.terms:
            terms_text = "\n".join(
                [
                    f"- {t.original}: {t.translation or '保留原文'}"
                    for t in glossary.terms[:max_terms]
                ]
            )
            return f"\n\n术语表（请严格遵循）：\n{terms_text}"
    except Exception:
        pass
    return ""


def build_glossary_context_from_terms(
    terms: List,
    include_strategy: bool = True
) -> str:
    """
    从术语列表构建上下文字符串

    Args:
        terms: 术语列表（GlossaryTerm 或字典）
        include_strategy: 是否包含翻译策略

    Returns:
        格式化的术语表字符串
    """
    if not terms:
        return ""

    lines = []
    for term in terms:
        if hasattr(term, 'original'):
            # GlossaryTerm 对象
            original = term.original
            translation = term.translation or '保留原文'
            strategy_note = ""
            if include_strategy and hasattr(term, 'strategy'):
                if term.strategy.value == "preserve":
                    strategy_note = " [保留原文]"
                elif term.strategy.value == "first_annotate":
                    strategy_note = " [首次注释]"
            lines.append(f"- {original}: {translation}{strategy_note}")
        elif isinstance(term, dict):
            # 字典
            original = term.get('original', '')
            translation = term.get('translation') or '保留原文'
            strategy_note = ""
            if include_strategy:
                strategy = term.get('strategy', '')
                if strategy == "preserve":
                    strategy_note = " [保留原文]"
                elif strategy == "first_annotate":
                    strategy_note = " [首次注释]"
            lines.append(f"- {original}: {translation}{strategy_note}")

    if lines:
        return "\n\n术语表（请严格遵循）：\n" + "\n".join(lines)
    return ""


def filter_relevant_terms(
    glossary: Glossary,
    paragraph: str,
    max_terms: int = 20
) -> List:
    """
    筛选段落相关的术语

    Args:
        glossary: 术语表
        paragraph: 段落文本
        max_terms: 最大返回术语数量

    Returns:
        List[GlossaryTerm]: 相关术语列表
    """
    from src.core.term_matcher import filter_relevant_terms as _filter
    return _filter(glossary, paragraph, max_terms)


def load_project_glossary(project_id: str) -> Glossary:
    """
    加载项目术语表

    Args:
        project_id: 项目ID

    Returns:
        Glossary: 项目术语表，如果不存在则返回空术语表
    """
    try:
        return _gm.load_project(project_id)
    except Exception:
        return Glossary()


def load_global_glossary(domain: str = "semiconductor") -> Glossary:
    """
    加载全局术语表

    Args:
        domain: 领域名称

    Returns:
        Glossary: 全局术语表
    """
    try:
        return _gm.load_global(domain)
    except Exception:
        return Glossary()


def get_combined_glossary(project_id: str, domain: str = "semiconductor") -> Glossary:
    """
    获取合并后的术语表（项目术语表 + 全局术语表）

    Args:
        project_id: 项目ID
        domain: 领域名称

    Returns:
        Glossary: 合并后的术语表
    """
    project_glossary = load_project_glossary(project_id)
    global_glossary = load_global_glossary(domain)

    # 合并术语表，项目术语表优先级更高
    combined = Glossary()
    combined.terms = list(global_glossary.terms)

    for term in project_glossary.terms:
        combined.add_term(term)

    return combined
