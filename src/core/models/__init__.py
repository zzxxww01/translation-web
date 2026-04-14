"""
Translation Agent - Data Models

Re-exports all model classes for backward compatibility.
Import from ``src.core.models`` continues to work unchanged.
"""

# --- Enums ---
from .enums import (
    TranslationStrategy,
    ParagraphStatus,
    ProjectStatus,
    ElementType,
)

# --- Glossary ---
from .glossary import GlossaryTerm, Glossary

# --- Translation / Paragraph / Section ---
from .translation import (
    TranslationRecord,
    HistoryRecord,
    InlineElement,
    Paragraph,
    Section,
)

# --- Project ---
from .project import (
    ProjectProgress,
    ProjectConfig,
    ArticleMetadata,
    ProjectMeta,
)

# --- Analysis & Four-Step ---
from .analysis import (
    StyleGuide,
    AnalysisResult,
    EnhancedTerm,
    ArticleStyle,
    TranslationChallenge,
    SectionUnderstanding,
    ArticleAnalysis,
    TranslationIssue,
    ReflectionResult,
    QualityAssessment,
    SectionTranslationResult,
    TermUsageTracker,
    LayeredContext,
    SectionQualityScore,
    QualityReportSummary,
)

# --- Consistency ---
from .consistency import (
    ConsistencyIssue,
    ConsistencyReport,
    TermUsageStats,
    StyleScore,
    ConsistencyReviewResult,
)

# --- Confirmation Workflow ---
from .confirmation import (
    TranslationVersion,
    ParagraphConfirmation,
    AIInsight,
    RetranslateOption,
)

# --- Translation Memory & Prescan ---
from .memory import (
    PrescanTerm,
    SectionPrescanResult,
    TermConflict,
    TermConflictResolution,
    TerminologyVersion,
)

__all__ = [
    # Enums
    "TranslationStrategy",
    "ParagraphStatus",
    "ProjectStatus",
    "ElementType",
    # Glossary
    "GlossaryTerm",
    "Glossary",
    # Translation
    "TranslationRecord",
    "HistoryRecord",
    "InlineElement",
    "Paragraph",
    "Section",
    # Project
    "ProjectProgress",
    "ProjectConfig",
    "ArticleMetadata",
    "ProjectMeta",
    # Analysis
    "StyleGuide",
    "AnalysisResult",
    "EnhancedTerm",
    "ArticleStyle",
    "TranslationChallenge",
    "SectionUnderstanding",
    "ArticleAnalysis",
    "TranslationIssue",
    "ReflectionResult",
    "QualityAssessment",
    "SectionTranslationResult",
    "TermUsageTracker",
    "LayeredContext",
    "SectionQualityScore",
    "QualityReportSummary",
    # Consistency
    "ConsistencyIssue",
    "ConsistencyReport",
    "TermUsageStats",
    "StyleScore",
    "ConsistencyReviewResult",
    # Confirmation
    "TranslationVersion",
    "ParagraphConfirmation",
    "AIInsight",
    "RetranslateOption",
    # Memory
    "PrescanTerm",
    "SectionPrescanResult",
    "TermConflict",
    "TermConflictResolution",
    "TerminologyVersion",
]
