"""
批量翻译服务

功能:
1. Phase 0: 深度分析全文
2. 逐章节翻译（四步法或粗粒度模式）
3. 进度跟踪
4. 错误处理和重试
5. 标题和元信息翻译
"""

import asyncio
import threading
import time as _time
from typing import List, Optional, Dict, Callable
from datetime import datetime
import logging

from src.core.models import (
    ProjectMeta, Section, Paragraph, ParagraphStatus,
    ProjectStatus, ArticleAnalysis
)
from src.core.project import ProjectManager
from src.agents.deep_analyzer import DeepAnalyzer
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.agents.consistency_reviewer import ConsistencyReviewer
from src.llm.base import LLMProvider
from src.services.batch_translation_types import TranslationProgress


logger = logging.getLogger(__name__)


class BatchTranslationService:
    """批量翻译服务"""

    # 类变量，用于存储翻译进度（单例模式）
    _progress_cache: Dict[str, TranslationProgress] = {}
    _progress_lock = threading.Lock()
    _PROGRESS_TTL_SECONDS = 3600  # 1 hour

    # 翻译模式
    TRANSLATION_MODE_FOUR_STEP = "four_step"  # 四步法（段落级）
    TRANSLATION_MODE_SECTION = "section"  # 章节级批量翻译

    def __init__(
        self,
        llm_provider: LLMProvider,
        project_manager: ProjectManager,
        translation_mode: str = "section"  # 默认使用章节级翻译
    ):
        """
        初始化批量翻译服务

        Args:
            llm_provider: LLM Provider
            project_manager: 项目管理器
            translation_mode: 翻译模式 ("four_step" 或 "section")
        """
        self.llm = llm_provider
        self.project_manager = project_manager
        self.translation_mode = translation_mode
        self.deep_analyzer = DeepAnalyzer(llm_provider)
        self.context_manager = LayeredContextManager()
        self.translator = FourStepTranslator(
            llm_provider=llm_provider,
            context_manager=self.context_manager
        )
        self.consistency_reviewer = ConsistencyReviewer(llm_provider)

    @classmethod
    def _evict_stale_progress(cls) -> None:
        """Remove progress entries older than TTL (call while holding _progress_lock)."""
        now = _time.monotonic()
        stale = [
            pid for pid, p in cls._progress_cache.items()
            if hasattr(p, '_mono_ts') and now - p._mono_ts > cls._PROGRESS_TTL_SECONDS
        ]
        for pid in stale:
            del cls._progress_cache[pid]

    def _load_project_with_sections(self, project_id: str) -> ProjectMeta:
        """Load project and attach sections."""
        project = self.project_manager.get(project_id)
        project.sections = self.project_manager.get_sections(project_id)
        return project

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

    def _record_error(
        self,
        progress: TranslationProgress,
        error: str,
        section_id: Optional[str] = None,
    ) -> None:
        """Append standardized error payload to progress."""
        item = {
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        if section_id:
            item["section"] = section_id
        progress.errors.append(item)

    async def translate_project(
        self,
        project_id: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None
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
        project = self._load_project_with_sections(project_id)
        original_status = project.status

        # 统计总数
        total_paragraphs = sum(len(s.paragraphs) for s in project.sections)
        total_sections = len(project.sections)

        # 创建进度跟踪
        progress = TranslationProgress(
            total_sections=total_sections,
            total_paragraphs=total_paragraphs,
            original_status=original_status,
        )
        progress._mono_ts = _time.monotonic()
        with self._progress_lock:
            self._evict_stale_progress()
            self._progress_cache[project_id] = progress

        # 更新项目状态为"分析中"
        self._set_active_status(project_id, project, ProjectStatus.ANALYZING)

        # 已翻译的段落计数器
        translated_count = 0

        try:
            # Phase 0: 深度分析全文
            logger.info(f"[{project_id}] Starting Phase 0: Deep Analysis")
            progress.current_step = "深度分析全文"
            self._notify_progress(on_progress, "深度分析全文", translated_count, total_paragraphs)

            analysis = self.deep_analyzer.analyze(project.sections)

            # 设置分析结果到上下文管理器
            self.context_manager.set_article_analysis(analysis)

            # 翻译标题和元信息
            logger.info(f"[{project_id}] Translating title and metadata")
            progress.current_step = "翻译标题"
            self._notify_progress(on_progress, "翻译标题", translated_count, total_paragraphs)
            await self._translate_title_and_metadata(project)
            self._save_meta(project_id, project)

            # 翻译章节标题
            logger.info(f"[{project_id}] Translating section titles")
            progress.current_step = "翻译章节标题"
            self._notify_progress(on_progress, "翻译章节标题", translated_count, total_paragraphs)
            await self._translate_section_titles(project, analysis)

            # 更新项目状态为"翻译中"
            self._set_active_status(project_id, project, ProjectStatus.IN_PROGRESS)

            # 逐章节翻译
            logger.info(f"[{project_id}] Starting section translation (mode: {self.translation_mode})")

            # 收集所有翻译结果用于一致性审查
            all_translations = {}
            for i, section in enumerate(project.sections):
                progress.current_section = section.title
                progress.current_step = f"翻译章节 {i+1}/{total_sections}"
                self._run_section_prescan(project_id, section, progress)

                # 断点续传：检查章节是否已全部翻译
                section_paragraph_count = len(section.paragraphs)
                translated_in_section = self._count_translated_paragraphs(section)
                
                if translated_in_section == section_paragraph_count and section_paragraph_count > 0:
                    # 整个章节已翻译，跳过
                    logger.info(
                        f"[{project_id}] Skipping section {section.section_id}: "
                        f"all {section_paragraph_count} paragraphs already translated"
                    )
                    translated_count += section_paragraph_count
                    progress.translated_sections += 1
                    progress.translated_paragraphs += section_paragraph_count
                    
                    # 收集已有翻译用于一致性审查
                    all_translations[section.section_id] = self._collect_section_translations(section)
                    
                    self._notify_progress(
                        on_progress,
                        f"跳过: {section.title} (已翻译)",
                        translated_count,
                        total_paragraphs,
                    )
                    continue

                self._notify_progress(
                    on_progress,
                    f"翻译: {section.title}",
                    translated_count,
                    total_paragraphs,
                )

                try:
                    # 根据翻译模式选择翻译方法
                    if self.translation_mode == self.TRANSLATION_MODE_SECTION:
                        # 章节级批量翻译（粗粒度）
                        translations = await self._translate_section_batch(
                            section=section,
                            section_index=i,
                            total_sections=total_sections,
                            all_sections=project.sections,
                            analysis=analysis
                        )

                        # 保存翻译结果到段落并收集结果
                        all_translations[section.section_id] = self._apply_section_batch_translations(
                            section,
                            translations,
                        )

                    else:
                        # 四步法翻译（细粒度）
                        result = self.translator.translate_section(
                            section=section,
                            all_sections=project.sections,
                            on_progress=self._create_section_callback(
                                section.title,
                                on_progress,
                                translated_count,
                                total_paragraphs,
                                section_paragraph_count,
                            )
                        )

                        self._apply_four_step_translations(section, result)
                        all_translations[section.section_id] = result.translations

                    # 保存章节
                    self.project_manager.save_section(project_id, section)

                    # 更新进度
                    progress.translated_sections += 1
                    translated_count += len(section.paragraphs)
                    progress.translated_paragraphs += len(section.paragraphs)
                    
                    # 发送章节完成进度
                    self._notify_progress(
                        on_progress,
                        f"完成: {section.title}",
                        translated_count,
                        total_paragraphs,
                    )

                    logger.info(
                        f"[{project_id}] Section {section.section_id} completed: "
                        f"{len(section.paragraphs)} paragraphs"
                    )

                except Exception as e:
                    error_msg = f"Failed to translate section {section.section_id}: {str(e)}"
                    logger.error(f"[{project_id}] {error_msg}")
                    self._record_error(progress, error_msg, section.section_id)

            # Phase 2: 一致性审查（优化：新增）
            logger.info(f"[{project_id}] Starting Phase 2: Consistency Review")
            progress.current_step = "一致性审查"
            self._notify_progress(on_progress, "一致性审查", translated_count, total_paragraphs)

            consistency_report = None
            try:
                consistency_report = self.consistency_reviewer.review(
                    sections=project.sections,
                    translations=all_translations,
                    article_analysis=analysis,
                    term_tracker=self.context_manager.term_tracker
                )

                # 记录一致性审查结果
                logger.info(
                    f"[{project_id}] Consistency review completed: "
                    f"{len(consistency_report.issues)} issues found, "
                    f"{len(consistency_report.auto_fixable)} auto-fixable"
                )

                # 如果有可自动修复的问题，应用修复
                if consistency_report.auto_fixable:
                    logger.info(f"[{project_id}] Applying {len(consistency_report.auto_fixable)} auto-fixes...")
                    all_translations = self.consistency_reviewer.auto_fix(
                        all_translations,
                        consistency_report.auto_fixable
                    )

                    # 更新段落翻译
                    for section in project.sections:
                        if section.section_id in all_translations:
                            for j, translation in enumerate(all_translations[section.section_id]):
                                if j < len(section.paragraphs):
                                    para = section.paragraphs[j]
                                    para.add_translation(translation, 'gemini_refined')
                            self.project_manager.save_section(project_id, section)

            except Exception as e:
                logger.error(f"[{project_id}] Consistency review failed: {str(e)}")
                # 一致性审查失败不影响翻译完成状态

            # 翻译完成
            progress.finished_at = datetime.now()
            progress.current_step = "翻译完成"

            # 更新项目状态为"已完成"
            project.status = self._final_status_after_success(original_status)
            self._save_meta(project_id, project)

            logger.info(f"[{project_id}] Translation completed")

            # 构建返回结果（包含一致性报告）
            result = {
                "project_id": project_id,
                "status": "completed",
                "total_sections": progress.total_sections,
                "translated_sections": progress.translated_sections,
                "total_paragraphs": progress.total_paragraphs,
                "translated_paragraphs": progress.translated_paragraphs,
                "error_count": len(progress.errors),
                "errors": progress.errors,
                "started_at": progress.started_at.isoformat(),
                "finished_at": progress.finished_at.isoformat(),
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
                            "auto_fixable": issue.auto_fixable
                        }
                        for issue in consistency_report.manual_review[:10]  # 最多返回10个需人工审核的问题
                    ]
                }

            return result

        except Exception as e:
            logger.error(f"[{project_id}] Translation failed: {str(e)}")
            self._record_error(progress, str(e))
            progress.finished_at = datetime.now()

            # 更新项目状态为失败
            project.status = original_status
            self._save_meta(project_id, project)

            return {
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
                "errors": progress.errors,
            }

    def _run_section_prescan(
        self,
        project_id: str,
        section: Section,
        progress: TranslationProgress,
    ) -> None:
        """Run optional section prescan and record terminology conflicts."""
        if not hasattr(self.translator, "prescan_section"):
            return

        try:
            prescan_result = self.translator.prescan_section(
                section=section,
                on_conflict=lambda conflict: progress.errors.append({
                    "type": "term_conflict",
                    "term": conflict.term,
                    "existing": conflict.existing_translation,
                    "new": conflict.new_translation,
                    "section_id": section.section_id,
                    "timestamp": datetime.now().isoformat(),
                }),
            )
            if prescan_result:
                logger.info(
                    f"[{project_id}] Section {section.section_id} prescan: "
                    f"{len(prescan_result.new_terms)} new terms found"
                )
        except Exception as exc:
            logger.warning(
                f"[{project_id}] Section {section.section_id} prescan skipped due to error: {exc}"
            )

    def _count_translated_paragraphs(self, section: Section) -> int:
        """Count paragraphs that already have a usable translation."""
        return sum(
            1
            for paragraph in section.paragraphs
            if paragraph.status in (ParagraphStatus.TRANSLATED, ParagraphStatus.APPROVED)
            or bool(paragraph.confirmed)
            or bool(paragraph.translations)
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
            collected.append(translation)

            paragraph = paragraph_map.get(para_id)
            if paragraph:
                paragraph.add_translation(translation, 'gemini')
                paragraph.status = ParagraphStatus.TRANSLATED

        return collected

    def _apply_four_step_translations(self, section: Section, result) -> None:
        """Apply four-step translations and optional AI insight to section paragraphs."""
        for index, translation in enumerate(result.translations):
            if index >= len(section.paragraphs):
                continue

            paragraph = section.paragraphs[index]
            paragraph.add_translation(translation, 'gemini')
            paragraph.status = ParagraphStatus.TRANSLATED

            if not hasattr(paragraph, 'ai_insight'):
                paragraph.ai_insight = self._build_ai_insight(result, paragraph, index)

    def _collect_section_translations(self, section: Section) -> List[str]:
        """Collect best-effort translation text for a section."""
        return [
            paragraph.confirmed
            or (list(paragraph.translations.values())[0].text if paragraph.translations else "")
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
                    estimated_current = base_count + int((current / total) * section_paragraphs)
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
                "refine": bool(result.reflection and not result.reflection.is_excellent)
            }
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
                "accuracy": result.reflection.accuracy_score
            }

        if result.reflection and result.reflection.issues:
            insight["issues"] = [
                {
                    "type": issue.issue_type,
                    "description": issue.description
                }
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
        with self._progress_lock:
            self._evict_stale_progress()
            progress = self._progress_cache.get(project_id)

        if not progress:
            # 如果没有缓存进度，从项目状态推断
            project = self._load_project_with_sections(project_id)

            if project.status == ProjectStatus.REVIEWING:
                # 已完成
                total_paragraphs = sum(len(s.paragraphs) for s in project.sections)
                translated = sum(
                    1 for s in project.sections
                    for p in s.paragraphs
                    if p.status == ParagraphStatus.TRANSLATED or p.status == ParagraphStatus.APPROVED
                )

                return {
                    "status": "completed",
                    "progress_percent": (translated / total_paragraphs * 100) if total_paragraphs > 0 else 0,
                    "translated_paragraphs": translated,
                    "total_paragraphs": total_paragraphs,
                }
            elif project.status == ProjectStatus.IN_PROGRESS:
                return {"status": "processing"}
            else:
                return {"status": "not_started"}

        return {
            "status": "completed" if progress.is_complete else "processing",
            **progress.to_dict()
        }

    async def cancel_translation(self, project_id: str) -> Dict:
        """
        取消翻译任务

        Args:
            project_id: 项目ID

        Returns:
            Dict: 取消结果
        """
        with self._progress_lock:
            progress = self._progress_cache.pop(project_id, None)

        if progress is not None:
            progress.finished_at = datetime.now()
            progress.current_step = "已取消"

            # 更新项目状态
            project = self._load_project_with_sections(project_id)
            project.status = progress.original_status
            self._save_meta(project_id, project)

            return {"status": "cancelled", "project_id": project_id}

        return {"status": "not_found", "project_id": project_id}

    def _can_transition_to_active_status(self, status: ProjectStatus) -> bool:
        """Whether service can temporarily move project into active translation status."""
        return status not in (ProjectStatus.REVIEWING, ProjectStatus.COMPLETED)

    def _final_status_after_success(self, original_status: ProjectStatus) -> ProjectStatus:
        """Resolve final status while preserving advanced existing states."""
        if original_status in (ProjectStatus.REVIEWING, ProjectStatus.COMPLETED):
            return original_status
        return ProjectStatus.REVIEWING

    def _save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息。"""
        if meta.id != project_id:
            raise ValueError(f"Project id mismatch: {project_id} != {meta.id}")
        self.project_manager.save_meta(meta)

    async def _translate_title_and_metadata(self, project: ProjectMeta) -> None:
        """
        翻译文章标题和元信息

        Args:
            project: 项目元信息
        """
        # 翻译文章标题
        if project.title and not project.title_translation:
            try:
                # 检查 LLM 是否有 translate_title 方法
                if hasattr(self.llm, 'translate_title'):
                    project.title_translation = self.llm.translate_title(project.title)
                else:
                    # 使用通用翻译
                    prompt = f"请将以下标题翻译成中文，保持简洁：\n\n{project.title}\n\n请直接输出翻译，不要添加任何解释："
                    project.title_translation = self.llm.generate(prompt, temperature=0.3)
                logger.info(f"Title translated: {project.title} -> {project.title_translation}")
            except Exception as e:
                logger.error(f"Failed to translate title: {e}")

        # 翻译元信息
        if project.metadata:
            try:
                if hasattr(self.llm, 'translate_metadata'):
                    result = self.llm.translate_metadata(
                        authors=project.metadata.authors,
                        date=project.metadata.published_date,
                        subtitle=project.metadata.subtitle
                    )
                    if result.get("subtitle"):
                        project.metadata.subtitle = result["subtitle"]
                elif project.metadata.subtitle:
                    # 使用通用翻译
                    prompt = f"请将以下副标题翻译成中文：\n\n{project.metadata.subtitle}\n\n请直接输出翻译："
                    project.metadata.subtitle = self.llm.generate(prompt, temperature=0.3)
            except Exception as e:
                logger.error(f"Failed to translate metadata: {e}")

    async def _translate_section_titles(
        self,
        project: ProjectMeta,
        analysis: ArticleAnalysis
    ) -> None:
        """
        翻译所有章节标题

        Args:
            project: 项目元信息
            analysis: 文章分析结果
        """
        for section in project.sections:
            if section.title and not section.title_translation:
                try:
                    # 构建上下文
                    context = f"这是一篇关于 {analysis.theme} 的文章中的章节标题。"

                    if hasattr(self.llm, 'translate_title'):
                        section.title_translation = self.llm.translate_title(
                            section.title,
                            context={"article_theme": analysis.theme}
                        )
                    else:
                        prompt = f"""请将以下章节标题翻译成中文。

{context}

原文标题：{section.title}

请直接输出翻译，不要添加任何解释："""
                        section.title_translation = self.llm.generate(prompt, temperature=0.3)

                    logger.info(f"Section title translated: {section.title} -> {section.title_translation}")
                except Exception as e:
                    logger.error(f"Failed to translate section title: {e}")

    async def _translate_section_batch(
        self,
        section: Section,
        section_index: int,
        total_sections: int,
        all_sections: List[Section],
        analysis: ArticleAnalysis
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

        for para in section.paragraphs:
            section_lines.append(f"[{para.id}] {para.source}")
            paragraph_ids.append(para.id)

        section_text = "\n\n".join(section_lines)

        # 构建上下文
        context = {
            "article_theme": analysis.theme,
            "section_position": f"第 {section_index + 1}/{total_sections} 章节",
            "previous_section_title": all_sections[section_index - 1].title if section_index > 0 else "无",
            "next_section_title": all_sections[section_index + 1].title if section_index < total_sections - 1 else "无",
            "glossary": [
                {"original": term.term, "translation": term.translation}
                for term in analysis.terminology[:20]
                if term.translation
            ],
            "guidelines": analysis.guidelines
        }

        # 检查 LLM 是否有 translate_section 方法
        if hasattr(self.llm, 'translate_section'):
            return self.llm.translate_section(
                section_text=section_text,
                section_title=section.title,
                context=context,
                paragraph_ids=paragraph_ids
            )
        else:
            # 使用通用翻译（降级方案）
            translations = []
            for para in section.paragraphs:
                translation = self.llm.translate(para.source, context=context)
                translations.append({"id": para.id, "translation": translation})
            return translations
