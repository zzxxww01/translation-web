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
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, List, Optional, Dict, Callable, Set
from datetime import datetime
import logging

from src.core.glossary import infer_glossary_tags
from src.core.longform_context import (
    build_article_challenge_payload,
    build_glossary_entries_from_terms,
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
from src.core.title_guard import (
    enforce_translated_title,
    extract_title_requirements,
    find_missing_title_terms,
)
from src.agents.deep_analyzer import DeepAnalyzer
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.agents.consistency_reviewer import ConsistencyReviewer
from src.llm.base import LLMProvider
from src.services.batch_translation_types import TranslationProgress
from src.services.progress_tracker import ProgressTracker
from src.services.source_metadata_service import SourceMetadataTranslationService


logger = logging.getLogger(__name__)


class BatchTranslationService:
    """批量翻译服务"""

    _shared_progress_tracker = ProgressTracker()
    _cancelled_projects: Set[str] = set()
    _cancelled_lock = threading.Lock()

    # 翻译模式
    TRANSLATION_MODE_FOUR_STEP = "four_step"  # 四步法（段落级）
    TRANSLATION_MODE_SECTION = "section"  # 章节级批量翻译
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
        max_concurrent_sections: int = 10,  # 最大并发章节数（提高到10）
    ):
        """
        初始化批量翻译服务

        Args:
            llm_provider: LLM Provider
            project_manager: 项目管理器
            translation_mode: 翻译模式 ("four_step" 或 "section")
            max_concurrent_sections: 最大并发章节数（默认10，VectorEngine可支持更高）
        """
        self.llm = llm_provider
        self.project_manager = project_manager
        self.translation_mode = translation_mode
        self.max_concurrent_sections = max_concurrent_sections
        self.deep_analyzer = DeepAnalyzer(llm_provider)
        self.context_manager = LayeredContextManager()
        self._progress_tracker = self._shared_progress_tracker

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
        )
        self.consistency_reviewer = ConsistencyReviewer(llm_provider)

    def _is_cancelled(self, project_id: str) -> bool:
        with self._cancelled_lock:
            return project_id in self._cancelled_projects

    def _mark_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.add(project_id)

    def _clear_cancelled(self, project_id: str) -> None:
        with self._cancelled_lock:
            self._cancelled_projects.discard(project_id)

    def _load_project_with_sections(self, project_id: str) -> ProjectMeta:
        """Load project and attach sections."""
        project = self.project_manager.get(project_id)
        project.sections = self.project_manager.get_sections(project_id)
        return project

    def _artifacts_root(self, project_id: str) -> Path:
        return self.project_manager.projects_path / project_id / "artifacts" / "runs"

    def _create_run_artifact_dir(self, project_id: str) -> tuple[str, Path]:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        run_dir = self._artifacts_root(project_id) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_id, run_dir

    def _normalize_artifact_payload(self, payload: Any) -> Any:
        if hasattr(payload, "model_dump"):
            return payload.model_dump(mode="json")
        if isinstance(payload, dict):
            return {
                key: self._normalize_artifact_payload(value)
                for key, value in payload.items()
            }
        if isinstance(payload, list):
            return [self._normalize_artifact_payload(item) for item in payload]
        return payload

    def _write_artifact_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                self._normalize_artifact_payload(payload),
                handle,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    def _load_latest_analysis_snapshot(self, project_id: str) -> Optional[ArticleAnalysis]:
        """Load the most recent persisted article analysis for resume runs."""
        artifacts_root = self._artifacts_root(project_id)
        if not artifacts_root.exists():
            return None

        run_dirs = sorted(
            (path for path in artifacts_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for run_dir in run_dirs:
            analysis_path = run_dir / "analysis.json"
            if not analysis_path.exists():
                continue
            try:
                with open(analysis_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if hasattr(ArticleAnalysis, "model_validate"):
                    return ArticleAnalysis.model_validate(payload)
                return ArticleAnalysis.parse_obj(payload)
            except Exception as exc:
                logger.warning(
                    "Failed to load analysis snapshot from %s: %s",
                    analysis_path,
                    exc,
                )
        return None

    def _load_latest_run_summary(self, project_id: str) -> Optional[Dict[str, Any]]:
        artifacts_root = self._artifacts_root(project_id)
        if not artifacts_root.exists():
            return None

        run_dirs = sorted(
            (path for path in artifacts_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for run_dir in run_dirs:
            summary_path = run_dir / "run-summary.json"
            if not summary_path.exists():
                continue
            try:
                with open(summary_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    return payload
            except Exception as exc:
                logger.warning(
                    "Failed to load run summary from %s: %s",
                    summary_path,
                    exc,
                )
        return None

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

        terms: List[GlossaryTerm] = []
        for section in payload.get("sections", []):
            for candidate in section.get("candidates", []):
                original = str(candidate.get("term") or "").strip()
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
        glossary = self.project_manager.glossary_manager.load_project(project_id)
        global_glossary = self.project_manager.glossary_manager.load_global()
        existing_terms = {
            term.original.lower(): term
            for term in glossary.terms
            if term.status == "active"
        }
        global_terms = {
            term.original.lower(): term
            for term in global_glossary.terms
            if term.status == "active"
        }

        added_terms: List[GlossaryTerm] = []
        for candidate in [
            *self._load_term_review_seed_terms(project_id),
            *self._build_analysis_seed_terms(analysis),
        ]:
            key = candidate.original.lower()
            if key in existing_terms:
                continue
            global_term = global_terms.get(key)
            if global_term is not None:
                same_translation = (
                    (global_term.translation or global_term.original)
                    == (candidate.translation or candidate.original)
                )
                if same_translation and global_term.strategy == candidate.strategy:
                    continue
            glossary.add_term(candidate)
            existing_terms[key] = candidate
            added_terms.append(candidate)

        if added_terms:
            self.project_manager.glossary_manager.save_project(project_id, glossary)

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
        # 加载项目
        self._clear_cancelled(project_id)
        project = self._load_project_with_sections(project_id)
        original_status = project.status
        self.context_manager.reset_all()

        # 重置 API 调用计数器
        from src.llm.gemini import GeminiProvider
        GeminiProvider._api_call_count = 0
        project_start_time = time.monotonic()

        # 统计总数
        total_paragraphs = sum(len(s.paragraphs) for s in project.sections)
        total_sections = len(project.sections)

        # 创建进度跟踪
        progress = self._progress_tracker.create(
            project_id=project_id,
            total_sections=total_sections,
            total_paragraphs=total_paragraphs,
            original_status=original_status,
        )

        run_id, run_dir = self._create_run_artifact_dir(project_id)
        self._write_artifact_json(
            run_dir / "source-manifest.json",
            self._build_source_manifest(project, project_id),
        )
        self._write_artifact_json(
            run_dir / "structure-map.json",
            self._build_structure_map(project),
        )

        # 更新项目状态为"分析中"
        self._set_active_status(project_id, project, ProjectStatus.ANALYZING)

        # 已翻译的段落计数器
        translated_count = 0

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
            progress.current_step = "已取消"
            progress.final_status = "cancelled"
            project.status = original_status
            self._save_meta(project_id, project)

            result = {
                "project_id": project_id,
                "status": "cancelled",
                "message": message,
                "total_sections": progress.total_sections,
                "translated_sections": progress.translated_sections,
                "total_paragraphs": progress.total_paragraphs,
                "translated_paragraphs": actual_translated,
                "error_count": len(progress.errors),
                "errors": progress.errors,
                "started_at": progress.started_at.isoformat(),
                "finished_at": progress.finished_at.isoformat(),
                "run_id": run_id,
                "artifacts_path": str(run_dir),
                "api_calls": GeminiProvider._api_call_count,
                "elapsed_seconds": round(time.monotonic() - project_start_time, 1),
            }
            self._write_artifact_json(run_dir / "run-summary.json", result)
            self._clear_cancelled(project_id)
            return result

        try:
            # Phase 0: 深度分析全文
            logger.info(f"[{project_id}] Starting Phase 0: Deep Analysis")
            progress.current_step = "深度分析全文"
            self._notify_progress(
                on_progress, "深度分析全文", translated_count, total_paragraphs
            )
            existing_translated = self._count_project_translated_paragraphs(project.sections)
            analysis = None
            if existing_translated > 0:
                analysis = self._load_latest_analysis_snapshot(project_id)
                if analysis is not None:
                    logger.info(
                        "[%s] Reusing persisted analysis snapshot for resume run",
                        project_id,
                    )

            if analysis is None:
                analysis = self.deep_analyzer.analyze(project.sections)
            glossary_seed_result = self._seed_project_glossary(project_id, analysis)
            analysis = self._merge_analysis_with_project_glossary(project_id, analysis)

            # 设置分析结果到上下文管理器
            self.context_manager.set_article_analysis(analysis)
            self.context_manager.add_terms_from_analysis(analysis.terminology)

            # 断点续传：预填充术语使用记录，让已译章节的术语不被重复加注
            self._prepopulate_term_tracker(project)

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
            progress.current_step = "翻译标题"
            self._notify_progress(
                on_progress, "翻译标题", translated_count, total_paragraphs
            )
            await self._translate_title_and_metadata(project, analysis)
            self._save_meta(project_id, project)

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            # 翻译章节标题
            logger.info(f"[{project_id}] Translating section titles")
            progress.current_step = "翻译章节标题"
            self._notify_progress(
                on_progress, "翻译章节标题", translated_count, total_paragraphs
            )
            await self._translate_section_titles(project_id, project, analysis)

            if self._is_cancelled(project_id):
                return finalize_cancelled_result()

            logger.info(f"[{project_id}] Translating source metadata")
            progress.current_step = "翻译来源说明"
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

            # 更新项目状态为"翻译中"
            self._set_active_status(project_id, project, ProjectStatus.IN_PROGRESS)

            # 并行翻译章节
            logger.info(
                f"[{project_id}] Starting parallel section translation "
                f"(mode: {self.translation_mode}, max_concurrent: {self.max_concurrent_sections})"
            )

            # 收集所有翻译结果用于一致性审查
            all_translations = {}

            # 使用信号量控制并发数
            semaphore = asyncio.Semaphore(self.max_concurrent_sections)

            async def translate_section_with_limit(section_index: int, section: Section):
                """带并发限制的章节翻译"""
                async with semaphore:
                    return await self._translate_single_section(
                        project_id=project_id,
                        section=section,
                        section_index=section_index,
                        total_sections=total_sections,
                        all_sections=project.sections,
                        analysis=analysis,
                        run_dir=run_dir,
                        progress=progress,
                        on_progress=on_progress,
                        on_term_conflict=on_term_conflict,
                        project=project,
                        total_paragraphs=total_paragraphs,
                    )

            # 创建所有翻译任务
            tasks = [
                translate_section_with_limit(i, section)
                for i, section in enumerate(project.sections)
            ]

            # 并行执行所有任务
            logger.info(f"[{project_id}] Launching {len(tasks)} section translation tasks")
            results = await asyncio.gather(*tasks, return_exceptions=True)

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
                    translated_count += result["paragraph_count"]
                    progress.translated_sections += 1
                    progress.translated_paragraphs += result["paragraph_count"]

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

                # 更新进度
                section_paragraph_count = result["paragraph_count"]
                translated_in_section = result["translated_before"]
                translated_after_section = self._count_translated_paragraphs(section)
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

            # Phase 2: 一致性审查（优化：新增）
            logger.info(f"[{project_id}] Starting Phase 2: Consistency Review")
            progress.current_step = "一致性审查"
            self._notify_progress(
                on_progress, "一致性审查", translated_count, total_paragraphs
            )

            consistency_report = None
            try:
                consistency_report = self.consistency_reviewer.review(
                    sections=project.sections,
                    translations=all_translations,
                    article_analysis=analysis,
                    term_tracker=self.context_manager.term_tracker,
                )

                # 记录一致性审查结果
                logger.info(
                    f"[{project_id}] Consistency review completed: "
                    f"{len(consistency_report.issues)} issues found, "
                    f"{len(consistency_report.auto_fixable)} auto-fixable"
                )

                # 如果有可自动修复的问题，应用修复
                if consistency_report.auto_fixable:
                    logger.info(
                        f"[{project_id}] Applying {len(consistency_report.auto_fixable)} auto-fixes..."
                    )
                    auto_fixed_translations = self.consistency_reviewer.auto_fix(
                        all_translations, consistency_report.auto_fixable
                    )

                    # Update paragraph translations, but never overwrite tokenized segments.
                    for section in project.sections:
                        if section.section_id in auto_fixed_translations:
                            for j, translation in enumerate(
                                auto_fixed_translations[section.section_id]
                            ):
                                if j < len(section.paragraphs):
                                    para = section.paragraphs[j]
                                    if para.expected_tokens:
                                        auto_fixed_translations[section.section_id][j] = (
                                            para.best_translation_text()
                                        )
                                        if translation != para.best_translation_text():
                                            progress.errors.append(
                                                {
                                                    "type": "consistency_autofix_skipped",
                                                    "section_id": section.section_id,
                                                    "paragraph_id": para.id,
                                                    "message": (
                                                        "Skipped auto-fix for a formatted paragraph "
                                                        "to preserve hidden token reconstruction."
                                                    ),
                                                    "timestamp": datetime.now().isoformat(),
                                                }
                                            )
                                        continue
                                    para.add_translation(translation, "gemini_refined")
                            self.project_manager.save_section(project_id, section)
                    all_translations = auto_fixed_translations

                self._write_artifact_json(
                    run_dir / "consistency.json",
                    {
                        "report": consistency_report,
                        "translations_after_consistency": all_translations,
                    },
                )

            except Exception as e:
                logger.error(f"[{project_id}] Consistency review failed: {str(e)}")
                self._write_artifact_json(
                    run_dir / "consistency.json",
                    {"error": str(e)},
                )
                # 一致性审查失败不影响翻译完成状态

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
            except Exception as export_exc:
                export_report["markdown"]["error"] = str(export_exc)

            is_complete = translation_complete and export_report["markdown"]["generated"]

            progress.finished_at = datetime.now()
            progress.translated_paragraphs = actual_translated
            progress.translated_sections = sum(
                1
                for section in project.sections
                if self._count_translated_paragraphs(section) == len(section.paragraphs)
                and len(section.paragraphs) > 0
            )
            progress.current_step = "completed" if is_complete else "incomplete"
            progress.final_status = "completed" if is_complete else "incomplete"
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

            logger.info(
                "[%s] Translation completed: %d API calls, %.0fs elapsed",
                project_id,
                GeminiProvider._api_call_count,
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
                "error_count": len(progress.errors),
                "errors": progress.errors,
                "started_at": progress.started_at.isoformat(),
                "finished_at": progress.finished_at.isoformat(),
                "run_id": run_id,
                "artifacts_path": str(run_dir),
                "export": export_report,
                "api_calls": GeminiProvider._api_call_count,
                "elapsed_seconds": round(time.monotonic() - project_start_time, 1),
            }

            # 添加一致性审查报告
            if consistency_report:
                result["consistency"] = {
                    "is_consistent": consistency_report.is_consistent,
                    "total_issues": len(consistency_report.issues),
                    "auto_fixable_count": len(consistency_report.auto_fixable),
                    "manual_review_count": len(consistency_report.manual_review),
                    "issues": [
                        {
                            "section_id": issue.section_id,
                            "paragraph_index": issue.paragraph_index,
                            "issue_type": issue.issue_type,
                            "description": issue.description,
                            "auto_fixable": issue.auto_fixable,
                        }
                        for issue in consistency_report.manual_review[
                            :10
                        ]  # 最多返回10个需人工审核的问题
                    ],
                }

            self._write_artifact_json(run_dir / "run-summary.json", result)

            self._clear_cancelled(project_id)
            return result

        except Exception as e:
            logger.error(f"[{project_id}] Translation failed: {str(e)}")
            self._progress_tracker.record_error(progress, str(e))
            progress.finished_at = datetime.now()
            progress.final_status = "failed"

            # 更新项目状态为失败
            project.status = original_status
            self._save_meta(project_id, project)

            failure_result = {
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
                "errors": progress.errors,
                "run_id": run_id,
                "artifacts_path": str(run_dir),
            }
            self._write_artifact_json(run_dir / "run-summary.json", failure_result)
            self._clear_cancelled(project_id)
            return failure_result

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
    ) -> Dict[str, Any]:
        """
        翻译单个章节（用于并行处理）

        Returns:
            Dict with keys: section_id, translations, error (if any)
        """
        try:
            # 取消检查
            if self._is_cancelled(project_id):
                return {"section_id": section.section_id, "cancelled": True}

            # 构建章节上下文
            section_prompt_context = self._build_section_prompt_context(
                project,
                section,
                section_index,
                analysis,
            )
            self._persist_section_artifact(
                run_dir,
                "section-context",
                section.section_id,
                section_prompt_context,
            )

            # 预扫描
            prescan_result = await self._run_section_prescan(
                project_id,
                section,
                progress,
                on_term_conflict=on_term_conflict,
            )
            if prescan_result:
                self._persist_section_artifact(
                    run_dir,
                    "section-prescan",
                    section.section_id,
                    prescan_result,
                )

            # 检查是否已翻译
            section_paragraph_count = len(section.paragraphs)
            translated_in_section = self._count_translated_paragraphs(section)

            if (
                translated_in_section == section_paragraph_count
                and section_paragraph_count > 0
            ):
                # 已翻译，跳过
                logger.info(
                    f"[{project_id}] Skipping section {section.section_id}: "
                    f"all {section_paragraph_count} paragraphs already translated"
                )
                return {
                    "section_id": section.section_id,
                    "skipped": True,
                    "translations": self._collect_section_translations(section),
                    "paragraph_count": section_paragraph_count,
                }

            # 翻译章节
            if self.translation_mode == self.TRANSLATION_MODE_SECTION:
                # 章节级批量翻译
                translations = await self._translate_section_batch(
                    section=section,
                    section_index=section_index,
                    total_sections=total_sections,
                    all_sections=all_sections,
                    analysis=analysis,
                )

                # 应用翻译结果
                collected_translations = self._apply_section_batch_translations(
                    section,
                    translations,
                )
                self._record_section_batch_term_usage(section, analysis)
                self._persist_section_artifact(
                    run_dir,
                    "section-draft",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "mode": self.translation_mode,
                        "prompt_context": section_prompt_context,
                        "translations": translations,
                    },
                )
            else:
                # 四步法翻译
                result = self.translator.translate_section(
                    section=section,
                    all_sections=all_sections,
                    project_id=project_id,
                    on_progress=self._create_section_callback(
                        section.title,
                        on_progress,
                        translated_in_section,
                        total_paragraphs,
                        max(section_paragraph_count - translated_in_section, 0),
                    ),
                )

                self._apply_four_step_translations(section, result)
                collected_translations = result.translations
                self._persist_section_artifact(
                    run_dir,
                    "section-draft",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "mode": self.translation_mode,
                        "prompt_context": section_prompt_context,
                        "understanding": result.understanding,
                        "translations": result.draft_translations,
                    },
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-critique",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "reflection": result.reflection,
                    },
                )
                self._persist_section_artifact(
                    run_dir,
                    "section-revision",
                    section.section_id,
                    {
                        "section_id": section.section_id,
                        "assessment": result.assessment,
                        "translations": result.revised_translations,
                    },
                )

            # 保存章节
            self.project_manager.save_section(project_id, section)

            return {
                "section_id": section.section_id,
                "translations": collected_translations,
                "paragraph_count": section_paragraph_count,
                "translated_before": translated_in_section,
            }

        except Exception as e:
            error_msg = f"Failed to translate section {section.section_id}: {str(e)}"
            logger.error(f"[{project_id}] {error_msg}")
            return {
                "section_id": section.section_id,
                "error": error_msg,
                "exception": e,
            }

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

            prescan_result = self.translator.prescan_section(
                section=section,
                on_conflict=record_conflict,
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
                    key = term.term.lower()
                    if key in self.context_manager.term_tracker.used_translations:
                        continue  # already recorded
                    if _count_term_occurrences(source, term.term) > 0:
                        self.context_manager.term_tracker.record_usage(
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
                key = term.term.lower()
                if key in self.context_manager.term_tracker.used_translations:
                    continue
                if _count_term_occurrences(source, term.term) > 0:
                    self.context_manager.term_tracker.record_usage(
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
        progress = self._progress_tracker.get(project_id)

        if progress:
            if progress.final_status:
                return {
                    "status": progress.final_status,
                    **progress.to_dict(),
                }

            return {
                "status": "completed" if progress.is_complete else "processing",
                **progress.to_dict(),
            }

        project = self._load_project_with_sections(project_id)
        total_paragraphs = sum(len(section.paragraphs) for section in project.sections)
        translated = self._count_project_translated_paragraphs(project.sections)
        is_complete = total_paragraphs > 0 and translated >= total_paragraphs
        latest_run = self._load_latest_run_summary(project_id)

        if latest_run:
            latest_status = str(latest_run.get("status") or "").strip() or "processing"
            latest_total = int(latest_run.get("total_paragraphs") or total_paragraphs or 0)
            latest_translated = int(
                latest_run.get("translated_paragraphs") or translated or 0
            )
            return {
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
                "current_section": None,
                "current_step": latest_status,
                "is_complete": latest_status == "completed",
                "error_count": int(latest_run.get("error_count") or 0),
                "started_at": latest_run.get("started_at"),
                "finished_at": latest_run.get("finished_at"),
                "final_status": latest_status,
                "run_id": latest_run.get("run_id"),
            }

        if is_complete and project.status in (
            ProjectStatus.REVIEWING,
            ProjectStatus.COMPLETED,
        ):
            status = "completed"
        elif project.status in (ProjectStatus.ANALYZING, ProjectStatus.IN_PROGRESS):
            status = "processing"
        elif translated > 0:
            status = "processing"
        else:
            status = "not_started"

        return {
            "status": status,
            "progress_percent": (
                (translated / total_paragraphs * 100)
                if total_paragraphs > 0
                else 0
            ),
            "translated_paragraphs": translated,
            "total_paragraphs": total_paragraphs,
            "is_complete": is_complete,
        }

    async def cancel_translation(self, project_id: str) -> Dict:
        """
        取消翻译任务

        Args:
            project_id: 项目ID

        Returns:
            Dict: 取消结果
        """
        # 设置取消标记，让翻译循环在下一个 section 迭代时退出
        self._mark_cancelled(project_id)

        progress = self._progress_tracker.get(project_id)

        if progress is not None:
            progress.current_step = "取消中"
            return {"status": "cancelling", "project_id": project_id}

        self._clear_cancelled(project_id)
        return {"status": "not_found", "project_id": project_id}

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

    def _save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息。"""
        if meta.id != project_id:
            raise ValueError(f"Project id mismatch: {project_id} != {meta.id}")
        self.project_manager.save_meta(meta)

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
            project.title_translation = translated_title
            logger.info(
                f"Title translated: {project.title} -> {project.title_translation}"
            )
            if result.get("subtitle") and project.metadata:
                project.metadata.subtitle = result["subtitle"]
                logger.info(f"Subtitle translated: {result['subtitle']}")
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

        try:
            translated_map = self.llm.translate_all_section_titles(
                pending,
                article_theme=analysis.theme,
            )
        except Exception as exc:
            logger.error("Failed to batch translate section titles: %s", exc)
            translated_map = {}

        for section_index, section in enumerate(project.sections):
            if not section.title or section.title_translation:
                continue
            translated_title = str(translated_map.get(section.section_id, "")).strip()
            if translated_title:
                section.title_translation = translated_title
                self.project_manager.save_section(project_id, section)
                logger.info(
                    "Section title translated (batch): %s -> %s",
                    section.title,
                    section.title_translation,
                )
                continue

            try:
                section.title_translation = self.llm.translate_section_title(
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
                    },
                )
                self.project_manager.save_section(project_id, section)
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
            "term_usage": self.context_manager.term_tracker.used_translations.copy(),
        }

        if not section_lines:
            return dehydrated_translations

        translated = self.llm.translate_section(
            section_text=section_text,
            section_title=section.title,
            context=context,
            paragraph_ids=paragraph_ids,
        )
        return [*translated, *dehydrated_translations]
