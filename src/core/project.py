"""
Translation Agent - Project Manager

Manage translation projects: create, read, update, delete.
"""

import json
import logging
import re
import threading
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from .models import (
    ProjectMeta, ProjectStatus, ProjectConfig,
    Section, Paragraph, ParagraphStatus, ElementType
)
from .glossary import GlossaryManager
from .inline_recovery_service import InlineRecoveryService
from .project_export_service import ProjectExportService
from .project_lifecycle_service import ProjectLifecycleService
from .project_repository import ProjectRepository
from .file_utils import write_text_atomic, write_json_atomic, read_json
from .limits import TranslationLimits


class ProjectManager:
    """项目管理器"""

    def __init__(self, projects_path: str = "projects"):
        """
        初始化项目管理器

        Args:
            projects_path: 项目目录路径
        """
        self.projects_path = Path(projects_path)
        self.projects_path.mkdir(parents=True, exist_ok=True)
        self.glossary_manager = GlossaryManager(projects_path=projects_path)
        self.inline_recovery = InlineRecoveryService(logger)
        self.project_export_service = ProjectExportService(
            inline_recovery=self.inline_recovery,
            project_dir_resolver=self._project_dir,
            write_text=self._write_text,
            write_json=self._write_json,
            get_project=self.get,
            get_sections=self.get_sections,
            best_translation_text=self._best_translation_text,
        )
        self.project_repository = ProjectRepository(
            project_dir_resolver=self._project_dir,
            read_json=self._read_json,
            write_json=self._write_json,
            write_text=self._write_text,
            get_project=self.get,
            render_source_block_markdown=self._render_source_block_markdown,
            render_markdown_line=self._format_markdown_line,
            best_translation_text=self._best_translation_text,
            logger_=logger,
        )
        self.project_lifecycle_service = ProjectLifecycleService(
            project_dir_resolver=self._project_dir,
            write_text=self._write_text,
            save_section=self._save_section,
            save_meta=self._save_meta,
            glossary_manager=self.glossary_manager,
            logger_=logger,
        )
        self._section_locks: OrderedDict[str, threading.RLock] = OrderedDict()
        self._section_locks_guard = threading.Lock()
        self._section_locks_max = TranslationLimits.SECTION_LOCK_CACHE_SIZE

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_path / project_id

    def _write_text(self, path: Path, content: str) -> None:
        write_text_atomic(path, content)

    def _read_json(self, path: Path) -> Any:
        return read_json(path)

    def _write_json(self, path: Path, payload: Any) -> None:
        write_json_atomic(path, payload)

    def _section_lock_key(self, project_id: str, section_id: str) -> str:
        return f"{project_id}:{section_id}"

    def _get_section_lock(self, project_id: str, section_id: str) -> threading.RLock:
        lock_key = self._section_lock_key(project_id, section_id)
        with self._section_locks_guard:
            existing_lock = self._section_locks.get(lock_key)
            if existing_lock is not None:
                self._section_locks.move_to_end(lock_key)
                return existing_lock
            new_lock = threading.RLock()
            self._section_locks[lock_key] = new_lock
            # Evict oldest entries when exceeding the cap, but only if not held
            while len(self._section_locks) > self._section_locks_max:
                oldest_key, oldest_lock = next(iter(self._section_locks.items()))
                # Try to acquire non-blocking to check if the lock is free
                if not oldest_lock.acquire(blocking=False):
                    logger.debug("Skipping eviction of held lock: %s", oldest_key)
                    break
                oldest_lock.release()
                self._section_locks.pop(oldest_key)
            return new_lock

    def _best_translation_text(self, paragraph: Paragraph, fallback_to_source: bool = True) -> str:
        """Get best available translation text for a paragraph."""
        return paragraph.best_translation_text(fallback_to_source=fallback_to_source)

    def _format_markdown_line(self, element_type: ElementType, text: str) -> str:
        """Format one markdown line based on paragraph element type."""
        return self.inline_recovery.format_markdown_line(element_type, text)

    def _group_section_blocks(self, section: Section) -> list[list[Paragraph]]:
        return self.inline_recovery.group_section_blocks(section)

    def _section_display_title(self, section: Section) -> str:
        return self.project_export_service.section_display_title(section)

    def _is_front_matter_section(self, section: Section) -> bool:
        return self.project_export_service.is_front_matter_section(section)

    def _should_render_section_heading(
        self, sections: list[Section], index: int, section: Section
    ) -> bool:
        return self.project_export_service.should_render_section_heading(sections, index, section)

    def _render_source_block_markdown(self, paragraphs: list[Paragraph]) -> str:
        return self.inline_recovery.render_source_block_markdown(paragraphs)

    def _render_block_markdown(
        self,
        paragraphs: list[Paragraph],
        fallback_to_source: bool = True,
    ) -> str:
        return self.inline_recovery.render_block_markdown(
            paragraphs,
            fallback_to_source=fallback_to_source,
        )

    def _smart_fallback_restore_inline_elements(
        self,
        source_text: str,
        translated_text: str,
        elements: List[Any],
        block_id: str
    ) -> str:
        return self.inline_recovery.smart_fallback_restore_inline_elements(
            source_text=source_text,
            translated_text=translated_text,
            elements=elements,
            block_id=block_id,
        )

    def _restore_single_link(
        self,
        source_text: str,
        translated_text: str,
        link_element: Any
    ) -> str:
        return self.inline_recovery.restore_single_link(
            source_text=source_text,
            translated_text=translated_text,
            link_element=link_element,
        )

    def _extract_chinese_word_candidates(
        self,
        text: str,
        center: int,
        max_candidates: int = 5
    ) -> list:
        return self.inline_recovery.extract_chinese_word_candidates(
            text=text,
            center=center,
            max_candidates=max_candidates,
        )

    def _find_best_match_window(
        self,
        text: str,
        center: int,
        estimated_length: int,
        reference: str,
        source_text: str = "",
        link_start: int = 0
    ) -> Optional[tuple]:
        return self.inline_recovery.find_best_match_window(
            text=text,
            center=center,
            estimated_length=estimated_length,
            reference=reference,
            source_text=source_text,
            link_start=link_start,
        )

    def _calculate_match_score(
        self,
        candidate: str,
        reference: str,
        candidate_pos: int,
        expected_pos: int,
        translated_text: str = "",
        before_context: list = None,
        after_context: list = None
    ) -> float:
        return self.inline_recovery.calculate_match_score(
            candidate=candidate,
            reference=reference,
            candidate_pos=candidate_pos,
            expected_pos=expected_pos,
            translated_text=translated_text,
            before_context=before_context,
            after_context=after_context,
        )

    def _calculate_match_score_old(
        self,
        candidate: str,
        reference: str,
        candidate_pos: int,
        expected_pos: int,
        translated_text: str = "",
        before_context: list = None,
        after_context: list = None
    ) -> float:
        """
        旧的复杂评分算法（保留作为参考）
        """
        # 1. Position score
        pos_diff = abs(candidate_pos - expected_pos)
        pos_score = 1.0 / (1.0 + pos_diff / 10.0)

        # 2. Length score
        has_alpha_ref = any(c.isalpha() and ord(c) < 128 for c in reference)
        has_alpha_cand = any(c.isalpha() and ord(c) < 128 for c in candidate)

        if has_alpha_ref and not has_alpha_cand:
            expected_chinese_len = len(reference) / 4.0
            len_diff = abs(len(candidate) - expected_chinese_len)
            len_score = 1.0 / (1.0 + len_diff / 2.0)
        else:
            len_ratio = min(len(candidate), len(reference)) / max(len(candidate), len(reference), 1)
            len_score = len_ratio

        # 3. Semantic features score
        semantic_score = 0.0

        if candidate and reference:
            if candidate[0] == reference[0]:
                semantic_score += 0.3

        has_digit_candidate = any(c.isdigit() for c in candidate)
        has_digit_reference = any(c.isdigit() for c in reference)
        if has_digit_candidate == has_digit_reference:
            semantic_score += 0.2

        has_alpha_candidate = any(c.isalpha() and ord(c) < 128 for c in candidate)
        has_alpha_reference = any(c.isalpha() and ord(c) < 128 for c in reference)
        if has_alpha_candidate == has_alpha_reference:
            semantic_score += 0.2

        if ' ' in reference and not has_alpha_candidate:
            if len(candidate) == 4:
                semantic_score += 0.3

        if has_alpha_reference == has_alpha_candidate:
            len_ratio = min(len(candidate), len(reference)) / max(len(candidate), len(reference), 1)
            if 0.7 <= len_ratio <= 1.3:
                semantic_score += 0.3

        if not has_alpha_candidate and translated_text:
            boundary_count = 0
            if candidate_pos == 0 or not ('\u4e00' <= translated_text[candidate_pos-1] <= '\u9fff'):
                boundary_count += 1
            candidate_end = candidate_pos + len(candidate)
            if candidate_end == len(translated_text) or not ('\u4e00' <= translated_text[candidate_end] <= '\u9fff'):
                boundary_count += 1

            if boundary_count == 2:
                semantic_score += 0.5
            elif boundary_count == 1:
                semantic_score += 0.2

            # Check if context words appear near the candidate
            candidate_start = candidate_pos
            candidate_end = candidate_pos + len(candidate)

            # Check before context
            if before_context and candidate_start > 0:
                before_text = translated_text[max(0, candidate_start - 15):candidate_start]
                for word in before_context:
                    if word.lower() in before_text.lower():
                        context_score += 0.5
                        break

            # Check after context
            if after_context and candidate_end < len(translated_text):
                after_text = translated_text[candidate_end:min(len(translated_text), candidate_end + 15)]
                for word in after_context:
                    if word.lower() in after_text.lower():
                        context_score += 0.5
                        break

        # Combined score with weights
        return (
            pos_score * 0.20 +
            len_score * 0.15 +
            semantic_score * 0.40 +
            context_score * 0.25
        )

    def _preferred_export_title(self, meta: ProjectMeta) -> str:
        """Use translated article title for exports when available."""
        return self.project_export_service.preferred_export_title(meta)

    def _sanitize_export_filename_component(self, value: str, fallback: str) -> str:
        """Keep the original title readable while removing invalid filename chars."""
        return self.project_export_service.sanitize_export_filename_component(value, fallback)

    _VALID_EXPORT_FORMATS = {"en", "zh"}

    def _normalize_export_format(self, format: str = "zh") -> str:
        return self.project_export_service.normalize_export_format(format)

    def _build_export_filename(self, meta: ProjectMeta, format: str = "zh") -> str:
        return self.project_export_service.build_export_filename(meta, format=format)

    def get_export_filename(self, project_id: str, format: str = "zh") -> str:
        """Return the user-facing export filename for a project."""
        return self.project_export_service.get_export_filename(project_id, format=format)

    def get_export_path(self, project_id: str, format: str = "zh") -> Path:
        """Return the export file path for a project."""
        return self.project_export_service.get_export_path(project_id, format=format)

    def _looks_like_untranslated_residue(self, text: str) -> bool:
        return self.project_export_service.looks_like_untranslated_residue(text)

    def _build_export_lint_payload(
        self,
        meta: ProjectMeta,
        sections: list[Section],
    ) -> dict[str, Any]:
        return self.project_export_service.build_export_lint_payload(meta, sections)

    def _write_export_lint_artifact(
        self,
        project_id: str,
        payload: dict[str, Any],
    ) -> None:
        self.project_export_service.write_export_lint_artifact(project_id, payload)

    def create(
        self,
        name: str,
        html_path: str,
        config: Optional[ProjectConfig] = None
    ) -> ProjectMeta:
        """
        创建新项目

        Args:
            name: 项目名称
            html_path: HTML 文件路径
            config: 项目配置

        Returns:
            ProjectMeta: 项目元信息
        """
        return self.project_lifecycle_service.create_project(
            name=name,
            html_path=html_path,
            config=config,
        )

    def _copy_assets_directory(self, html_source: Path, project_dir: Path) -> None:
        """Copy HTML asset folder (e.g., *_files) into project directory."""
        self.project_lifecycle_service.copy_assets_directory(html_source, project_dir)

    def _find_assets_directory(self, html_source: Path) -> Optional[Path]:
        """Find related assets directory next to the HTML file."""
        return self.project_lifecycle_service.find_assets_directory(html_source)

    def get(self, project_id: str) -> ProjectMeta:
        """
        获取项目元信息

        Args:
            project_id: 项目 ID

        Returns:
            ProjectMeta: 项目元信息
        """
        meta_path = self._project_dir(project_id) / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")

        try:
            data = self._read_json(meta_path)
        except (json.JSONDecodeError, IOError) as e:
            raise FileNotFoundError(f"Failed to load project meta: {e}")

        try:
            meta = ProjectMeta(**data)
        except (TypeError, ValueError) as e:
            # meta.json 损坏，返回默认项目元信息
            logger.warning("Project %s meta.json is corrupted: %s", project_id, e)
            raise FileNotFoundError(f"Project meta is corrupted: {e}")

        # 修复进度显示问题：如果 total_paragraphs 为 0，尝试从 sections 重新计算
        if meta.progress.total_paragraphs == 0:
            try:
                sections = self.get_sections(project_id)
                if sections:  # 只要有章节就更新进度
                    meta.update_progress(sections)
                    # 仅在内存中更新，不保存到文件（避免文件锁问题）
            except Exception as e:
                # 静默忽略，返回原始数据
                logger.warning("Failed to recalculate progress for %s: %s", project_id, e)

        return meta

    def list_all(self) -> List[ProjectMeta]:
        """
        列出所有项目

        Returns:
            List[ProjectMeta]: 项目列表
        """
        projects = []
        for project_dir in self.projects_path.iterdir():
            if project_dir.is_dir():
                meta_path = project_dir / "meta.json"
                if meta_path.exists():
                    try:
                        projects.append(self.get(project_dir.name))
                    except Exception:
                        pass
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def delete(self, project_id: str) -> None:
        """
        删除项目

        Args:
            project_id: 项目 ID
        """
        self.project_lifecycle_service.delete_project(project_id)

    def get_sections(self, project_id: str) -> List[Section]:
        """
        获取项目所有章节

        Args:
            project_id: 项目 ID

        Returns:
            List[Section]: 章节列表
        """
        return self.project_repository.get_sections(project_id)

    def get_section(self, project_id: str, section_id: str) -> Optional[Section]:
        """
        获取单个章节

        Args:
            project_id: 项目 ID
            section_id: 章节 ID

        Returns:
            Optional[Section]: 章节，如果不存在返回 None
        """
        return self._load_section(project_id, section_id)

    def save_meta(self, meta: ProjectMeta) -> None:
        """Persist project metadata to disk."""
        self._save_meta(meta.id, meta)

    def save_section(self, project_id: str, section: Section) -> None:
        """
        保存章节

        Args:
            project_id: 项目 ID
            section: 章节
        """
        section_lock = self._get_section_lock(project_id, section.section_id)
        with section_lock:
            self._save_section(project_id, section)
            self._update_progress(project_id)

    def update_paragraph(
        self,
        project_id: str,
        section_id: str,
        paragraph_id: str,
        translation: Optional[str] = None,
        tokenized_text: Optional[str] = None,
        format_issues: Optional[List[str]] = None,
        status: Optional[ParagraphStatus] = None,
        model: str = "manual"
    ) -> Paragraph:
        """
        更新段落

        Args:
            project_id: 项目 ID
            section_id: 章节 ID
            paragraph_id: 段落 ID
            translation: 译文
            status: 状态
            model: 翻译来源

        Returns:
            Paragraph: 更新后的段落
        """
        section = self._load_section(project_id, section_id)
        if not section:
            raise FileNotFoundError(f"Section not found: {section_id}")

        # 找到段落
        paragraph = None
        for p in section.paragraphs:
            if p.id == paragraph_id:
                paragraph = p
                break

        if not paragraph:
            raise FileNotFoundError(f"Paragraph not found: {paragraph_id}")

        # Clear confirmation as soon as an approved paragraph is retranslated or edited.
        should_confirm = status == ParagraphStatus.APPROVED
        should_unconfirm = (
            paragraph.confirmed is not None
            and status is not None
            and status != ParagraphStatus.APPROVED
        )

        if translation is not None and not should_confirm:
            translation_changed = paragraph.best_translation_text() != translation
            should_unconfirm = should_unconfirm or translation_changed

        if should_unconfirm:
            paragraph.unconfirm(
                next_status=status or ParagraphStatus.MODIFIED,
                source=model,
            )

        # 更新译文
        if translation is not None:
            latest_record = paragraph.latest_translation(non_empty=True)
            resolved_tokenized = tokenized_text
            resolved_issues = list(format_issues or [])
            if (
                resolved_tokenized is None
                and latest_record is not None
                and latest_record.text == translation
            ):
                resolved_tokenized = latest_record.tokenized_text
                if not resolved_issues:
                    resolved_issues = list(latest_record.format_issues)

            paragraph.add_translation(
                translation,
                model,
                tokenized_text=resolved_tokenized,
                format_issues=resolved_issues,
            )
            if should_confirm:
                paragraph.confirm(
                    translation,
                    model,
                    tokenized_text=resolved_tokenized,
                    format_issues=resolved_issues,
                )

        # 更新状态
        if status is not None:
            paragraph.status = status

        # 保存
        self._save_section(project_id, section)
        self._update_progress(project_id)

        return paragraph

    def update_paragraph_locked(
        self,
        project_id: str,
        section_id: str,
        paragraph_id: str,
        translation: Optional[str] = None,
        tokenized_text: Optional[str] = None,
        format_issues: Optional[List[str]] = None,
        status: Optional[ParagraphStatus] = None,
        model: str = "manual"
    ) -> Paragraph:
        """Update one paragraph while holding the section write lock."""
        section_lock = self._get_section_lock(project_id, section_id)
        with section_lock:
            return self.update_paragraph(
                project_id,
                section_id,
                paragraph_id,
                translation=translation,
                tokenized_text=tokenized_text,
                format_issues=format_issues,
                status=status,
                model=model,
            )

    @contextmanager
    def section_lock(self, project_id: str, section_id: str):
        """Acquire the section-level write lock as a context manager."""
        lock = self._get_section_lock(project_id, section_id)
        with lock:
            yield

    def confirm_paragraph(
        self,
        project_id: str,
        section_id: str,
        paragraph_id: str,
        translation: str
    ) -> Paragraph:
        """
        确认段落译文

        Args:
            project_id: 项目 ID
            section_id: 章节 ID
            paragraph_id: 段落 ID
            translation: 确认的译文

        Returns:
            Paragraph: 更新后的段落
        """
        return self.update_paragraph_locked(
            project_id, section_id, paragraph_id,
            translation=translation,
            status=ParagraphStatus.APPROVED,
            model="manual"
        )

    def export(self, project_id: str, include_source: bool = False, format: str = 'zh') -> str:
        return self.project_export_service.export(
            project_id,
            include_source=include_source,
            format=format,
        )

    def export_source_markdown(self, project_id: str) -> str:
        return self.project_export_service.export_source_markdown(project_id)

    def export_markdown(self, project_id: str, include_source: bool = False) -> str:
        return self.project_export_service.export_markdown(
            project_id,
            include_source=include_source,
        )

    def generate_preview(self, project_id: str) -> str:
        return self.project_export_service.generate_preview(project_id)

    def _save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息"""
        self.project_repository.save_meta(project_id, meta)

    def _save_section(self, project_id: str, section: Section) -> None:
        """保存章节"""
        self.project_repository.save_section(
            project_id,
            section,
            grouped_blocks=self._group_section_blocks(section),
        )

    def _load_section(self, project_id: str, section_id: str) -> Optional[Section]:
        """加载章节"""
        return self.project_repository.load_section(project_id, section_id)

    def _update_progress(self, project_id: str) -> None:
        """更新项目进度"""
        self.project_repository.update_progress(
            project_id,
            get_sections=self.get_sections,
        )
