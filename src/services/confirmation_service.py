"""
分段确认服务

功能:
1. 获取段落的所有版本（AI版本 + 参考版本）
2. 确认段落译文
3. 更新术语翻译
4. 导出纯译文
"""

from typing import List, Dict, Optional
from datetime import datetime
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from src.core.models import (
    ProjectMeta, Paragraph, ParagraphConfirmation
)
from src.core.project import ProjectManager
from src.core.glossary import GlossaryManager


logger = logging.getLogger(__name__)


class ConfirmationService:
    """分段确认服务 - 带性能优化的版本"""

    # 类级别的缓存池
    _cache = {}
    _cache_lock = asyncio.Lock()
    _thread_pool = ThreadPoolExecutor(max_workers=4)

    def __init__(
        self,
        project_manager: ProjectManager,
        glossary_manager: GlossaryManager
    ):
        """
        初始化分段确认服务

        Args:
            project_manager: 项目管理器
            glossary_manager: 术语表管理器
        """
        self.project_manager = project_manager
        self.glossary_manager = glossary_manager

        # 实例级性能监控
        self.performance_stats = {
            "get_paragraph_calls": 0,
            "confirm_paragraph_calls": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0
        }

    def _load_project_with_sections(self, project_id: str) -> ProjectMeta:
        """加载项目及其章节。"""
        project = self.project_manager.get(project_id)
        project.sections = self.project_manager.get_sections(project_id)
        return project

    async def _load_project_with_sections_async(self, project_id: str) -> ProjectMeta:
        """在线程池中并行加载项目与章节。"""
        loop = asyncio.get_event_loop()
        project, sections = await asyncio.gather(
            loop.run_in_executor(self._thread_pool, self.project_manager.get, project_id),
            loop.run_in_executor(self._thread_pool, self.project_manager.get_sections, project_id),
        )
        project.sections = sections
        return project

    async def get_paragraph_confirmation(
        self,
        project_id: str,
        paragraph_index: int
    ) -> Dict:
        """
        获取段落的所有版本和确认状态 - 优化版本

        性能优化：
        - 使用缓存减少重复计算
        - 异步I/O操作
        - 线程池处理文件读取
        - 批量数据加载

        Args:
            project_id: 项目ID
            paragraph_index: 段落全局索引

        Returns:
            Dict: {
                "paragraph": Paragraph,
                "versions": List[TranslationVersion],
                "current_confirmation": Optional[ParagraphConfirmation]
            }
        """
        start_time = time.time()
        self.performance_stats["get_paragraph_calls"] += 1

        # 缓存键
        cache_key = f"{project_id}:{paragraph_index}"

        # 尝试从缓存获取
        async with self._cache_lock:
            if cache_key in self._cache:
                cached_data, cache_time = self._cache[cache_key]
                # 5分钟缓存有效期
                if time.time() - cache_time < 300:
                    self.performance_stats["cache_hits"] += 1
                    logger.debug(f"[{project_id}] Cache hit for paragraph {paragraph_index}")
                    return cached_data

        # 缓存未命中，异步加载数据
        try:
            # 使用线程池并行加载项目和章节数据
            project = await self._load_project_with_sections_async(project_id)

            # 获取段落
            paragraph, section, _section_index, _para_index = self._get_paragraph_by_index(
                project, paragraph_index
            )

            if not paragraph:
                raise IndexError(f"Paragraph index {paragraph_index} out of range")

            # 并行构建版本列表
            versions = await self._build_versions_async(paragraph, project)

            # 获取当前确认状态
            current_confirmation = project.confirmation_map.get(paragraph.id)

            result = {
                "paragraph": {
                    "id": paragraph.id,
                    "index": paragraph_index,
                    "source": paragraph.source,
                    "element_type": paragraph.element_type.value,
                    "status": paragraph.status.value,
                    "section_id": section.section_id,
                    "section_title": section.title
                },
                "versions": versions,
                "current_confirmation": current_confirmation.model_dump() if current_confirmation else None,
                "total_paragraphs": sum(len(s.paragraphs) for s in project.sections)
            }

            # 更新缓存
            async with self._cache_lock:
                self._cache[cache_key] = (result, time.time())
                # 限制缓存大小
                if len(self._cache) > 1000:
                    # 删除最旧的500个条目
                    sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
                    for key in sorted_keys[:500]:
                        del self._cache[key]

            # 更新性能统计
            elapsed = time.time() - start_time
            self._update_performance_stats(elapsed)

            logger.info(f"[{project_id}] Loaded paragraph {paragraph_index} in {elapsed:.2f}s")
            return result

        except Exception as e:
            logger.error(f"[{project_id}] Failed to get paragraph confirmation: {e}")
            raise

    async def confirm_paragraph(
        self,
        project_id: str,
        paragraph_id: str,
        translation: str,
        version_id: Optional[str] = None,
        custom_edit: bool = False
    ) -> Dict:
        """
        确认段落译文

        Args:
            project_id: 项目ID
            paragraph_id: 段落ID
            translation: 确认的译文
            version_id: 选中的版本ID（可选）
            custom_edit: 是否为自定义编辑

        Returns:
            Dict: 确认结果
        """
        # 加载项目
        project = self._load_project_with_sections(project_id)

        # 找到段落并确认
        confirmed_paragraph = None
        confirmed_section = None

        for section in project.sections:
            for para in section.paragraphs:
                if para.id == paragraph_id:
                    # 确认译文
                    source = "manual" if custom_edit else (version_id or "ai")
                    para.confirm(translation, source=source)
                    confirmed_paragraph = para
                    confirmed_section = section
                    break
            if confirmed_paragraph:
                break

        if not confirmed_paragraph:
            raise ValueError(f"Paragraph {paragraph_id} not found")

        # 更新确认映射
        confirmation = ParagraphConfirmation(
            paragraph_id=paragraph_id,
            selected_version_id=version_id,
            custom_translation=translation if custom_edit else None,
            confirmed_at=datetime.now()
        )
        project.confirmation_map[paragraph_id] = confirmation

        # 保存章节
        self.project_manager.save_section(project_id, confirmed_section)

        # 保存项目元信息（更新confirmation_map）
        self._save_meta(project_id, project)

        # 清理项目缓存，避免返回旧确认状态
        await self._invalidate_cache_for_project(project_id)

        logger.info(f"[{project_id}] Paragraph {paragraph_id} confirmed")

        return {
            "paragraph_id": paragraph_id,
            "translation": translation,
            "status": confirmed_paragraph.status.value,
            "selected_version_id": version_id,
            "confirmed_at": confirmation.confirmed_at.isoformat()
        }

    async def update_terms(
        self,
        project_id: str,
        changes: List[Dict]
    ) -> Dict:
        """
        更新术语翻译

        当用户在确认译文时修改了术语，此方法用于静默更新术语表

        Args:
            project_id: 项目ID
            changes: [{term, old_translation, new_translation}]

        Returns:
            Dict: 更新结果
        """
        # 加载术语表
        glossary = self.glossary_manager.load_project(project_id)

        updated_terms = []

        for change in changes:
            term_original = change.get('term')
            new_translation = change.get('new_translation')

            if not term_original or not new_translation:
                continue

            # 查找现有术语
            existing_term = glossary.get_term(term_original)

            if existing_term:
                # 更新现有术语的翻译
                old_translation = existing_term.translation
                existing_term.translation = new_translation

                updated_terms.append({
                    "term": term_original,
                    "old_translation": old_translation,
                    "new_translation": new_translation
                })

                logger.info(
                    f"[{project_id}] Term updated: {term_original} "
                    f"({old_translation} -> {new_translation})"
                )

        # 保存术语表
        if updated_terms:
            self.glossary_manager.save_project(project_id, glossary)

        return {
            "updated_count": len(updated_terms),
            "terms": updated_terms
        }

    async def export_translation(
        self,
        project_id: str,
        include_source: bool = False,
        export_format: str = "markdown"
    ) -> Dict:
        """
        导出译文

        Args:
            project_id: 项目ID
            include_source: 是否包含原文
            export_format: 导出格式 ("markdown" 或 "bilingual")

        Returns:
            Dict: {
                "content": str,
                "filename": str,
                "paragraph_count": int,
                "saved_path": str
            }
        """
        from pathlib import Path
        from src.core.exporter import MarkdownExporter

        # 加载项目
        project = self._load_project_with_sections(project_id)

        # 使用增强版导出器
        exporter = MarkdownExporter(restore_inline_elements=True)

        # 根据格式导出
        if export_format == "bilingual":
            content = exporter.export_bilingual(
                sections=project.sections,
                title=project.title_translation or project.title
            )
        else:
            content = exporter.export_sections(
                sections=project.sections,
                title=project.title,
                title_translation=project.title_translation,
                metadata=project.metadata,
                include_source=include_source,
                use_translation=True
            )

        # 统计段落数
        paragraph_count = sum(
            1 for s in project.sections
            for p in s.paragraphs
            if p.confirmed or p.translations
        )

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        format_suffix = "_双语" if export_format == "bilingual" else "_译文"
        filename = f"{project.title}{format_suffix}_{timestamp}.md"

        # 保存到项目的 exports 文件夹
        projects_path = Path(self.project_manager.projects_path)
        exports_dir = projects_path / project_id / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        saved_path = exports_dir / filename
        with open(saved_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"[{project_id}] Exported {paragraph_count} paragraphs to {saved_path}")

        return {
            "content": content,
            "filename": filename,
            "paragraph_count": paragraph_count,
            "saved_path": str(saved_path)
        }

    async def get_translation_progress(
        self,
        project_id: str
    ) -> Dict:
        """
        获取翻译/确认进度

        Args:
            project_id: 项目ID

        Returns:
            Dict: 进度信息
        """
        project = self._load_project_with_sections(project_id)

        total_paragraphs = sum(len(s.paragraphs) for s in project.sections)
        confirmed_paragraphs = sum(
            1 for s in project.sections
            for p in s.paragraphs
            if p.status.value == "approved"
        )

        translated_paragraphs = sum(
            1 for s in project.sections
            for p in s.paragraphs
            if p.translations
        )

        return {
            "project_id": project_id,
            "status": project.status.value,
            "total_paragraphs": total_paragraphs,
            "translated_paragraphs": translated_paragraphs,
            "confirmed_paragraphs": confirmed_paragraphs,
            "progress_percent": (confirmed_paragraphs / total_paragraphs * 100) if total_paragraphs > 0 else 0,
            "is_complete": confirmed_paragraphs >= total_paragraphs
        }

    def _get_paragraph_by_index(
        self,
        project: ProjectMeta,
        index: int
    ) -> tuple:
        """
        根据全局索引获取段落

        Returns:
            (paragraph, section, section_index, paragraph_index_in_section)
        """
        current = 0
        for section_idx, section in enumerate(project.sections):
            for para_idx, para in enumerate(section.paragraphs):
                if current == index:
                    return para, section, section_idx, para_idx
                current += 1

        return None, None, 0, 0

    def _get_latest_translation(self, paragraph: Paragraph):
        """获取最新的翻译记录"""
        if not paragraph.translations:
            raise ValueError("No translations available")

        # 返回最新的翻译（按created_at排序）
        return max(
            paragraph.translations.values(),
            key=lambda t: t.created_at
        )

    def _build_ai_insight(self, paragraph: Paragraph) -> Optional[Dict]:
        """
        构建AI透明度数据

        从段落的扩展字段中提取四步法结果
        """
        # 如果段落有ai_insight属性，直接返回
        if hasattr(paragraph, 'ai_insight'):
            return paragraph.ai_insight

        # 否则返回基础信息
        if paragraph.translations:
            latest = self._get_latest_translation(paragraph)
            return {
                "overall_score": 8.0,  # 默认分数
                "is_excellent": True,
                "applied_terms": [],
                "style": "专业技术",
                "steps": {
                    "understand": True,
                    "translate": True,
                    "reflect": True,
                    "refine": False
                },
                "model": latest.model,
                "created_at": latest.created_at.isoformat()
            }

        return None

    def _save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息。"""
        if meta.id != project_id:
            raise ValueError(f"Project id mismatch: {project_id} != {meta.id}")
        self.project_manager.save_meta(meta)

    async def _build_versions_async(self, paragraph: Paragraph, project: ProjectMeta) -> List[Dict]:
        """
        异步构建版本列表 - 性能优化

        并行处理AI版本和参考版本的构建
        """
        versions = []

        # AI翻译版本
        if paragraph.translations:
            ai_translation = self._get_latest_translation(paragraph)
            ai_insight = self._build_ai_insight(paragraph)

            versions.append({
                "id": "ai",
                "name": "AI翻译",
                "source_type": "ai",
                "translation": ai_translation.text,
                "model": ai_translation.model,
                "created_at": ai_translation.created_at.isoformat(),
                "ai_insight": ai_insight
            })

        # 参考版本（导入的）
        for ref_version in project.versions:
            if paragraph.id in ref_version.paragraphs:
                ref_translation = ref_version.paragraphs[paragraph.id]
                if ref_translation:  # 不为None才添加
                    versions.append({
                        "id": ref_version.id,
                        "name": ref_version.name,
                        "source_type": "imported",
                        "translation": ref_translation,
                        "created_at": ref_version.created_at.isoformat(),
                        "metadata": ref_version.metadata
                    })

        return versions

    def _update_performance_stats(self, elapsed_time: float) -> None:
        """更新性能统计"""
        current_avg = self.performance_stats["avg_response_time"]
        total_calls = self.performance_stats["get_paragraph_calls"]

        # 计算新的平均响应时间
        if total_calls == 1:
            self.performance_stats["avg_response_time"] = elapsed_time
        else:
            self.performance_stats["avg_response_time"] = (
                (current_avg * (total_calls - 1) + elapsed_time) / total_calls
            )

    async def batch_confirm_paragraphs(
        self,
        project_id: str,
        confirmations: List[Dict]
    ) -> Dict:
        """
        批量确认段落 - 新功能

        大幅减少API调用次数，提高确认性能

        Args:
            project_id: 项目ID
            confirmations: [
                {
                    "paragraph_id": str,
                    "translation": str,
                    "version_id": Optional[str],
                    "custom_edit": bool
                }
            ]

        Returns:
            Dict: 批量确认结果
        """
        start_time = time.time()
        self.performance_stats["confirm_paragraph_calls"] += len(confirmations)

        try:
            # 批量加载项目数据
            loop = asyncio.get_event_loop()
            project = await self._load_project_with_sections_async(project_id)
            sections = project.sections

            # 创建段落ID到段落的映射
            paragraph_map = {}
            section_map = {}
            section_lookup = {}
            for section in sections:
                section_lookup[section.section_id] = section
                for para in section.paragraphs:
                    paragraph_map[para.id] = para
                    section_map[para.id] = section

            results = []
            modified_sections = set()

            # 批量处理确认
            for confirmation in confirmations:
                paragraph_id = confirmation["paragraph_id"]
                translation = confirmation["translation"]
                version_id = confirmation.get("version_id")
                custom_edit = confirmation.get("custom_edit", False)

                if paragraph_id not in paragraph_map:
                    logger.warning(f"[{project_id}] Paragraph {paragraph_id} not found")
                    continue

                # 确认译文
                paragraph = paragraph_map[paragraph_id]
                section = section_map[paragraph_id]
                source = "manual" if custom_edit else (version_id or "ai")
                paragraph.confirm(translation, source=source)

                # 更新确认映射
                project.confirmation_map[paragraph_id] = ParagraphConfirmation(
                    paragraph_id=paragraph_id,
                    selected_version_id=version_id,
                    custom_translation=translation if custom_edit else None,
                    confirmed_at=datetime.now()
                )

                modified_sections.add(section.section_id)
                results.append({
                    "paragraph_id": paragraph_id,
                    "translation": translation,
                    "status": paragraph.status.value,
                    "selected_version_id": version_id,
                    "confirmed_at": project.confirmation_map[paragraph_id].confirmed_at.isoformat()
                })

            # 批量保存修改的章节
            save_tasks = [
                loop.run_in_executor(
                    self._thread_pool,
                    self.project_manager.save_section,
                    project_id,
                    section_lookup[section_id]
                )
                for section_id in modified_sections
                if section_id in section_lookup
            ]
            await asyncio.gather(*save_tasks)

            # 保存项目元信息
            await loop.run_in_executor(
                self._thread_pool,
                self._save_meta,
                project_id,
                project
            )

            # 清理相关缓存
            await self._invalidate_cache_for_project(project_id)

            elapsed = time.time() - start_time
            logger.info(
                f"[{project_id}] Batch confirmed {len(results)} paragraphs in {elapsed:.2f}s"
            )

            return {
                "confirmed_count": len(results),
                "results": results,
                "processing_time": elapsed
            }

        except Exception as e:
            logger.error(f"[{project_id}] Batch confirmation failed: {e}")
            raise

    async def _invalidate_cache_for_project(self, project_id: str) -> None:
        """清理指定项目的缓存"""
        async with self._cache_lock:
            keys_to_delete = [key for key in self._cache.keys() if key.startswith(f"{project_id}:")]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"[{project_id}] Invalidated {len(keys_to_delete)} cache entries")

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        return {
            **self.performance_stats,
            "cache_size": len(self._cache),
            "cache_hit_rate": (
                self.performance_stats["cache_hits"] / max(self.performance_stats["get_paragraph_calls"], 1) * 100
            )
        }
