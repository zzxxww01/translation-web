# Agent modules

# 原有模块
from .translation import TranslationAgent, create_translation_agent
from .analysis import AnalysisAgent, create_analysis_agent

# 四步法新增模块
from .context_manager import LayeredContextManager, create_context_manager
from .quality_gate import QualityGate, create_quality_gate
from .four_step_translator import FourStepTranslator, create_four_step_translator
from .deep_analyzer import DeepAnalyzer, create_deep_analyzer
from .consistency_reviewer import ConsistencyReviewer, create_consistency_reviewer

__all__ = [
    # 原有
    "TranslationAgent",
    "create_translation_agent",
    "AnalysisAgent",
    "create_analysis_agent",
    # 四步法新增
    "LayeredContextManager",
    "create_context_manager",
    "QualityGate",
    "create_quality_gate",
    "FourStepTranslator",
    "create_four_step_translator",
    "DeepAnalyzer",
    "create_deep_analyzer",
    "ConsistencyReviewer",
    "create_consistency_reviewer",
]
