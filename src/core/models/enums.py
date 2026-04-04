"""Enum types shared across the translation agent domain."""

from enum import Enum


class TranslationStrategy(str, Enum):
    """术语翻译策略"""

    PRESERVE = "preserve"  # 全文保持英文原文，不加注释
    FIRST_ANNOTATE = "first_annotate"  # 首次出现翻译+括号注明，后续用中文
    TRANSLATE = "translate"  # 全文直接使用中文
    PRESERVE_ANNOTATE = "preserve_annotate"  # 首次出现保留原文+括号注中文，后续只保留原文


class ParagraphStatus(str, Enum):
    """段落翻译状态"""

    PENDING = "pending"  # 待翻译
    TRANSLATING = "translating"  # 翻译中
    TRANSLATED = "translated"  # 已翻译，待审阅
    REVIEWING = "reviewing"  # 审阅中
    MODIFIED = "modified"  # 已修改，待确认
    APPROVED = "approved"  # 已确认


class ProjectStatus(str, Enum):
    """项目状态"""

    CREATED = "created"  # 刚创建
    ANALYZING = "analyzing"  # 分析中
    IN_PROGRESS = "in_progress"  # 翻译进行中
    REVIEWING = "reviewing"  # 全文审阅中
    COMPLETED = "completed"  # 已完成


class ElementType(str, Enum):
    """HTML 元素类型"""

    H1 = "h1"
    H2 = "h2"
    H3 = "h3"
    H4 = "h4"
    P = "p"
    LI = "li"
    BLOCKQUOTE = "blockquote"
    CODE = "code"
    TABLE = "table"
    IMAGE = "image"

