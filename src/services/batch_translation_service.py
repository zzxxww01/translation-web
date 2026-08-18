"""
批量翻译服务

功能:
1. Phase 0: 深度分析全文
2. 逐章节翻译（四步法或粗粒度模式）
3. 进度跟踪（委托 ProgressTracker）
4. 错误处理和重试
5. 标题和元信息翻译
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Awaitable, List, Optional, Dict, Callable
from datetime import datetime
import logging

from src.core.glossary import infer_glossary_tags
from src.config.timeout_config import TimeoutConfig
from src.core.longform_context import (
    build_article_challenge_payload,
    build_glossary_entries_from_terms,
    build_previous_translation_pairs,
    build_section_context_payload,
    build_translation_guidelines,
)
from src.core.models import (
    ProjectMeta,
    Section,
    Paragraph,
    ParagraphStatus,
    ProjectStatus,
    ArticleAnalysis,
    EnhancedTerm,
    GlossaryTerm,
    TermConflict,
    TermConflictResolution,
    TranslationStrategy,
)
from src.core.format_tokens import (
    TranslationPayload,
    apply_translation_payload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
)
from src.core.glossary_prompt import _count_term_occurrences
from src.core.glossary_prompt import select_prompt_terms_for_text
from src.core.glossary_prompt import (
    render_glossary_prompt_block,
    select_glossary_terms_for_text,
)
from src.core.project import ProjectManager
from src.core.project_export_service import ExportBlockedError
from src.core.protected_terms import desinicize_token
from src.core.translation_qa import _POWER_UNIT_SINICIZED
from src.core.title_guard import (
    enforce_translated_title,
    extract_title_requirements,
    find_missing_title_terms,
)
from src.agents.deep_analyzer import DeepAnalyzer
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.agents.quality_report_generator import QualityReportGenerator
from src.llm.base import LLMProvider
from src.services.batch_translation_types import TranslationProgress
from src.services.progress_tracker import ProgressTracker
from src.services.source_metadata_service import SourceMetadataTranslationService
from src.services.translation_artifact_service import TranslationArtifactService
from src.services.translation_run_registry import (
    RunStateSnapshot,
    translation_run_registry,
)
from src.services.section_translation_executor import SectionTranslationExecutor
from src.services.term_review_artifact import (
    SUBMISSION_SUBMITTED,
    is_current_term_review_artifact,
    is_legacy_term_review_artifact,
)
from src.api.utils.concurrency import run_llm_blocking
from src.llm.usage_metrics import llm_usage_metrics


logger = logging.getLogger(__name__)

# 章节内段落在提示词里的分隔符，与整章拼接保持一致。
SECTION_LINE_SEPARATOR = chr(10) * 2

# 章节标题翻译共用的「白名单铁律」，与
# src/prompts/longform/translation/section_batch_translate.txt 第 7-14 行保持一致。
# 标题走的是独立的提示词链路，若不显式带上这段铁律，标题会出现「吉瓦」「词元」
# 一类正文里被明令禁止的写法，与正文形成两套术语。
SECTION_TITLE_WHITELIST_RULES = """## 白名单铁律——永不翻译（最高优先级，压过下方一切"尽量译成中文"的要求）
即便下文要求"白名单外复杂名词尽量译成中文"，**本清单中的词也绝不适用**，永远保持英文半角原形：
1. **token**：一律小写英文 token，绝不写成 词元／令牌／代币／词块。✅"更快的 token"、"40 token/秒"；❌"更快的词元"、"40 词元/秒"。复合专名 Tokenomics 也保留英文（❌代币经济学）。
2. **功率／能量单位**：GW／TW／MW／kW／W／GWh／MWh／kWh，以及任何含单位的复合／派生单位（W/cm²、W/m²、LPM、$/kW 等）永远保留半角原形、整体保留不拆译。✅"10GW"、"25 kW"、"50 W/cm²"；❌"10 吉瓦"、"25 千瓦"、"50 瓦/平方厘米"。原文用拼写形（gigawatts／kilowatts）时改写成符号（GW／kW），但绝不译成"吉瓦／千瓦"。GW/MW 显眼易留、kW/W 像中文而最易被误译——**kW≠千瓦、W≠瓦、W/cm²≠瓦/平方厘米**。其余计量/物理量符号（A/V/Hz/℃/bar/bps/GB·s⁻¹ 等）一律同理保留半角原形，禁译安培/伏特/赫兹/摄氏度。
3. **代码标识符／函数名／文件名／命令／环境变量／行内代码**、**软件库与产品名**（vLLM、CUDA、Bedrock、Copilot 等）、**硬件型号与工艺节点**（GB300、H100、N2、18A 等）、**基准测试名**：保持英文原名，禁意译（❌ Bedrock→基石）。
4. **URL／slug／被引用的英文文章·论文·报告标题／作者署名行**：保持英文。
5. **无通行中文译名的公司/机构专名（含术语表未登记者）**：一律保留英文原形；拿不准即保留，禁臆造中文名（如 CoreWeave 类术语表未登记的新公司不得译成中文）。
判定顺序：先看词是否落在本铁律或下方白名单；命中则永不翻译，不再走"尽量译成中文"。"""


def _repair_title_sinicization(translated_title: Optional[str]) -> tuple[str, str]:
    """修复标题里的白名单违规写法，返回 ``(修复后的标题, 未能修复的命中项)``。

    token 汉化有确定性 fixer（``desinicize_token``），就地改回英文即可，不必丢弃
    整个译名。功率单位没有 fixer——但它在正文里只是 warning，标题却把整条译名
    丢掉、回退成英文原标题，反而让成品更糟；所以只记 warning、保留译名，与正文
    口径一致（见 translation_qa 里 power_unit_sinicized 的降级说明）。
    """
    text = (translated_title or "").strip()
    if not text:
        return "", ""

    repaired = desinicize_token(text)
    match = _POWER_UNIT_SINICIZED.search(repaired)
    return repaired, (match.group(0) if match else "")


class BatchTranslationService:
    """批量翻译服务"""

    _shared_progress_tracker = ProgressTracker()
    PRESCAN_TIMEOUT_SECONDS = TimeoutConfig.ANALYSIS

    # 翻译模式
    TRANSLATION_MODE_FOUR_STEP = "four_step"  # 四步法（段落级）
    TRANSLATION_MODE_SECTION = "section"  # 章节级批量翻译

    # section 模式的单批上限。模型输出上限是 8192 token，而中文译文约 1 字 1 token，
    # 一批英文源文 12000 字符大致产出 4000-5000 中文字符，留足余量。
    # 语料实测：单章 9400 英文词的章节整章一次调用需要约 14000 输出 token，必然截断。
    MAX_SECTION_BATCH_PARAGRAPHS = 40
    MAX_SECTION_BATCH_CHARS = 12000
    MISSING_PARAGRAPH_RETRIES = 2
    AUTO_GLOSSARY_TERM_OVERRIDES: Dict[str, str] = {
        "wide expert parallelism": "宽专家并行",
        "wide expert parallelism (wideep)": "宽专家并行 (WideEP)",
        "wide ep": "宽专家并行",
        "wideep": "WideEP",
        "interactivity": "交互性",
        "throughput": "吞吐量",
        "time per output token (tpot)": "每个输出 Token 耗时 (TPOT)",
        "disaggregated serving": "解耦式推理服务",
        "disaggregated inference": "解耦推理",
        "disaggregated prefill": "解耦式预填充",
        "disagg prefill": "解耦式预填充",
    }

    def __init__(
        self,
        llm_provider: LLMProvider,
        project_manager: ProjectManager,
        translation_mode: str = "section",  # 默认使用章节级翻译
        max_concurrent_sections: int = 10,  # 保留兼容；跨章节按文档顺序提交
        analysis_llm_provider: Optional[LLMProvider] = None,
        user_model_override: Optional[str] = None,  # 用户指定的模型（全流程使用）
    ):
        """
        初始化批量翻译服务

        Args:
            llm_provider: LLM Provider（用于向后兼容）
            project_manager: 项目管理器
            translation_mode: 翻译模式 ("four_step" 或 "section")
            max_concurrent_sections: 兼容旧调用方；章节现按文档顺序翻译
            analysis_llm_provider: 分析专用LLM（可选）
            user_model_override: 用户指定的模型名称，如果提供则全流程使用该模型
        """
        self.llm = llm_provider
        self.project_manager = project_manager
        self.translation_mode = translation_mode
        self.max_concurrent_sections = max_concurrent_sections
        self.analysis_llm = analysis_llm_provider or llm_provider
        self.user_model_override = user_model_override
        self._phase_provider_cache: Dict[str, LLMProvider] = {}

        # 加载模型配置
        from src.core.model_config import get_model_config
        self.model_config = get_model_config()

        self.deep_analyzer = DeepAnalyzer(self.analysis_llm)
        self.context_manager = LayeredContextManager()
        self._progress_tracker = self._shared_progress_tracker
        self._run_registry = translation_run_registry
        self._artifact_service = TranslationArtifactService(self.project_manager.projects_path)

        # 覆盖已有译文的范围，由 set_retranslate_scope() 设置；默认保持历史行为。
        self._retranslate_scope: str = "resume"
        self._retranslate_section_ids: set[str] = set()

        # 懒加载翻译记忆服务
        memory_service = None
        try:
            from src.services.memory_service import TranslationMemoryService

            memory_service = TranslationMemoryService()
        except Exception as e:
            logger.warning("Failed to load TranslationMemoryService: %s", e)

        self.translator = FourStepTranslator(
            llm_provider=llm_provider,
            context_manager=self.context_manager,
            memory_service=memory_service,
            get_provider_for_phase=self._get_provider_for_phase,
        )
        # Phase 3 provider is optional and only needed after every section has
        # translated. Construct it lazily so startup does not open an unused HTTP
        # client or fail an otherwise viable run because the review model is down.
        self.quality_report_generator: Optional[QualityReportGenerator] = None

        # 创建包装方法，自动使用phase1 provider
        async def translate_section_batch_with_phase(*args, **kwargs):
            phase1_provider = self._get_provider_for_phase("phase1_draft")
            return await self._translate_section_batch(*args, **kwargs, phase1_provider=phase1_provider)

        self._section_executor = SectionTranslationExecutor(
            is_cancelled=self._is_cancelled,
            touch_progress=self._touch_progress,
            build_section_prompt_context=self._build_section_prompt_context,
            persist_section_artifact=self._persist_section_artifact,
            run_section_prescan=self._run_section_prescan,
            count_translated_paragraphs=self._count_translated_paragraphs,
            translate_section_batch=translate_section_batch_with_phase,
            apply_section_batch_translations=self._apply_section_batch_translations,
            record_section_batch_term_usage=self._record_section_batch_term_usage,
            four_step_translate_section=self.translator.translate_section,
            create_section_callback=self._create_section_callback,
            apply_four_step_translations=self._apply_four_step_translations,
            # 章节循环仅合并本次生成的段落，不覆盖并发人工编辑，也不每章
            # 全量重算进度；所有章节完成后统一聚合一次。
            merge_translation_updates=(
                self.project_manager.merge_translation_updates_locked
            ),
            commit_four_step_result=self.translator.commit_section_feedback,
            should_force_retranslate=self._should_force_retranslate,
        )

    def set_retranslate_scope(
        self,
        scope: str = "resume",
        section_ids: Optional[List[str]] = None,
    ) -> None:
        """选择本次运行覆盖已有译文的范围。

        - ``resume``（默认，历史行为）：只翻没有可用译文的段落。
        - ``section``：只重译 ``section_ids`` 列出的章节，其余章节仍走续跑。
        - ``all``：整篇重译。

        重译不会绕过段落级的版本机制——``merge_translation_updates_locked`` 仍按
        model 维度写入 ``paragraph.translations``，旧译文作为历史版本保留。
        """
        normalized = (scope or "resume").strip().lower()
        if normalized not in {"resume", "section", "all"}:
            raise ValueError(f"Unsupported retranslate scope: {scope}")
        if normalized == "section" and not section_ids:
            raise ValueError("retranslate scope 'section' requires section_ids")
        self._retranslate_scope = normalized
        self._retranslate_section_ids = set(section_ids or ())

    def _should_force_retranslate(self, section: Section) -> bool:
        scope = getattr(self, "_retranslate_scope", "resume")
        if scope == "all":
            return True
        if scope == "section":
            return section.section_id in getattr(
                self, "_retranslate_section_ids", set()
            )
        return False

    def _get_provider_for_phase(self, phase: str) -> LLMProvider:
        """
        获取指定阶段的LLM Provider

        Args:
            phase: 翻译阶段 (phase0_prescan, phase1_draft, phase2_refine, phase3_review)

        Returns:
            LLMProvider实例
        """
        llm_usage_metrics.set_phase(phase)

        # 如果用户指定了模型，全流程使用该模型
        if self.user_model_override:
            model_config = self.model_config.get_model_for_phase(phase, model_override=self.user_model_override)
            logger.info(f"Using user-specified model for {phase}: {model_config['model']}")
            return self.llm  # 用户已经通过API传入了对应的provider

        # 否则根据阶段获取不同的模型
        model_config = self.model_config.get_model_for_phase(phase)
        model_name = model_config['model']

        cached = self._phase_provider_cache.get(model_name)
        if cached is not None:
            return cached

        # 如果当前 provider 已经是目标模型，直接返回。配置使用 alias，而
        # concrete provider 往往只暴露 real model，所以两种名称都要比较。
        provider_selectors = {
            str(value).strip().lower()
            for value in (
                getattr(self.llm, "model_alias", None),
                getattr(self.llm, "model_name", None),
                getattr(self.llm, "default_model", None),
            )
            if value
        }
        expected_selectors = {str(model_name).strip().lower()}
        try:
            from src.llm.config_loader import get_config_loader

            configured_model = get_config_loader().get_model_config(model_name)
            if configured_model is not None and configured_model.real_model:
                expected_selectors.add(configured_model.real_model.strip().lower())
        except Exception:
            # Alias comparison still works for adapters and test providers.
            pass
        if provider_selectors & expected_selectors:
            self._phase_provider_cache[model_name] = self.llm
            return self.llm

        # 创建新的provider
        from src.api.utils.llm_factory import create_llm_provider
        logger.info(f"Creating provider for {phase}: {model_name} (temp={model_config['temperature']})")
        provider = create_llm_provider(provider=model_name)
        self._phase_provider_cache[model_name] = provider
        return provider

    def _get_quality_report_generator(self) -> QualityReportGenerator:
        generator = self.quality_report_generator
        if generator is None:
            generator = QualityReportGenerator(
                self._get_provider_for_phase("phase3_review")
            )
            self.quality_report_generator = generator
        return generator

    def _is_cancelled(self, project_id: str) -> bool:
        return self._run_registry.is_cancelled(project_id)

    def _clear_cancelled(self, project_id: str) -> None:
        self._run_registry.clear_cancelled(project_id)

    @classmethod
    def _get_active_run(cls, project_id: Optional[str] = None):
        return translation_run_registry.get_active_run(project_id)

    @classmethod
    def _set_active_run(
        cls,
        project_id: str,
        *,
        run_id: Optional[str],
        status: str,
        current_step: Optional[str] = None,
    ):
        return translation_run_registry.set_active_run(
            project_id,
            run_id=run_id,
            status=status,
            current_step=current_step,
        )

    @classmethod
    def _release_active_run(
        cls,
        project_id: str,
        *,
        run_id: Optional[str] = None,
        lease_id: Optional[str] = None,
    ) -> None:
        translation_run_registry.release_active_run(
            project_id,
            run_id=run_id,
            lease_id=lease_id,
        )

    @classmethod
    async def claim_translation_slot(
        cls,
        project_id: str,
        *,
        wait_timeout: float = 300.0,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        return await translation_run_registry.claim_translation_slot(
            project_id,
            wait_timeout=wait_timeout,
            poll_interval=poll_interval,
        )

    def _load_project_with_sections(self, project_id: str) -> ProjectMeta:
        """Load project and attach sections."""
        project = self.project_manager.get(project_id)
        project.sections = self.project_manager.get_sections(project_id)
        return project

    def _progress_cache(self) -> ProgressTracker:
        return getattr(self, "_progress_tracker", self._shared_progress_tracker)

    def _artifacts_root(self, project_id: str) -> Path:
        return self._artifact_service.artifacts_root(project_id)

    def _create_run_artifact_dir(self, project_id: str) -> tuple[str, Path]:
        return self._artifact_service.create_run_artifact_dir(project_id)

    def _normalize_artifact_payload(self, payload: Any) -> Any:
        return self._artifact_service.normalize_payload(payload)

    def _write_artifact_json(self, path: Path, payload: Any) -> None:
        self._artifact_service.write_json(path, payload)

    def _load_latest_analysis_snapshot(self, project_id: str) -> Optional[ArticleAnalysis]:
        """Load the most recent persisted article analysis for resume runs."""
        return self._artifact_service.load_latest_analysis_snapshot(project_id)

    def _load_latest_run_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self._artifact_service.load_latest_run_summary(project_id)

    def _load_latest_run_snapshot(
        self,
        project_id: str,
    ) -> tuple[Optional[Dict[str, Any]], Optional[RunStateSnapshot]]:
        return self._artifact_service.load_latest_run_snapshot(project_id)

    def _get_latest_run_dir(self, project_id: str) -> Optional[Path]:
        return self._artifact_service.get_latest_run_dir(project_id)

    def _infer_run_state(self, project_id: str) -> Optional[RunStateSnapshot]:
        return self._artifact_service.infer_run_state(project_id)

    def _build_source_manifest(
        self,
        project: ProjectMeta,
        project_id: str,
    ) -> Dict[str, Any]:
        return {
            "project_id": project_id,
            "title": project.title,
            "title_translation": project.title_translation,
            "source_file": project.source_file,
            "workflow_mode": self.translation_mode,
            "section_count": len(project.sections),
            "paragraph_count": sum(len(section.paragraphs) for section in project.sections),
            "generated_at": datetime.now().isoformat(),
        }

    def _build_structure_map(self, project: ProjectMeta) -> Dict[str, Any]:
        return {
            "sections": [
                {
                    "section_id": section.section_id,
                    "title": section.title,
                    "title_translation": section.title_translation,
                    "paragraph_count": len(section.paragraphs),
                    "paragraphs": [
                        {
                            "id": paragraph.id,
                            "index": paragraph.index,
                            "element_type": paragraph.element_type.value,
                            "heading_level": paragraph.heading_level,
                            "heading_chain": paragraph.heading_chain,
                            "source_preview": paragraph.source[:160],
                        }
                        for paragraph in section.paragraphs
                    ],
                }
                for section in project.sections
            ]
        }

    def _build_section_plan(
        self,
        project: ProjectMeta,
        analysis: ArticleAnalysis,
    ) -> Dict[str, Any]:
        section_roles = analysis.section_roles or {}
        sections_payload = []
        total_sections = len(project.sections)
        for index, section in enumerate(project.sections):
            understanding = section_roles.get(section.section_id)
            sections_payload.append(
                {
                    "section_id": section.section_id,
                    "title": section.title,
                    "position": f"{index + 1}/{total_sections}",
                    "paragraph_count": len(section.paragraphs),
                    "previous_section_title": (
                        project.sections[index - 1].title if index > 0 else ""
                    ),
                    "next_section_title": (
                        project.sections[index + 1].title
                        if index < total_sections - 1
                        else ""
                    ),
                    "section_role": (
                        understanding.role_in_article if understanding else ""
                    ),
                    "translation_notes": (
                        understanding.translation_notes if understanding else []
                    ),
                }
            )

        return {
            "article_theme": analysis.theme,
            "structure_summary": analysis.structure_summary,
            "translation_mode": self.translation_mode,
            "sections": sections_payload,
        }

    def _build_prompt_context_snapshot(
        self,
        analysis: ArticleAnalysis,
    ) -> Dict[str, Any]:
        return {
            "article_theme": analysis.theme,
            "structure_summary": analysis.structure_summary,
            "style": self._normalize_artifact_payload(analysis.style),
            "guidelines": analysis.guidelines,
            "challenges": self._normalize_artifact_payload(analysis.challenges),
            "terminology": [
                {
                    "term": term.term,
                    "translation": term.translation,
                    "strategy": term.strategy.value,
                    "first_occurrence_note": term.first_occurrence_note,
                    "rationale": term.rationale,
                }
                for term in analysis.terminology
            ],
        }

    def _enhanced_term_from_glossary(self, glossary_term) -> EnhancedTerm:
        return EnhancedTerm(
            term=glossary_term.original,
            translation=glossary_term.translation,
            context_meaning=glossary_term.note or "",
            strategy=glossary_term.strategy,
            first_occurrence_note=(
                glossary_term.strategy == TranslationStrategy.FIRST_ANNOTATE
            ),
        )

    def _merge_analysis_with_project_glossary(
        self,
        project_id: str,
        analysis: ArticleAnalysis,
    ) -> ArticleAnalysis:
        merged_glossary = self.project_manager.glossary_manager.load_merged(project_id)
        merged_terms: Dict[str, EnhancedTerm] = {
            term.term.lower(): term.model_copy()
            for term in analysis.terminology
        }

        for glossary_term in merged_glossary.terms:
            if glossary_term.status != "active":
                continue
            key = glossary_term.original.lower()
            existing = merged_terms.get(key)
            if existing:
                # Glossary 只覆盖 translation/strategy/first_occurrence_note，
                # 保留 analysis 提供的 context_meaning 和 rationale
                merged_terms[key] = existing.model_copy(
                    update={
                        "translation": glossary_term.translation or existing.translation,
                        "strategy": glossary_term.strategy,
                        "first_occurrence_note": (
                            glossary_term.strategy == TranslationStrategy.FIRST_ANNOTATE
                        ),
                    }
                )
            else:
                merged_terms[key] = (
                    self._enhanced_term_from_glossary(glossary_term)
                )

        analysis.terminology = list(merged_terms.values())
        return analysis

    def _normalize_auto_glossary_translation(
        self,
        original: str,
        translation: Optional[str],
    ) -> Optional[str]:
        normalized_original = (original or "").strip()
        cleaned = (translation or "").strip()
        if not normalized_original:
            return None

        override = self.AUTO_GLOSSARY_TERM_OVERRIDES.get(normalized_original.lower())
        if not override and " (" in normalized_original and normalized_original.endswith(")"):
            base_term = normalized_original.rsplit(" (", 1)[0].strip()
            override = self.AUTO_GLOSSARY_TERM_OVERRIDES.get(base_term.lower())
        if override:
            return override
        return cleaned or None

    def _build_auto_glossary_term(
        self,
        *,
        original: str,
        translation: Optional[str],
        strategy: TranslationStrategy,
        note: Optional[str],
        source: str,
    ) -> Optional[GlossaryTerm]:
        normalized_original = (original or "").strip()
        normalized_translation = self._normalize_auto_glossary_translation(
            normalized_original,
            translation,
        )
        if not normalized_original:
            return None

        resolved_strategy = strategy
        if not normalized_translation:
            normalized_translation = normalized_original
        if normalized_translation == normalized_original:
            resolved_strategy = TranslationStrategy.PRESERVE

        return GlossaryTerm(
            original=normalized_original,
            translation=normalized_translation,
            strategy=resolved_strategy,
            note=(note or "").strip() or None,
            tags=infer_glossary_tags(normalized_original),
            source=source,
            scope="project",
            status="active",
        )

    def _derive_auto_glossary_alias_terms(self, term: GlossaryTerm) -> List[GlossaryTerm]:
        original = term.original.strip()
        if " (" not in original or not original.endswith(")"):
            return []

        base, _, remainder = original.rpartition(" (")
        abbreviation = remainder[:-1].strip()
        aliases: List[GlossaryTerm] = []

        base = base.strip()
        if base:
            base_translation = term.translation or base
            suffixes = [f"({abbreviation})", f"（{abbreviation}）"]
            for suffix in suffixes:
                if base_translation.endswith(suffix):
                    base_translation = base_translation[: -len(suffix)].rstrip(" （(")
                    break
            aliases.append(
                term.model_copy(
                    update={
                        "original": base,
                        "translation": base_translation,
                    }
                )
            )

        if abbreviation and len(abbreviation) <= 16:
            aliases.append(
                term.model_copy(
                    update={
                        "original": abbreviation,
                        "translation": abbreviation,
                        "strategy": TranslationStrategy.PRESERVE,
                    }
                )
            )

        return aliases

    def _load_term_review_seed_terms(self, project_id: str) -> List[GlossaryTerm]:
        latest_path = (
            self.project_manager.projects_path
            / project_id
            / "artifacts"
            / "term-review"
            / "latest.json"
        )
        if not latest_path.exists():
            return []

        try:
            with open(latest_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            logger.warning("Failed to load term-review artifact %s: %s", latest_path, exc)
            return []

        is_current_artifact = is_current_term_review_artifact(payload)
        is_legacy_artifact = is_legacy_term_review_artifact(payload)
        if not is_current_artifact and not is_legacy_artifact:
            logger.warning(
                "Ignoring term-review artifact with unsupported schema: %s",
                latest_path,
            )
            return []
        if (
            is_current_artifact
            and payload.get("submission_status") != SUBMISSION_SUBMITTED
        ):
            return []

        raw_decisions = payload.get("decisions")
        has_submitted_decisions = isinstance(raw_decisions, list)
        if is_current_artifact and not has_submitted_decisions:
            logger.warning(
                "Ignoring submitted term-review artifact without decisions: %s",
                latest_path,
            )
            return []
        decisions_by_term = {
            re.sub(r"\s+", " ", str(decision.get("term") or "").strip()).lower(): decision
            for decision in (raw_decisions or [])
            if isinstance(decision, dict) and str(decision.get("term") or "").strip()
        }

        terms: List[GlossaryTerm] = []
        for section in payload.get("sections", []):
            for candidate in section.get("candidates", []):
                original = str(candidate.get("term") or "").strip()
                normalized_original = re.sub(r"\s+", " ", original).lower()
                decision = decisions_by_term.get(normalized_original)
                if has_submitted_decisions:
                    action = str((decision or {}).get("action") or "").strip().lower()
                    if not decision or action not in {"accept", "custom"}:
                        continue
                    translation = str(decision.get("translation") or "").strip()
                else:
                    # Only the explicitly recognized schema-less v1 shape keeps
                    # the historical auto-seed behavior.
                    translation = str(candidate.get("suggested_translation") or "").strip()
                reasons = {
                    str(reason).strip().lower()
                    for reason in (candidate.get("reasons") or [])
                    if str(reason).strip()
                }
                occurrence_count = int(candidate.get("occurrence_count") or 0)
                if not original or not translation:
                    continue
                if (
                    occurrence_count < 2
                    and "title" not in reasons
                    and "high_frequency" not in reasons
                ):
                    continue

                term = self._build_auto_glossary_term(
                    original=original,
                    translation=translation,
                    strategy=(
                        TranslationStrategy.PRESERVE
                        if translation == original
                        else TranslationStrategy.TRANSLATE
                    ),
                    note=(candidate.get("contexts") or [None])[0],
                    source="term_review_auto",
                )
                if term is None:
                    continue
                terms.append(term)
                terms.extend(self._derive_auto_glossary_alias_terms(term))

        return terms

    def _build_analysis_seed_terms(
        self,
        analysis: ArticleAnalysis,
    ) -> List[GlossaryTerm]:
        terms: List[GlossaryTerm] = []
        for term in analysis.terminology:
            normalized_original = (term.term or "").strip()
            base_original = (
                normalized_original.rsplit(" (", 1)[0].strip()
                if " (" in normalized_original and normalized_original.endswith(")")
                else normalized_original
            )
            if (
                normalized_original.lower() not in self.AUTO_GLOSSARY_TERM_OVERRIDES
                and base_original.lower() not in self.AUTO_GLOSSARY_TERM_OVERRIDES
            ):
                continue
            glossary_term = self._build_auto_glossary_term(
                original=term.term,
                translation=term.translation,
                strategy=term.strategy,
                note=term.context_meaning or term.rationale,
                source="analysis_auto",
            )
            if glossary_term is None:
                continue
            terms.append(glossary_term)
            terms.extend(self._derive_auto_glossary_alias_terms(glossary_term))
        return terms

    def _seed_project_glossary(
        self,
        project_id: str,
        analysis: ArticleAnalysis,
    ) -> Dict[str, Any]:
        glossary_manager = self.project_manager.glossary_manager
        global_glossary = glossary_manager.load_global()
        global_terms = {
            term.original.lower(): term
            for term in global_glossary.terms
            if term.status == "active"
        }
        seed_candidates = [
            *self._load_term_review_seed_terms(project_id),
            *self._build_analysis_seed_terms(analysis),
        ]

        added_terms: List[GlossaryTerm] = []
        with glossary_manager.project_lock(project_id):
            glossary = glossary_manager.load_project(project_id)
            existing_terms = {
                term.original.lower(): term
                for term in glossary.terms
                if term.status == "active"
            }
            for candidate in seed_candidates:
                key = candidate.original.lower()
                if key in existing_terms:
                    continue
                global_term = global_terms.get(key)
                if global_term is not None:
                    # 2026-08-09：**全局已有该词 → 一律不写入项目词表**。
                    # 原逻辑只在「译名与策略都相同」时跳过，一旦本次候选与全局有任何
                    # 差异就会落盘，而项目词表过去优先级高于全局，等于用翻译当时的
                    # 旧译名把全局的修正静默压回去（实测一次性覆盖了 15 条全局条目：
                    # capex 资本开支→资本支出、node 判据型→制程节点、agentic 智能体→
                    # 智能体化…）。全局词表是单一事实源：候选与全局不一致时，应当去
                    # 修全局词表，而不是在项目里另立一份。不设单篇破例的开关。
                    logger.debug(
                        "[%s] skip project-glossary seed %r: already in global glossary",
                        project_id, candidate.original,
                    )
                    continue
                glossary.add_term(candidate)
                existing_terms[key] = candidate
                added_terms.append(candidate)

            if added_terms:
                glossary_manager.save_project(project_id, glossary)

        return {
            "added": len(added_terms),
            "terms": [
                {
                    "original": term.original,
                    "translation": term.translation,
                    "strategy": term.strategy.value,
                    "source": term.source,
                }
                for term in added_terms
            ],
        }

    def _build_title_glossary_block(
        self,
        project_id: str,
        title: str,
        subtitle: Optional[str],
    ) -> str:
        merged_glossary = self.project_manager.glossary_manager.load_merged(project_id)
        selected_terms = select_glossary_terms_for_text(
            merged_glossary,
            "\n".join(filter(None, [title, subtitle or ""])),
            max_terms=12,
        )
        return render_glossary_prompt_block(
            selected_terms,
            include_title=False,
            empty_text="(无命中术语)",
        )

    def _build_section_prompt_context(
        self,
        project: ProjectMeta,
        section: Section,
        section_index: int,
        analysis: ArticleAnalysis,
    ) -> Dict[str, Any]:
        understanding = analysis.section_roles.get(section.section_id)
        total_sections = len(project.sections)

        section_role = ""
        translation_notes: list = []
        key_points: list = []
        if understanding:
            ctx = build_section_context_payload(understanding)
            section_role = ctx.get("role", "")
            translation_notes = ctx.get("translation_notes", [])
            key_points = ctx.get("key_points", [])

        return {
            "section_id": section.section_id,
            "section_title": section.title,
            "section_title_translation": section.title_translation,
            "section_position": f"{section_index + 1}/{total_sections}",
            "article_theme": analysis.theme,
            "structure_summary": analysis.structure_summary,
            "target_audience": analysis.style.target_audience,
            "translation_voice": analysis.style.translation_voice,
            "previous_section_title": (
                project.sections[section_index - 1].title if section_index > 0 else ""
            ),
            "next_section_title": (
                project.sections[section_index + 1].title
                if section_index < total_sections - 1
                else ""
            ),
            "section_role": section_role,
            "translation_notes": translation_notes,
            "key_points": key_points,
            "guidelines": build_translation_guidelines(analysis.guidelines),
            "article_challenges": build_article_challenge_payload(analysis.challenges),
            "terminology": build_glossary_entries_from_terms(analysis.terminology),
        }

    def _persist_section_artifact(
        self,
        run_dir: Optional[Path],
        category: str,
        section_id: str,
        payload: Any,
    ) -> None:
        if run_dir is None:
            return
        self._write_artifact_json(run_dir / category / f"{section_id}.json", payload)

    def _notify_progress(
        self,
        callback: Optional[Callable[[str, int, int], None]],
        step: str,
        current: int,
        total: int,
    ) -> None:
        """Safely notify progress callback when provided."""
        if callback:
            callback(step, current, total)

    def _touch_progress(
        self,
        progress: TranslationProgress,
        *,
        step: Optional[str] = None,
        current_section: Optional[str] = None,
    ) -> None:
        if step is not None:
            progress.current_step = step
        if current_section is not None:
            progress.current_section = current_section
        self._progress_cache().touch(progress)
        if progress.run_id:
            self._artifact_service.write_run_state(
                progress.project_id,
                progress.run_id,
                {
                    "status": progress.final_status or "processing",
                    **progress.to_dict(),
                },
            )

    def _set_active_status(
        self,
        project_id: str,
        project: ProjectMeta,
        status: ProjectStatus,
    ) -> None:
        """Transition to active translation status when allowed."""
        if self._can_transition_to_active_status(project.status):
            project.status = status
            self._save_meta(project_id, project)

    async def translate_project(
        self,
        project_id: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        on_term_conflict: Optional[
            Callable[[TermConflict], Awaitable[Dict[str, Any]]]
        ] = None,
    ) -> Dict:
        """
        翻译整个项目

        流程:
        1. Phase 0: 深度分析全文
        2. 逐章节翻译（四步法）
        3. 保存翻译结果
        4. 更新项目状态

        Args:
            project_id: 项目ID
            on_progress: 进度回调 (step_name, current, total)

        Returns:
            Dict: 翻译结果统计
        """
        # 登记主事件循环：四步法经 asyncio.to_thread 在工作线程执行，后台学习协程
        # 需经此循环用 run_coroutine_threadsafe 回投（见 memory_service._spawn_background）。
        try:
            from src.services.memory_service import TranslationMemoryService

            TranslationMemoryService.register_loop()
        except Exception:
            pass

        # 加载项目
        project = self._load_project_with_sections(project_id)
        original_status = project.status
        self.context_manager.reset_all()
        self.translator.reset_feedback_history()

        project_start_time = time.monotonic()

        # 统计总数
        total_paragraphs = sum(len(s.paragraphs) for s in project.sections)
        total_sections = len(project.sections)
        # 将被重译的章节，其已有译文不计入起始进度——否则「整篇重译」一开机
        # 进度条就是 100%，而且下面的 is_resume_run 会把重译误判成续跑。
        retranslated_ids = {
            section.section_id
            for section in project.sections
            if self._should_force_retranslate(section)
        }
        countable_sections = [
            section
            for section in project.sections
            if section.section_id not in retranslated_ids
        ]
        existing_translated = self._count_project_translated_paragraphs(
            countable_sections
        )
        existing_translated_sections = sum(
            1
            for section in countable_sections
            if section.paragraphs
            and self._count_translated_paragraphs(section)
            == len(section.paragraphs)
        )
        is_resume_run = (
            not retranslated_ids and 0 < existing_translated < total_paragraphs
        )
        previous_summary = (
            self._artifact_service.load_latest_run_summary(project_id)
            if is_resume_run
            else None
        )
        resume_from_run_id = None
        if previous_summary:
            resume_from_run_id = (
                str(previous_summary.get("run_id") or "").strip() or None
            )

        # 创建进度跟踪
        progress = self._progress_tracker.create(
            project_id=project_id,
            total_sections=total_sections,
            total_paragraphs=total_paragraphs,
            original_status=original_status,
        )
        progress.translated_paragraphs = existing_translated
        progress.translated_sections = existing_translated_sections
        if retranslated_ids:
            progress.current_step = (
                "整篇重译"
                if self._retranslate_scope == "all"
                else f"重译 {len(retranslated_ids)} 个章节"
            )
        elif is_resume_run:
            progress.current_step = (
                f"断点续译：已完成 {existing_translated}/{total_paragraphs} 段"
            )

        run_id, run_dir = self._create_run_artifact_dir(project_id)
        llm_usage_metrics.start_run(run_id, project_id=project_id)
        progress.run_id = run_id
        self._touch_progress(progress)
        self._set_active_run(
            project_id,
            run_id=run_id,
            status="processing",
            current_step=progress.current_step,
        )
        self._write_artifact_json(
            run_dir / "source-manifest.json",
            self._build_source_manifest(project, project_id),
        )
        self._write_artifact_json(
            run_dir / "structure-map.json",
            self._build_structure_map(project),
        )
        if is_resume_run:
            self._write_artifact_json(
                run_dir / "resume-checkpoint.json",
                {
                    "resumed": True,
                    "source_run_id": resume_from_run_id,
                    "translated_paragraphs": existing_translated,
                    "total_paragraphs": total_paragraphs,
                    "remaining_paragraphs": (
                        total_paragraphs - existing_translated
                    ),
                },
            )

        # 更新项目状态为"分析中"
        self._set_active_status(project_id, project, ProjectStatus.ANALYZING)

        # 已翻译的段落计数器
        translated_count = existing_translated

        def finalize_cancelled_result(
            message: str = "Translation cancelled by user",
        ) -> Dict[str, Any]:
            actual_translated = self._count_project_translated_paragraphs(
                project.sections
            )
            progress.finished_at = datetime.now()
            progress.translated_paragraphs = actual_translated
            progress.translated_sections = sum(
                1
                for section in project.sections
                if self._count_translated_paragraphs(section) == len(section.paragraphs)
                and len(section.paragraphs) > 0
            )
            progress.final_status = "cancelled"
            self._touch_progress(progress, step="已取消")
            project.status = original_status
            self._save_meta(project_id, project)

            usage_summary = llm_usage_metrics.finish_run(run_id)
            result = {
                "project_id": project_id,
                "status": "cancelled",
                "message": message,
                "total_sections": progress.total_sections,
                "translated_sections": progress.translated_sections,
                "total_paragraphs": progress.total_paragraphs,
                "translated_paragraphs": actual_translated,
                "translation_mode": self.translation_mode,
                "resumed": is_resume_run,
                "resume_from_run_id": resume_from_run_id,
                "checkpoint_paragraphs": existing_translated,
                "error_count": len(progress.errors),
                "errors": progress.errors,
                "started_at": progress.started_at.isoformat(),
                "finished_at": progress.finished_at.isoformat(),
                "run_id": run_id,
                "artifacts_path": str(run_dir),
                "api_calls": usage_summary["api_calls"],
                "llm_usage": usage_summary,
                "elapsed_seconds": round(time.monotonic() - project_start_time, 1),
            }
            self._write_artifact_json(run_dir / "run-summary.json", result)
            self._clear_cancelled(project_id)
            self._release_active_run(project_id, run_id=run_id)
            return result

        try:
            # Phase 0: 深度分析全文
            logger.info(f"[{project_id}] Starting Phase 0: Deep Analysis")
            phase0_step = "恢复分析上下文" if is_resume_run else "深度分析全文"
            self._touch_progress(progress, step=phase0_step)
            self._notify_progress(
                on_progress, phase0_step, translated_count, total_paragraphs
            )

            # 获取Phase 0专用的provider
            phase0_provider = self._get_provider_for_phase("phase0_prescan")
            phase0_analyzer = DeepAnalyzer(phase0_provider)

            analysis = None
            if existing_translated > 0:
                analysis = self._load_latest_analysis_snapshot(project_id)
                if analysis is not None:
                    logger.info(
                        "[%s] Reusing persisted analysis snapshot for resume run",
                        project_id,
                    )

            if analysis is None:
                analysis = phase0_analyzer.analyze(
                    project.sections,
                    should_cancel=lambda: self._is_cancelled(project_id),
                )
            glossary_seed_result = self._seed_project_glossary(project_id, analysis)
            analysis = self._merge_analysis_with_project_glossary(project_id, analysis)

            # 设置分析结果到上下文管理器
            self.context_manager.set_article_analysis(analysis)
            self.context_manager.add_terms_from_analysis(analysis.terminology)

            # 从持久化快照建立运行时上下文。后续每章乐观合并后都会重建，
            # 确保未落盘的 AI 草稿不会影响下一章。
            self._rebuild_persisted_translation_context(project.sections)

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            self._write_artifact_json(run_dir / "analysis.json", analysis)
            self._write_artifact_json(
                run_dir / "glossary-seed.json",
                glossary_seed_result,
            )
            self._write_artifact_json(
                run_dir / "section-plan.json",
                self._build_section_plan(project, analysis),
            )
            self._write_artifact_json(
                run_dir / "prompt-context.json",
                self._build_prompt_context_snapshot(analysis),
            )

            # 翻译标题和元信息
            logger.info(f"[{project_id}] Translating title and metadata")
            self._touch_progress(progress, step="翻译标题")
            self._notify_progress(
                on_progress, "翻译标题", translated_count, total_paragraphs
            )
            await self._translate_title_and_metadata(project, analysis)

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            # 翻译章节标题
            logger.info(f"[{project_id}] Translating section titles")
            self._touch_progress(progress, step="翻译章节标题")
            self._notify_progress(
                on_progress, "翻译章节标题", translated_count, total_paragraphs
            )
            await self._translate_section_titles(project_id, project, analysis)

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            logger.info(f"[{project_id}] Translating source metadata")
            self._touch_progress(progress, step="翻译来源说明")
            self._notify_progress(
                on_progress, "翻译来源说明", translated_count, total_paragraphs
            )
            SourceMetadataTranslationService(
                self.project_manager,
                self.llm,
            ).translate_project_sources(
                project_id,
                sections=project.sections,
                artifact_dir=run_dir,
            )
            # Metadata/title writes merge into fresh section snapshots. Reload
            # before body translation so prompt context also sees any manual
            # edits made while the earlier LLM stages were running.
            project.sections = self.project_manager.get_sections(project_id)

            # 更新项目状态为"翻译中"
            self._set_active_status(project_id, project, ProjectStatus.IN_PROGRESS)

            # Prescan 必须先覆盖全部待译章节，再按文档顺序逐章翻译和提交。
            # 四步法与章节模式都依赖前文章节、术语首现和已提交反馈；跨章节
            # 并发会让这些状态取决于网络返回顺序。
            logger.info(
                "[%s] Starting ordered section translation (mode: %s)",
                project_id,
                self.translation_mode,
            )

            # 收集所有翻译结果用于一致性审查
            all_translations = {}
            consistency_report = None

            results = await self._translate_sections_in_document_order(
                project_id=project_id,
                project=project,
                analysis=analysis,
                run_dir=run_dir,
                progress=progress,
                on_progress=on_progress,
                on_term_conflict=on_term_conflict,
                total_paragraphs=total_paragraphs,
            )

            # All section deltas are persisted without per-section progress
            # scans. Aggregate once, then reload the canonical snapshots so
            # later reporting/export sees concurrent manual edits rather than
            # generated in-memory candidates that lost a conflict.
            self.project_manager.update_progress(project_id)
            project.sections = self.project_manager.get_sections(project_id)

            # 处理结果
            for i, result in enumerate(results):
                section = project.sections[i]

                # 检查是否取消
                if self._is_cancelled(project_id):
                    logger.info(f"[{project_id}] Translation cancelled by user")
                    return finalize_cancelled_result()

                # 处理异常
                if isinstance(result, Exception):
                    error_msg = f"Failed to translate section {section.section_id}: {str(result)}"
                    logger.error(f"[{project_id}] {error_msg}")
                    self._progress_tracker.record_error(
                        progress, error_msg, section.section_id
                    )
                    continue

                # 处理取消
                if result.get("cancelled"):
                    logger.info(f"[{project_id}] Section {section.section_id} cancelled")
                    continue

                # 处理跳过的章节
                if result.get("skipped"):
                    all_translations[section.section_id] = result["translations"]

                    self._notify_progress(
                        on_progress,
                        f"跳过: {section.title} (已翻译)",
                        translated_count,
                        total_paragraphs,
                    )
                    logger.info(
                        f"[{project_id}] Skipped section {section.section_id}: "
                        f"all {result['paragraph_count']} paragraphs already translated"
                    )
                    continue

                # 处理错误
                if "error" in result:
                    error_msg = result["error"]
                    logger.error(f"[{project_id}] {error_msg}")
                    self._progress_tracker.record_error(
                        progress, error_msg, section.section_id
                    )
                    continue

                # 处理成功翻译的章节
                all_translations[section.section_id] = result["translations"]

                # 四步法降级（反思/润色异常回落裸初译）也要记一笔，否则 run-summary
                # 的 error_count 为 0，未经润色的章节完全不可见（审计 LC7）
                if result.get("degraded"):
                    degraded_message = (
                        f"Section {section.section_id} degraded to draft translation: "
                        f"{result.get('degraded_reason') or 'unknown reason'}"
                    )
                    logger.warning("[%s] %s", project_id, degraded_message)
                    self._progress_tracker.record_error(
                        progress,
                        degraded_message,
                        section.section_id,
                    )

                conflict_ids = result.get("conflict_paragraph_ids", [])
                if conflict_ids:
                    conflict_message = (
                        "Skipped stale AI results for paragraphs changed during "
                        f"translation: {', '.join(conflict_ids)}"
                    )
                    logger.info(
                        "[%s] %s",
                        project_id,
                        conflict_message,
                    )
                    self._progress_tracker.record_error(
                        progress,
                        conflict_message,
                        section.section_id,
                    )

                # 更新进度
                section_paragraph_count = result["paragraph_count"]
                translated_in_section = result["translated_before"]
                translated_after_section = result["translated_after"]
                translated_delta = max(
                    translated_after_section - translated_in_section,
                    0,
                )

                if (
                    translated_after_section == section_paragraph_count
                    and section_paragraph_count > 0
                ):
                    progress.translated_sections += 1

                translated_count += translated_delta
                progress.translated_paragraphs += translated_delta

                # 发送章节完成进度
                self._notify_progress(
                    on_progress,
                    f"完成: {section.title}",
                    translated_count,
                    total_paragraphs,
                )

                logger.info(
                    f"[{project_id}] Section {section.section_id} completed: "
                    f"{section_paragraph_count} paragraphs"
                )

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            # Phase 3: 质量报告生成
            logger.info(f"[{project_id}] Starting Phase 3: Quality Report Generation")
            self._touch_progress(progress, step="质量报告生成")
            self._notify_progress(
                on_progress, "质量报告生成", translated_count, total_paragraphs
            )

            quality_report = None
            try:
                llm_usage_metrics.set_phase("phase3_review")
                quality_report = self._get_quality_report_generator().generate_report(
                    sections=project.sections,
                    translations=all_translations,
                    article_analysis=analysis,
                )

                # 记录质量报告结果
                logger.info(
                    f"[{project_id}] Quality report generated: "
                    f"{quality_report.summary.total_issues} issues found "
                    f"(H:{quality_report.summary.high_severity_count}, "
                    f"M:{quality_report.summary.medium_severity_count}, "
                    f"L:{quality_report.summary.low_severity_count}), "
                    f"overall score: {quality_report.summary.overall_score}"
                )

                self._write_artifact_json(
                    run_dir / "quality_report.json",
                    quality_report.to_dict(),
                )

            except Exception as e:
                logger.error(f"[{project_id}] Quality report generation failed: {str(e)}")
                self._write_artifact_json(
                    run_dir / "quality_report.json",
                    {"error": str(e)},
                )
                # 质量报告生成失败不影响翻译完成状态

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            # 翻译完成
            actual_translated = self._count_project_translated_paragraphs(
                project.sections
            )
            translation_complete = (
                total_paragraphs > 0 and actual_translated >= total_paragraphs
            )

            export_report = {
                "generated_at": datetime.now().isoformat(),
                "translation_mode": self.translation_mode,
                "markdown": {
                    "path": str(
                        self.project_manager.get_export_path(
                            project_id,
                            format="zh",
                        )
                    ),
                    "generated": False,
                },
            }
            try:
                markdown_output = self.project_manager.export_markdown(
                    project_id, include_source=False
                )
                export_report["markdown"]["generated"] = True
                export_report["markdown"]["bytes"] = len(markdown_output.encode("utf-8"))
            except ExportBlockedError as blocked_exc:
                # QA 阻断：译文已落盘到 *_zh.blocked.md，用户拿得到可交付文本，
                # 属于「已完成 + 待复核」，不能因此把整轮翻译标成未完成（审计 RR6）
                export_report["markdown"]["error"] = str(blocked_exc)
                export_report["markdown"]["blocked"] = True
                blocked_path = getattr(blocked_exc, "blocked_path", None)
                if blocked_path:
                    export_report["markdown"]["blocked_path"] = str(blocked_path)
                logger.warning(
                    "[%s] Markdown export blocked by QA: %s",
                    project_id,
                    blocked_exc,
                )
            except Exception as export_exc:
                export_report["markdown"]["error"] = str(export_exc)

            is_complete = translation_complete and (
                export_report["markdown"]["generated"]
                or export_report["markdown"].get("blocked", False)
            )

            progress.finished_at = datetime.now()
            progress.translated_paragraphs = actual_translated
            progress.translated_sections = sum(
                1
                for section in project.sections
                if self._count_translated_paragraphs(section) == len(section.paragraphs)
                and len(section.paragraphs) > 0
            )
            progress.final_status = "completed" if is_complete else "incomplete"
            self._touch_progress(
                progress,
                step="completed" if is_complete else "incomplete",
            )
            project.status = (
                self._final_status_after_success(original_status)
                if is_complete
                else ProjectStatus.IN_PROGRESS
            )
            self._save_meta(project_id, project)

            self._write_artifact_json(
                run_dir / "markdown-export-report.json",
                export_report,
            )

            usage_summary = llm_usage_metrics.finish_run(run_id)
            logger.info(
                "[%s] Translation completed: %d API calls, %.0fs elapsed",
                project_id,
                usage_summary["api_calls"],
                time.monotonic() - project_start_time,
            )
            if not is_complete:
                logger.warning(
                    f"[{project_id}] Translation incomplete: "
                    f"{actual_translated}/{total_paragraphs} paragraphs usable"
                )

            # 构建返回结果（包含一致性报告）
            result = {
                "project_id": project_id,
                "status": "completed" if is_complete else "incomplete",
                "total_sections": progress.total_sections,
                "translated_sections": progress.translated_sections,
                "total_paragraphs": progress.total_paragraphs,
                "translated_paragraphs": actual_translated,
                "translation_mode": self.translation_mode,
                "resumed": is_resume_run,
                "resume_from_run_id": resume_from_run_id,
                "checkpoint_paragraphs": existing_translated,
                "error_count": len(progress.errors),
                "errors": progress.errors,
                "started_at": progress.started_at.isoformat(),
                "finished_at": progress.finished_at.isoformat(),
                "run_id": run_id,
                "artifacts_path": str(run_dir),
                "export": export_report,
                "api_calls": usage_summary["api_calls"],
                "llm_usage": usage_summary,
                "elapsed_seconds": round(time.monotonic() - project_start_time, 1),
            }

            # 注意：一致性审查已从本链路移除。此前残留的 `if consistency_report:`
            # 消费代码引用了一个从未赋值的变量，会在每次成功翻译后抛 NameError，
            # 导致整个 run 被误判为 failed。已删除该死代码。

            self._write_artifact_json(run_dir / "run-summary.json", result)

            self._clear_cancelled(project_id)
            self._release_active_run(project_id, run_id=run_id)
            return result

        except Exception as e:
            if self._is_cancelled(project_id) or "cancelled" in str(e).lower():
                logger.info(
                    "[%s] Translation cancelled during in-flight operation: %s",
                    project_id,
                    e,
                )
                return finalize_cancelled_result(str(e))
            logger.error(f"[{project_id}] Translation failed: {str(e)}")
            self._progress_tracker.record_error(progress, str(e))
            progress.finished_at = datetime.now()
            progress.final_status = "failed"
            self._touch_progress(progress, step="failed")

            # 更新项目状态为失败
            project.status = original_status
            self._save_meta(project_id, project)

            usage_summary = llm_usage_metrics.finish_run(run_id)
            failure_result = {
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
                "errors": progress.errors,
                "translation_mode": self.translation_mode,
                "resumed": is_resume_run,
                "resume_from_run_id": resume_from_run_id,
                "checkpoint_paragraphs": existing_translated,
                "run_id": run_id,
                "artifacts_path": str(run_dir),
                "api_calls": usage_summary["api_calls"],
                "llm_usage": usage_summary,
                "elapsed_seconds": round(time.monotonic() - project_start_time, 1),
            }
            self._write_artifact_json(run_dir / "run-summary.json", failure_result)
            self._clear_cancelled(project_id)
            self._release_active_run(project_id, run_id=run_id)
            return failure_result

    async def _translate_sections_in_document_order(
        self,
        *,
        project_id: str,
        project: ProjectMeta,
        analysis: ArticleAnalysis,
        run_dir: Path,
        progress: TranslationProgress,
        on_progress: Optional[Callable[[str, int, int], None]],
        on_term_conflict: Optional[
            Callable[[TermConflict], Awaitable[Dict[str, Any]]]
        ],
        total_paragraphs: int,
    ) -> List[Any]:
        """Prescan all sections, then generate and persist them in document order."""
        planned_section_ids = [
            section.section_id
            for section in project.sections
        ]

        logger.info(
            "[%s] Prescanning %d sections before translation",
            project_id,
            len(planned_section_ids),
        )
        for section_id in planned_section_ids:
            if self._is_cancelled(project_id):
                return []
            section = next(
                (
                    candidate
                    for candidate in project.sections
                    if candidate.section_id == section_id
                ),
                None,
            )
            if section is None:
                continue
            await self._section_executor.prescan(
                project_id=project_id,
                section=section,
                run_dir=run_dir,
                progress=progress,
                on_term_conflict=on_term_conflict,
            )

        results: List[Any] = []
        for section_id in planned_section_ids:
            if self._is_cancelled(project_id):
                break

            # Refresh before generation so manual edits made during prescan or a
            # previous chapter's LLM call are part of the optimistic snapshot.
            project.sections = self.project_manager.get_sections(project_id)
            section_index = next(
                (
                    index
                    for index, candidate in enumerate(project.sections)
                    if candidate.section_id == section_id
                ),
                None,
            )
            if section_index is None:
                results.append(
                    RuntimeError(
                        f"Section disappeared during translation: {section_id}"
                    )
                )
                continue

            # Runtime context for this chapter contains only the canonical
            # document prefix. Persisted future chapters must not suppress a
            # FIRST_ANNOTATE occurrence in an earlier chapter.
            self._rebuild_persisted_translation_context(
                project.sections[: section_index + 1]
            )
            section = project.sections[section_index]
            try:
                result = await self._translate_single_section(
                    project_id=project_id,
                    section=section,
                    section_index=section_index,
                    total_sections=len(project.sections),
                    all_sections=project.sections,
                    analysis=analysis,
                    run_dir=run_dir,
                    progress=progress,
                    on_progress=on_progress,
                    on_term_conflict=on_term_conflict,
                    project=project,
                    total_paragraphs=total_paragraphs,
                    prescan_completed=True,
                    translated_before_project=(
                        self._count_project_translated_paragraphs(
                            project.sections
                        )
                    ),
                )
            except Exception as exc:
                result = exc
            results.append(result)

            # The four-step translator records provisional draft context while
            # generating. Replace it after every merge (including conflicts and
            # failures) with the latest persisted prefix before the next chapter.
            project.sections = self.project_manager.get_sections(project_id)
            persisted_index = next(
                (
                    index
                    for index, candidate in enumerate(project.sections)
                    if candidate.section_id == section_id
                ),
                section_index,
            )
            self._rebuild_persisted_translation_context(
                project.sections[: persisted_index + 1]
            )

        return results

    async def _translate_single_section(
        self,
        project_id: str,
        section: Section,
        section_index: int,
        total_sections: int,
        all_sections: List[Section],
        analysis: ArticleAnalysis,
        run_dir: Path,
        progress: TranslationProgress,
        on_progress: Optional[Callable[[str, int, int], None]],
        on_term_conflict: Optional[Callable[[TermConflict], Awaitable[Dict[str, Any]]]],
        project: ProjectMeta,
        total_paragraphs: int,
        prescan_completed: bool = False,
        translated_before_project: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self._section_executor.translate(
            project_id=project_id,
            section=section,
            section_index=section_index,
            total_sections=total_sections,
            all_sections=all_sections,
            analysis=analysis,
            run_dir=run_dir,
            progress=progress,
            on_progress=on_progress,
            on_term_conflict=on_term_conflict,
            project=project,
            total_paragraphs=total_paragraphs,
            translation_mode=self.translation_mode,
            translation_mode_section=self.TRANSLATION_MODE_SECTION,
            prescan_completed=prescan_completed,
            translated_before_project=translated_before_project,
        )

    async def _run_section_prescan(
        self,
        project_id: str,
        section: Section,
        progress: TranslationProgress,
        on_term_conflict: Optional[
            Callable[[TermConflict], Awaitable[Dict[str, Any]]]
        ] = None,
    ) -> Optional[Any]:
        """Run optional section prescan and record terminology conflicts."""
        if not hasattr(self.translator, "prescan_section"):
            return None

        try:
            conflicts: List[TermConflict] = []

            def record_conflict(conflict: TermConflict) -> None:
                conflicts.append(conflict)
                progress.errors.append(
                    {
                        "type": "term_conflict",
                        "term": conflict.term,
                        "existing": conflict.existing_translation,
                        "new": conflict.new_translation,
                        "existing_note": conflict.existing_note,
                        "new_note": conflict.new_note,
                        "section_id": section.section_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            # prescan_section 是同步阻塞 LLM 调用。使用隔离的有界线程池，且给
            # 整个预扫描设置硬预算；传输层即使未按自身 timeout 返回，也不会
            # 永久卡住整篇翻译或耗尽通用请求线程池。
            scan_terms = getattr(self.translator, "scan_section_terms", None)
            apply_prescan = getattr(self.translator, "apply_section_prescan", None)
            if callable(scan_terms) and callable(apply_prescan):
                # Only the pure network/parse phase runs in the abandonable
                # worker. Shared terminology is committed below, after the call
                # returned inside its budget.
                prescan_result = await asyncio.wait_for(
                    run_llm_blocking(scan_terms, section=section),
                    timeout=self.PRESCAN_TIMEOUT_SECONDS,
                )
                if prescan_result is not None:
                    prescan_result = apply_prescan(
                        prescan_result,
                        on_conflict=record_conflict,
                    )
            else:
                # Compatibility path for test doubles and custom translators.
                prescan_result = await asyncio.wait_for(
                    run_llm_blocking(
                        self.translator.prescan_section,
                        section=section,
                        on_conflict=record_conflict,
                    ),
                    timeout=self.PRESCAN_TIMEOUT_SECONDS,
                )
            if on_term_conflict:
                for conflict in conflicts:
                    resolution_data = await on_term_conflict(conflict)
                    resolution = TermConflictResolution(
                        term=conflict.term,
                        chosen_translation=(
                            resolution_data.get("chosen_translation")
                            or conflict.existing_translation
                            or conflict.new_translation
                        ),
                        apply_to_all=resolution_data.get("apply_to_all", True),
                    )
                    self.context_manager.resolve_conflict(resolution)
            if prescan_result:
                logger.info(
                    f"[{project_id}] Section {section.section_id} prescan: "
                    f"{len(prescan_result.new_terms)} new terms found"
                )
            return prescan_result
        except TimeoutError:
            progress.errors.append(
                {
                    "type": "prescan_timeout",
                    "section_id": section.section_id,
                    "timeout_seconds": self.PRESCAN_TIMEOUT_SECONDS,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            logger.warning(
                "[%s] Section %s prescan timed out after %ss; continuing",
                project_id,
                section.section_id,
                self.PRESCAN_TIMEOUT_SECONDS,
            )
            return None
        except Exception as exc:
            logger.warning(
                f"[{project_id}] Section {section.section_id} prescan skipped due to error: {exc}"
            )
            return None

    def _count_translated_paragraphs(self, section: Section) -> int:
        """Count paragraphs that already have a usable translation."""
        return sum(
            1
            for paragraph in section.paragraphs
            if paragraph.has_usable_translation()
        )

    def _count_project_translated_paragraphs(self, sections: List[Section]) -> int:
        """Count paragraphs with usable translations across the whole project."""
        return sum(
            self._count_translated_paragraphs(section)
            for section in sections
        )

    def _rebuild_persisted_translation_context(
        self,
        sections: List[Section],
    ) -> None:
        """Replace provisional context with a canonical persisted section prefix."""
        analysis = self.context_manager.article_analysis
        terms = list(analysis.terminology) if analysis else []
        records: List[tuple[str, str, str, Dict[str, str]]] = []

        for section in sections:
            for paragraph in section.paragraphs:
                if not paragraph.has_usable_translation():
                    continue
                translation = paragraph.best_translation_text(
                    fallback_to_source=False
                )
                if not translation:
                    continue
                source = paragraph.source or ""
                terms_used = {
                    term.term: term.translation
                    for term in terms
                    if term.translation
                    and _count_term_occurrences(source, term.term) > 0
                }
                records.append(
                    (
                        section.section_id,
                        source,
                        translation,
                        terms_used,
                    )
                )

        self.context_manager.replace_translation_history(records)

    def _prepopulate_term_tracker(self, project: ProjectMeta) -> None:
        """Scan already-translated paragraphs to pre-fill the term usage tracker.

        This ensures that when resuming a partially translated project,
        ``first_annotate`` / ``preserve_annotate`` terms from previously
        translated sections are correctly marked as already used.
        """
        analysis = self.context_manager.article_analysis
        if not analysis:
            return

        # Collect terms that need first-occurrence tracking
        tracked = [
            t
            for t in analysis.terminology
            if t.strategy
            in (TranslationStrategy.FIRST_ANNOTATE, TranslationStrategy.PRESERVE_ANNOTATE)
        ]
        if not tracked:
            return

        for section in project.sections:
            for para in section.paragraphs:
                if not para.has_usable_translation():
                    continue
                source = para.source or ""
                if not source:
                    continue
                for term in tracked:
                    if self.context_manager.has_term_usage(term.term):
                        continue  # already recorded
                    if _count_term_occurrences(source, term.term) > 0:
                        self.context_manager.record_term_usage(
                            term.term,
                            term.translation or term.term,
                            section.section_id,
                        )

    def _apply_section_batch_translations(
        self,
        section: Section,
        translations: List[Dict[str, str]],
    ) -> List[str]:
        """Apply section-mode translations to paragraph objects and return collected texts."""
        paragraph_map = {paragraph.id: paragraph for paragraph in section.paragraphs}
        collected = []

        for trans_item in translations:
            para_id = trans_item.get("id")
            translation = trans_item.get("translation", "")
            if not isinstance(translation, str) or not translation.strip():
                raise ValueError(f"Empty translation returned for paragraph {para_id}")

            paragraph = paragraph_map.get(para_id)
            if paragraph:
                payload = build_translation_payload(
                    paragraph,
                    translation,
                    token_repairer=self._repair_format_tokens,
                )
                apply_translation_payload(paragraph, payload, "pro")
                paragraph.status = ParagraphStatus.TRANSLATED
                collected.append(payload.text)

        return collected

    def _record_section_batch_term_usage(
        self,
        section: Section,
        analysis: ArticleAnalysis,
    ) -> None:
        """Update the tracker after section-batch translation for article-wide first-use logic."""
        tracked_terms = [
            term
            for term in analysis.terminology
            if term.strategy
            in (
                TranslationStrategy.FIRST_ANNOTATE,
                TranslationStrategy.PRESERVE_ANNOTATE,
            )
        ]
        if not tracked_terms:
            return

        for paragraph in section.paragraphs:
            if not paragraph.has_usable_translation():
                continue

            source = paragraph.source or ""
            if not source:
                continue

            for term in tracked_terms:
                if self.context_manager.has_term_usage(term.term):
                    continue
                if _count_term_occurrences(source, term.term) > 0:
                    self.context_manager.record_term_usage(
                        term.term,
                        term.translation or term.term,
                        section.section_id,
                    )

    def _apply_four_step_translations(self, section: Section, result) -> None:
        """Apply four-step translations and optional AI insight to section paragraphs."""
        outputs = getattr(result, "translation_outputs", None) or []
        for index, translation in enumerate(result.translations):
            if index >= len(section.paragraphs):
                continue

            paragraph = section.paragraphs[index]
            payload = outputs[index] if index < len(outputs) else None
            if paragraph.inline_elements:
                candidate_text = (
                    payload.get("tokenized_text")
                    if payload and isinstance(payload.get("tokenized_text"), str)
                    else translation
                )
                translation_payload = build_translation_payload(
                    paragraph,
                    candidate_text,
                    token_repairer=self._repair_format_tokens,
                )
            else:
                translation_payload = (
                    TranslationPayload(
                        text=translation,
                        tokenized_text=payload.get("tokenized_text"),
                        format_issues=list(payload.get("format_issues") or []),
                    )
                    if payload
                    else build_translation_payload(paragraph, translation)
                )
            apply_translation_payload(
                paragraph,
                translation_payload,
                "pro",
            )
            paragraph.status = ParagraphStatus.TRANSLATED

            if paragraph.ai_insight is None:
                paragraph.ai_insight = self._build_ai_insight(result, paragraph, index)

    def _repair_format_tokens(
        self,
        paragraph: Paragraph,
        translated_tokenized_text: str,
        issues: List[str],
    ) -> Optional[str]:
        if not paragraph.inline_elements:
            return None

        prepared = build_translation_input(paragraph)
        return self.llm.repair_format_tokens(
            source_text=prepared.tokenized_text or prepared.text,
            translated_text=translated_tokenized_text,
            format_tokens=[
                {
                    "id": element.span_id,
                    "type": element.type,
                    "text": element.text,
                }
                for element in (paragraph.inline_elements or [])
                if element.span_id
            ],
            issues=issues,
        )

    def _collect_section_translations(self, section: Section) -> List[str]:
        """Collect best-effort translation text for a section."""
        return [
            paragraph.best_translation_text()
            for paragraph in section.paragraphs
        ]

    def _create_section_callback(
        self,
        section_title: str,
        parent_callback: Optional[Callable[[str, int, int], None]],
        base_count: int = 0,
        total_paragraphs: int = 0,
        section_paragraphs: int = 0,
    ) -> Callable[[str, int, int], None]:
        """创建章节进度回调

        Args:
            section_title: 章节标题
            parent_callback: 父级回调
            base_count: 已翻译的段落基数（传递给父回调的 current）
            total_paragraphs: 总段落数（传递给父回调的 total）
            section_paragraphs: 当前章节段落数（用于估算章节内进度）
        """

        def callback(step: str, current: int, total: int):
            if parent_callback:
                if total > 0 and section_paragraphs > 0 and total_paragraphs > 0:
                    estimated_current = base_count + int(
                        (current / total) * section_paragraphs
                    )
                    effective_total = total_paragraphs
                    progress_current = min(estimated_current, effective_total)
                else:
                    progress_current = base_count
                    effective_total = total_paragraphs

                parent_callback(
                    f"{section_title} - {step}",
                    progress_current,
                    effective_total,
                )

        return callback

    def _build_ai_insight(self, result, paragraph: Paragraph, index: int) -> Dict:
        """
        构建AI透明度数据

        从四步法结果中提取透明度信息
        """
        insight = {
            "overall_score": 0.0,
            "is_excellent": False,
            "applied_terms": [],
            "style": "专业技术",
            "steps": {
                "understand": bool(result.understanding),
                "translate": True,
                "reflect": bool(result.reflection),
                "refine": bool(
                    result.reflection and not result.reflection.is_excellent
                ),
            },
        }

        # 从反思结果中提取评分
        if result.reflection:
            insight["overall_score"] = result.reflection.overall_score
            insight["is_excellent"] = result.reflection.is_excellent

        # 从评估中提取评分
        if result.assessment:
            insight["overall_score"] = result.assessment.overall_score

        # 从上下文中提取术语
        if result.understanding and result.understanding.translation_notes:
            # 尝试从翻译注释中提取术语
            insight["applied_terms"] = result.understanding.translation_notes[:5]

        # 详细信息（可选）
        if result.understanding:
            insight["understanding"] = result.understanding.model_dump()

        if result.reflection:
            insight["scores"] = {
                "readability": result.reflection.readability_score,
                "accuracy": result.reflection.accuracy_score,
            }

        if result.reflection and result.reflection.issues:
            insight["issues"] = [
                {"type": issue.issue_type, "description": issue.description}
                for issue in result.reflection.issues
            ]

        return insight

    async def get_translation_progress(self, project_id: str) -> Dict:
        """
        获取翻译进度

        Args:
            project_id: 项目ID

        Returns:
            Dict: 进度信息
        """
        progress = self._progress_cache().get(project_id)
        active_run = self._get_active_run(project_id)
        is_active_project = active_run is not None
        active_run_id = active_run.run_id if active_run else None
        if (
            progress is not None
            and is_active_project
            and (
                active_run_id is None
                or progress.run_id != active_run_id
            )
        ):
            progress = None
        def compact_usage(run_id: Optional[str], stored: Any = None) -> Optional[Dict[str, Any]]:
            usage = stored if isinstance(stored, dict) else None
            if usage is None and run_id:
                current = llm_usage_metrics.summary(run_id, include_calls=False)
                if current.get("api_calls"):
                    usage = current
            if usage is None:
                return None
            return {
                key: value
                for key, value in usage.items()
                if key != "calls"
            }

        def attach_active_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
            terminal_statuses = {"completed", "cancelled", "failed", "incomplete"}
            effective_status = str(payload.get("final_status") or payload.get("status") or "")
            payload["active_project_id"] = active_run.project_id if active_run else None
            payload["active_run_id"] = active_run.run_id if active_run else None
            payload["can_stop"] = is_active_project and payload.get("status") in (
                "processing",
                "starting",
                "cancelling",
            )
            payload["is_cancelling"] = bool(
                effective_status not in terminal_statuses
                and (
                    (progress and progress.cancel_requested)
                    or (is_active_project and active_run and active_run.status == "cancelling")
                    or payload.get("status") == "cancelling"
                )
            )
            run_id = payload.get("run_id")
            if run_id and "llm_usage" not in payload:
                usage = compact_usage(str(run_id))
                if usage is not None:
                    payload["llm_usage"] = usage
            return payload

        if progress:
            payload = progress.to_dict()
            if progress.final_status:
                return attach_active_fields({
                    "status": progress.final_status,
                    **payload,
                })

            stalled_seconds = max(
                int((datetime.now() - progress.last_updated_at).total_seconds()),
                0,
            )
            return attach_active_fields({
                "status": "completed" if progress.is_complete else "processing",
                "stalled_seconds": stalled_seconds,
                **payload,
            })

        if is_active_project and active_run_id is None:
            project = await asyncio.to_thread(
                self._load_project_with_sections,
                project_id,
            )
            latest_run = None
            latest_run_state = None
        else:
            project, run_snapshot = await asyncio.gather(
                asyncio.to_thread(self._load_project_with_sections, project_id),
                asyncio.to_thread(self._load_latest_run_snapshot, project_id),
            )
            latest_run, latest_run_state = run_snapshot

        total_paragraphs = sum(len(section.paragraphs) for section in project.sections)
        translated = self._count_project_translated_paragraphs(project.sections)
        is_complete = total_paragraphs > 0 and translated >= total_paragraphs
        latest_run_is_active = bool(
            is_active_project
            and active_run_id is not None
            and latest_run_state
            and latest_run_state.run_id == active_run_id
        )

        if is_active_project and active_run_id is None:
            return attach_active_fields({
                "status": active_run.status,
                "progress_percent": (
                    (translated / total_paragraphs * 100)
                    if total_paragraphs > 0
                    else 0
                ),
                "translated_paragraphs": translated,
                "total_paragraphs": total_paragraphs,
                "is_complete": False,
            })

        if (
            latest_run_is_active
            and latest_run
            and latest_run_state
            and latest_run_state.run_id != str(latest_run.get("run_id") or "")
        ):
            return attach_active_fields({
                "status": latest_run_state.status,
                "progress_percent": (
                    (translated / total_paragraphs * 100)
                    if total_paragraphs > 0
                    else 0
                ),
                "translated_paragraphs": translated,
                "total_paragraphs": total_paragraphs,
                "translated_sections": sum(
                    1 for section in project.sections if self._count_translated_paragraphs(section) == len(section.paragraphs) and len(section.paragraphs) > 0
                ),
                "total_sections": len(project.sections),
                "current_section": latest_run_state.current_section,
                "current_step": latest_run_state.current_step,
                "is_complete": False,
                "error_count": latest_run_state.error_count,
                "started_at": latest_run_state.started_at,
                "last_updated_at": latest_run_state.updated_at,
                "finished_at": latest_run_state.finished_at,
                "final_status": None,
                "run_id": latest_run_state.run_id,
            })

        if latest_run:
            latest_status = str(latest_run.get("status") or "").strip() or "processing"
            latest_total = int(latest_run.get("total_paragraphs") or total_paragraphs or 0)
            latest_translated = int(
                latest_run.get("translated_paragraphs") or translated or 0
            )
            return attach_active_fields({
                "status": latest_status,
                "progress_percent": (
                    (latest_translated / latest_total * 100)
                    if latest_total > 0
                    else 0
                ),
                "translated_paragraphs": latest_translated,
                "total_paragraphs": latest_total,
                "translated_sections": int(latest_run.get("translated_sections") or 0),
                "total_sections": int(latest_run.get("total_sections") or len(project.sections)),
                "current_section": latest_run_state.current_section if latest_run_state else None,
                "current_step": latest_run_state.current_step if latest_run_state else latest_status,
                "is_complete": latest_status == "completed",
                "error_count": int(latest_run.get("error_count") or 0),
                "started_at": latest_run.get("started_at"),
                "last_updated_at": latest_run_state.updated_at if latest_run_state else None,
                "finished_at": latest_run.get("finished_at"),
                "final_status": latest_status,
                "run_id": latest_run.get("run_id") or (latest_run_state.run_id if latest_run_state else None),
                "llm_usage": compact_usage(
                    str(latest_run.get("run_id") or ""),
                    latest_run.get("llm_usage"),
                ),
            })

        if latest_run_is_active and latest_run_state:
            return attach_active_fields({
                "status": latest_run_state.status,
                "progress_percent": (
                    (translated / total_paragraphs * 100)
                    if total_paragraphs > 0
                    else 0
                ),
                "translated_paragraphs": translated,
                "total_paragraphs": total_paragraphs,
                "translated_sections": sum(
                    1 for section in project.sections if self._count_translated_paragraphs(section) == len(section.paragraphs) and len(section.paragraphs) > 0
                ),
                "total_sections": len(project.sections),
                "current_section": latest_run_state.current_section,
                "current_step": latest_run_state.current_step,
                "is_complete": False,
                "error_count": latest_run_state.error_count,
                "started_at": latest_run_state.started_at,
                "last_updated_at": latest_run_state.updated_at,
                "finished_at": latest_run_state.finished_at,
                "final_status": None,
                "run_id": latest_run_state.run_id,
            })

        if is_complete and project.status in (
            ProjectStatus.REVIEWING,
            ProjectStatus.COMPLETED,
        ):
            status = "completed"
        elif is_active_project and project.status in (
            ProjectStatus.ANALYZING,
            ProjectStatus.IN_PROGRESS,
        ):
            status = "processing"
        elif translated > 0:
            status = "partial"
        else:
            status = "not_started"

        return attach_active_fields({
            "status": status,
            "progress_percent": (
                (translated / total_paragraphs * 100)
                if total_paragraphs > 0
                else 0
            ),
            "translated_paragraphs": translated,
            "total_paragraphs": total_paragraphs,
            "is_complete": is_complete,
        })

    @classmethod
    def cancel_run(
        cls,
        project_id: str,
        *,
        registry=None,
        progress_tracker: Optional[ProgressTracker] = None,
    ) -> Dict:
        """取消翻译任务（不需要服务实例）。

        取消只依赖运行登记与进度缓存，**不碰 LLM**。做成 classmethod 是为了让
        stop 端点在 LLM 配置损坏时仍能取消正在跑的翻译——否则"配置坏了导致
        翻译卡住"和"取消不了"会同时发生。两个参数缺省时用模块级/类级单例，
        实例方法会把自己的依赖传进来。
        """
        registry = registry or translation_run_registry
        tracker = progress_tracker or cls._shared_progress_tracker

        active_run = registry.mark_active_cancelled(project_id)
        if active_run is None:
            registry.clear_cancelled(project_id)
            return {"status": "not_found", "project_id": project_id}

        # Only a registry-owned run can be cancelled. Completed progress remains
        # cached for status polling and must never recreate an active slot.
        progress = tracker.get(project_id)

        if (
            progress is not None
            and not progress.final_status
            and progress.run_id == active_run.run_id
        ):
            progress.cancel_requested = True
            progress.current_step = "取消中"
            tracker.touch(progress)
            return {
                "status": "cancelling",
                "project_id": project_id,
                "run_id": progress.run_id,
            }

        return {
            "status": "cancelling",
            "project_id": project_id,
            "run_id": active_run.run_id,
        }

    async def cancel_translation(self, project_id: str) -> Dict:
        """
        取消翻译任务

        Args:
            project_id: 项目ID

        Returns:
            Dict: 取消结果
        """
        result = self.cancel_run(
            project_id,
            registry=self._run_registry,
            progress_tracker=self._progress_cache(),
        )
        # 实例路径额外落一次 run-state 工件（classmethod 版拿不到 artifact
        # service，取消本身不依赖它）。
        progress = self._progress_cache().get(project_id)
        if result.get("status") == "cancelling" and progress is not None:
            self._touch_progress(progress)
        return result

    def _can_transition_to_active_status(self, status: ProjectStatus) -> bool:
        """Whether service can temporarily move project into active translation status."""
        return status not in (ProjectStatus.REVIEWING, ProjectStatus.COMPLETED)

    def _final_status_after_success(
        self, original_status: ProjectStatus
    ) -> ProjectStatus:
        """Resolve final status while preserving advanced existing states."""
        if original_status in (ProjectStatus.REVIEWING, ProjectStatus.COMPLETED):
            return original_status
        return ProjectStatus.REVIEWING

    def _save_meta(
        self,
        project_id: str,
        meta: ProjectMeta,
        *,
        fields: tuple[str, ...] = ("status",),
        metadata_fields: tuple[str, ...] = (),
    ) -> None:
        """Merge only metadata fields owned by the batch translation flow."""
        if meta.id != project_id:
            raise ValueError(f"Project id mismatch: {project_id} != {meta.id}")
        nested_fields = {}
        if meta.metadata is not None and metadata_fields:
            nested_fields["metadata"] = {
                field_name: getattr(meta.metadata, field_name)
                for field_name in metadata_fields
            }
        self.project_manager.merge_meta_fields(
            project_id,
            fields={field_name: getattr(meta, field_name) for field_name in fields},
            nested_fields=nested_fields,
        )

    async def _translate_title_and_metadata(
        self,
        project: ProjectMeta,
        analysis: ArticleAnalysis,
    ) -> None:
        """
        翻译文章标题和副标题（合并为一次 API 调用）

        Args:
            project: 项目元信息
            analysis: 文章分析结果
        """
        if not project.title or project.title_translation:
            return

        try:
            subtitle = project.metadata.subtitle if project.metadata else None
            expected_title_translation = project.title_translation
            expected_subtitle = subtitle
            requirements = extract_title_requirements(project.title)
            preservation_lines: List[str] = []
            if requirements.required_prefix:
                preservation_lines.append(
                    f"- 必须完整保留标题前缀中的品牌/版本信息：{requirements.required_prefix}"
                )
            if requirements.former_name:
                preservation_lines.append(
                    f"- 原题中的历史名称必须保留：{requirements.former_name}"
                )
            glossary_block = self._build_title_glossary_block(
                project.id,
                project.title,
                subtitle,
            )
            result = self.llm.translate_title(
                project.title,
                context={
                    "article_theme": analysis.theme,
                    "structure_summary": analysis.structure_summary,
                    "target_audience": analysis.style.target_audience,
                    "glossary_block": glossary_block,
                    "preservation_block": "\n".join(preservation_lines)
                    if preservation_lines
                    else "- 无额外保留项",
                },
                subtitle=subtitle,
            )
            translated_title = enforce_translated_title(
                project.title,
                result.get("title", ""),
            )
            missing_terms = find_missing_title_terms(project.title, translated_title)
            if missing_terms:
                logger.warning(
                    "Translated title still missing protected terms %s for project %s",
                    missing_terms,
                    project.id,
                )
            fields = {"title_translation": translated_title}
            expected_fields = {
                "title_translation": expected_title_translation,
            }
            nested_fields: Dict[str, Dict[str, Any]] = {}
            expected_nested_fields: Dict[str, Dict[str, Any]] = {}
            translated_subtitle = result.get("subtitle")
            if translated_subtitle and project.metadata:
                nested_fields["metadata"] = {"subtitle": translated_subtitle}
                expected_nested_fields["metadata"] = {
                    "subtitle": expected_subtitle,
                }

            persisted, applied_fields = (
                self.project_manager.compare_and_set_meta_fields(
                    project.id,
                    fields=fields,
                    expected_fields=expected_fields,
                    nested_fields=nested_fields,
                    expected_nested_fields=expected_nested_fields,
                )
            )
            project.title_translation = persisted.title_translation
            if project.metadata and persisted.metadata:
                project.metadata.subtitle = persisted.metadata.subtitle

            if "title_translation" in applied_fields:
                logger.info(
                    "Title translated: %s -> %s",
                    project.title,
                    project.title_translation,
                )
            else:
                logger.info(
                    "Skipped stale generated title for project %s",
                    project.id,
                )
            if "metadata.subtitle" in applied_fields:
                logger.info("Subtitle translated: %s", translated_subtitle)
            elif translated_subtitle:
                logger.info(
                    "Skipped stale generated subtitle for project %s",
                    project.id,
                )
        except Exception as e:
            logger.error(f"Failed to translate title/subtitle: {e}")

    async def _translate_section_titles(
        self, project_id: str, project: ProjectMeta, analysis: ArticleAnalysis
    ) -> None:
        """
        翻译所有章节标题

        Args:
            project: 项目元信息
            analysis: 文章分析结果
        """
        pending: List[Dict[str, Any]] = []
        for section_index, section in enumerate(project.sections):
            if section.title and not section.title_translation:
                pending.append(
                    {
                        "id": section.section_id,
                        "title": section.title,
                        "prev": (
                            project.sections[section_index - 1].title
                            if section_index > 0
                            else ""
                        ),
                        "next": (
                            project.sections[section_index + 1].title
                            if section_index < len(project.sections) - 1
                            else ""
                        ),
                    }
                )

        if not pending:
            return

        # 标题链路此前完全绕过词表与白名单，导致标题与正文两套术语（审计 LC2）。
        try:
            title_glossary_block = self._build_title_glossary_block(
                project_id,
                "\n".join(item["title"] for item in pending),
                None,
            )
        except Exception as exc:
            logger.warning("Failed to build section title glossary block: %s", exc)
            title_glossary_block = "(无命中术语)"

        try:
            # 基类默认实现已接受这两个关键字参数，无需再靠捕获 TypeError 兼容——
            # 那种写法会把方法体内部抛出的 TypeError 一并吞掉，静默触发第二次
            # 完整 LLM 调用，且第二次丢掉词表与白名单，成本翻倍还让约束失效。
            translated_map = self.llm.translate_all_section_titles(
                pending,
                article_theme=analysis.theme,
                glossary_block=title_glossary_block,
                whitelist_rules=SECTION_TITLE_WHITELIST_RULES,
            )
        except Exception as exc:
            logger.error("Failed to batch translate section titles: %s", exc)
            translated_map = {}

        for section_index, section in enumerate(project.sections):
            if not section.title or section.title_translation:
                continue
            expected_title_translation = section.title_translation
            raw_title = str(translated_map.get(section.section_id, "")).strip()
            translated_title, violation = _repair_title_sinicization(raw_title)
            if translated_title != raw_title:
                logger.info(
                    "Repaired sinicized token in section title: %s -> %s",
                    raw_title,
                    translated_title,
                )
            if violation:
                # 保留译名、只记 warning：丢弃会让整章标题回退成英文，比一个
                # 「吉瓦」更糟。功率单位在正文里同样只是 warning。
                logger.warning(
                    "Section title keeps a sinicized power unit %r (title=%s); "
                    "review before publishing.",
                    violation,
                    translated_title,
                )
            if translated_title:
                persisted_section, applied = (
                    self.project_manager.update_section_title_translation_locked(
                        project_id,
                        section.section_id,
                        translated_title,
                        expected_title_translation=expected_title_translation,
                    )
                )
                section.title_translation = persisted_section.title_translation
                if not applied:
                    logger.info(
                        "Skipped stale section title translation: %s",
                        section.section_id,
                    )
                    continue
                logger.info(
                    "Section title translated (batch): %s -> %s",
                    section.title,
                    section.title_translation,
                )
                continue

            try:
                translated_title = self.llm.translate_section_title(
                    section.title,
                    context={
                        "article_theme": analysis.theme,
                        "context": "Section heading inside a long-form article",
                        "previous_section_title": (
                            project.sections[section_index - 1].title
                            if section_index > 0
                            else ""
                        ),
                        "next_section_title": (
                            project.sections[section_index + 1].title
                            if section_index < len(project.sections) - 1
                            else ""
                        ),
                        "glossary_block": title_glossary_block,
                        "whitelist_rules": SECTION_TITLE_WHITELIST_RULES,
                    },
                )
                translated_title, violation = _repair_title_sinicization(translated_title)
                if violation:
                    # 同上：保留译名只记 warning，丢弃反而让标题退回英文。
                    logger.warning(
                        "Fallback section title keeps a sinicized power unit %r "
                        "(title=%s); review before publishing.",
                        violation,
                        translated_title,
                    )
                persisted_section, applied = (
                    self.project_manager.update_section_title_translation_locked(
                        project_id,
                        section.section_id,
                        translated_title,
                        expected_title_translation=expected_title_translation,
                    )
                )
                section.title_translation = persisted_section.title_translation
                if not applied:
                    logger.info(
                        "Skipped stale section title translation: %s",
                        section.section_id,
                    )
                    continue
                logger.info(
                    "Section title translated (fallback): %s -> %s",
                    section.title,
                    section.title_translation,
                )
            except Exception as exc:
                logger.error("Failed to fallback translate section title: %s", exc)

    async def _translate_section_batch(
        self,
        section: Section,
        section_index: int,
        total_sections: int,
        all_sections: List[Section],
        analysis: ArticleAnalysis,
        phase1_provider: Optional[LLMProvider] = None,  # 新增参数
    ) -> List[Dict[str, str]]:
        """
        章节级批量翻译

        使用粗粒度模式一次性翻译整个章节

        Args:
            section: 要翻译的章节
            section_index: 章节索引
            total_sections: 总章节数
            all_sections: 所有章节
            analysis: 文章分析结果
            phase1_provider: Phase 1专用provider（可选）

        Returns:
            List[Dict[str, str]]: 翻译结果列表 [{"id": "p001", "translation": "..."}, ...]
        """
        # 构建章节文本（带段落ID）
        section_lines = []
        paragraph_ids = []
        dehydrated_translations: List[Dict[str, str]] = []
        batch_source_text_parts: List[str] = []

        format_tokens = []
        token_count = 0
        for para in section.paragraphs:
            dehydrated_payload = build_dehydrated_link_payload(para)
            if dehydrated_payload is not None and dehydrated_payload.tokenized_text:
                dehydrated_translations.append(
                    {
                        "id": para.id,
                        "translation": dehydrated_payload.tokenized_text,
                    }
                )
                continue

            prepared = build_translation_input(para)
            prompt_text = prepared.tokenized_text or prepared.text
            section_lines.append(f"[{para.id}] {prompt_text}")
            paragraph_ids.append(para.id)
            batch_source_text_parts.append(para.source)
            if para.inline_elements:
                format_tokens.extend(
                    [
                        {
                            "id": element.span_id,
                            "type": element.type,
                            "text": element.text,
                            "paragraph_id": para.id,
                        }
                        for element in para.inline_elements
                        if element.span_id
                    ]
                )
                token_count += len(para.inline_elements)

        section_text = "\n\n".join(section_lines)
        batch_source_text = "\n\n".join(batch_source_text_parts)

        understanding = analysis.section_roles.get(section.section_id)

        # 构建上下文
        context = {
            "article_theme": analysis.theme,
            "target_audience": analysis.style.target_audience,
            "translation_voice": analysis.style.translation_voice,
            "section_position": f"第 {section_index + 1}/{total_sections} 章节",
            "previous_section_title": (
                all_sections[section_index - 1].title if section_index > 0 else "无"
            ),
            "next_section_title": (
                all_sections[section_index + 1].title
                if section_index < total_sections - 1
                else "无"
            ),
            "glossary": [
                *build_glossary_entries_from_terms(
                    select_prompt_terms_for_text(
                        analysis.terminology,
                        batch_source_text,
                    )
                )
            ],
            "guidelines": build_translation_guidelines(analysis.guidelines),
            "section_role": (
                build_section_context_payload(understanding).get("role", "")
                if understanding
                else ""
            ),
            "translation_notes": (
                build_section_context_payload(understanding).get("translation_notes", [])
                if understanding
                else []
            ),
            "article_challenges": build_article_challenge_payload(analysis.challenges),
            "format_tokens": format_tokens,
            "format_token_count": token_count,
            "term_usage": self.context_manager.snapshot_term_usage(),
        }

        # 注入前文译文：section 模式此前从不传这一项，提示词里的「前文译文」恒为
        # 「无」，跨章节首现判定与风格锚点全部失效（审计 LC1）。
        # feedback_from_previous_sections 由四步法 reflection 产出，section 模式下
        # 永远为空，故不一并注入。
        previous_translations = build_previous_translation_pairs(
            self.context_manager,
            section.section_id,
            prev_section_id=(
                all_sections[section_index - 1].section_id
                if section_index > 0
                else None
            ),
        )
        if previous_translations:
            context["previous_translations"] = previous_translations

        if not section_lines:
            return dehydrated_translations

        # 使用Phase 1 provider（如果提供）或默认provider。同步网络调用
        # 卸载到线程池，保证顺序章节翻译期间事件循环仍可响应取消和进度查询。
        provider = phase1_provider or self.llm

        # 按段数与字符数分批。此前整章一次调用、无任何上限：单章 9400 词的章节
        # （ClusterMAX 有 5 个）产出约 14000 输出 token，稳超模型 8192 的上限，
        # 模型只吐出前几十段，其余段落**既不报错也不重试**地留在未翻译状态，
        # 而本次运行仍报「成功」。四步法那条路早有分批与逐段回退，默认的
        # section 模式反而两样都没有。
        batches = self._split_section_batches(section_lines, paragraph_ids)
        translated: List[Dict[str, str]] = []
        for batch_lines, batch_ids in batches:
            translated.extend(
                await self._call_section_batch(
                    provider=provider,
                    section=section,
                    context=context,
                    format_tokens=format_tokens,
                    batch_lines=batch_lines,
                    batch_ids=batch_ids,
                )
            )

        # 完整性校验 + 缺段重试。模型漏返、超长截断都会表现为「返回条目少于请求」，
        # 静默丢段比翻译失败更糟——用户看到的是一篇夹杂英文原文的成品。
        translated = await self._retry_missing_paragraphs(
            provider=provider,
            section=section,
            context=context,
            format_tokens=format_tokens,
            section_lines=section_lines,
            paragraph_ids=paragraph_ids,
            translated=translated,
        )
        return [*translated, *dehydrated_translations]

    def _split_section_batches(
        self,
        section_lines: List[str],
        paragraph_ids: List[str],
    ) -> List[tuple[List[str], List[str]]]:
        """按段数与字符数把一章切成若干批，保证单批输出不撞模型的输出上限。"""
        batches: List[tuple[List[str], List[str]]] = []
        cur_lines: List[str] = []
        cur_ids: List[str] = []
        cur_chars = 0

        for line, para_id in zip(section_lines, paragraph_ids):
            over_count = len(cur_lines) >= self.MAX_SECTION_BATCH_PARAGRAPHS
            over_chars = cur_chars + len(line) > self.MAX_SECTION_BATCH_CHARS
            if cur_lines and (over_count or over_chars):
                batches.append((cur_lines, cur_ids))
                cur_lines, cur_ids, cur_chars = [], [], 0
            cur_lines.append(line)
            cur_ids.append(para_id)
            cur_chars += len(line)

        if cur_lines:
            batches.append((cur_lines, cur_ids))
        return batches

    async def _call_section_batch(
        self,
        *,
        provider: LLMProvider,
        section: Section,
        context: Dict[str, Any],
        format_tokens: List[Dict[str, Any]],
        batch_lines: List[str],
        batch_ids: List[str],
    ) -> List[Dict[str, str]]:
        """翻译一批段落。格式 token 按批过滤，避免把别批的 token 说明发给模型。"""
        batch_id_set = set(batch_ids)
        batch_tokens = [
            token for token in format_tokens
            if token.get("paragraph_id") in batch_id_set
        ]
        batch_context = {
            **context,
            "format_tokens": batch_tokens,
            "format_token_count": len(batch_tokens),
        }
        result = await asyncio.to_thread(
            provider.translate_section,
            section_text=SECTION_LINE_SEPARATOR.join(batch_lines),
            section_title=section.title,
            context=batch_context,
            paragraph_ids=batch_ids,
        )
        return list(result or [])

    async def _retry_missing_paragraphs(
        self,
        *,
        provider: LLMProvider,
        section: Section,
        context: Dict[str, Any],
        format_tokens: List[Dict[str, Any]],
        section_lines: List[str],
        paragraph_ids: List[str],
        translated: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """补齐模型漏返的段落；补不齐时明确告警，不让运行伪装成功。"""
        line_by_id = dict(zip(paragraph_ids, section_lines))

        for attempt in range(self.MISSING_PARAGRAPH_RETRIES):
            returned = {
                item.get("id")
                for item in translated
                if isinstance(item, dict)
                and isinstance(item.get("translation"), str)
                and item["translation"].strip()
            }
            missing = [pid for pid in paragraph_ids if pid not in returned]
            if not missing:
                return translated

            logger.warning(
                "[%s] Section batch returned %s/%s paragraphs; retrying %s missing "
                "(attempt %s/%s)",
                section.section_id,
                len(returned),
                len(paragraph_ids),
                len(missing),
                attempt + 1,
                self.MISSING_PARAGRAPH_RETRIES,
            )

            # 重试用更小的批，漏返多半就是单批过大导致的输出截断
            retry_size = max(1, self.MAX_SECTION_BATCH_PARAGRAPHS // 4)
            for start in range(0, len(missing), retry_size):
                chunk_ids = missing[start:start + retry_size]
                chunk_lines = [line_by_id[pid] for pid in chunk_ids]
                try:
                    translated.extend(
                        await self._call_section_batch(
                            provider=provider,
                            section=section,
                            context=context,
                            format_tokens=format_tokens,
                            batch_lines=chunk_lines,
                            batch_ids=chunk_ids,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "[%s] Missing-paragraph retry failed for %s ids: %s",
                        section.section_id,
                        len(chunk_ids),
                        exc,
                    )

        returned = {
            item.get("id")
            for item in translated
            if isinstance(item, dict)
            and isinstance(item.get("translation"), str)
            and item["translation"].strip()
        }
        still_missing = [pid for pid in paragraph_ids if pid not in returned]
        if still_missing:
            logger.error(
                "[%s] %s/%s paragraphs still untranslated after retries: %s",
                section.section_id,
                len(still_missing),
                len(paragraph_ids),
                ", ".join(still_missing[:10]),
            )
        return translated
