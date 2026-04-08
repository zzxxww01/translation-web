"""
Translation Agent - Project Manager

Manage translation projects: create, read, update, delete.
"""

import json
import logging
import os
import re
import shutil
import threading
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

from slugify import slugify

logger = logging.getLogger(__name__)

from .models import (
    ProjectMeta, ProjectStatus, ProjectProgress, ProjectConfig,
    Section, Paragraph, ParagraphStatus, ElementType, Glossary
)
from .glossary import GlossaryManager
from .format_tokens import (
    FormatRecoveryError,
    assign_span_ids,
    group_paragraphs_by_parent_block,
    reconstruct_block_tokenized_text,
    require_valid_reconstruction,
    restore_markdown_from_tokenized,
    sorted_block_groups,
    tokenize_text,
)
from .markdown_project_parser import MarkdownProjectParser
from ..html2md import convert_html_to_markdown_text
from .title_guard import find_missing_title_terms


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
        self.markdown_parser = MarkdownProjectParser()
        self.glossary_manager = GlossaryManager(projects_path=projects_path)
        self._section_locks: OrderedDict[str, threading.RLock] = OrderedDict()
        self._section_locks_guard = threading.Lock()
        self._section_locks_max = 256

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_path / project_id

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)

    def _read_json(self, path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, path)

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
        if element_type == ElementType.H3:
            return f"### {text}"
        if element_type == ElementType.H4:
            return f"#### {text}"
        if element_type == ElementType.LI:
            return f"- {text}"
        if element_type == ElementType.BLOCKQUOTE:
            return f"> {text}"
        return text

    def _group_section_blocks(self, section: Section) -> list[list[Paragraph]]:
        return sorted_block_groups(section.paragraphs)

    def _section_display_title(self, section: Section) -> str:
        return (section.title_translation or section.title or "").strip()

    def _is_front_matter_section(self, section: Section) -> bool:
        paragraphs = section.paragraphs
        if not paragraphs or len(paragraphs) > 4:
            return False
        first = paragraphs[0]
        if not first.is_heading or first.heading_level not in {3, 4}:
            return False
        return all(
            p.element_type in {ElementType.H3, ElementType.H4, ElementType.P, ElementType.IMAGE}
            for p in paragraphs
        )

    def _should_render_section_heading(
        self, sections: list[Section], index: int, section: Section
    ) -> bool:
        if index != 0 or index + 1 >= len(sections):
            return True

        current_title = self._section_display_title(section)
        next_title = self._section_display_title(sections[index + 1])
        if not current_title or current_title != next_title:
            return True

        return not self._is_front_matter_section(section)

    def _render_source_block_markdown(self, paragraphs: list[Paragraph]) -> str:
        first = paragraphs[0]
        if first.parent_block_markdown:
            return first.parent_block_markdown
        if first.source_html and first.element_type in {ElementType.IMAGE, ElementType.TABLE}:
            return first.source_html
        if first.inline_elements:
            tokenized = tokenize_text(first.source, first.inline_elements)
            return restore_markdown_from_tokenized(tokenized, first.inline_elements)
        return self._format_markdown_line(first.element_type, first.source)

    def _render_block_markdown(
        self,
        paragraphs: list[Paragraph],
        fallback_to_source: bool = True,
    ) -> str:
        first = paragraphs[0]
        block_type = first.parent_block_type or first.element_type

        if block_type == ElementType.IMAGE:
            return first.parent_block_markdown or first.source_html or f"![image]({first.source})"
        if block_type == ElementType.TABLE:
            return first.parent_block_markdown or first.parent_source_html or first.source
        if block_type == ElementType.CODE:
            try:
                text = require_valid_reconstruction(
                    paragraphs,
                    fallback_to_source=fallback_to_source,
                ).text
            except FormatRecoveryError as error:
                logger.warning(
                    "Format recovery failed for code block %s, fallback to plain export: %s",
                    first.parent_block_id or first.id,
                    error,
                )
                text = reconstruct_block_tokenized_text(
                    paragraphs,
                    fallback_to_source=fallback_to_source,
                ).text
            return f"```\n{text}\n```"

        try:
            payload = require_valid_reconstruction(
                paragraphs, fallback_to_source=fallback_to_source
            )
            if first.parent_inline_elements:
                text = restore_markdown_from_tokenized(
                    payload.tokenized_text or payload.text,
                    first.parent_inline_elements,
                )
            else:
                text = payload.text
        except FormatRecoveryError as error:
            logger.warning(
                "Format recovery failed for block %s, fallback to plain export: %s",
                first.parent_block_id or first.id,
                error,
            )
            # Best-effort export: keep translated plain text and avoid aborting the full document export.
            text = reconstruct_block_tokenized_text(
                paragraphs,
                fallback_to_source=fallback_to_source,
            ).text
        return self._format_markdown_line(block_type, text)

    def _preferred_export_title(self, meta: ProjectMeta) -> str:
        """Use translated article title for exports when available."""
        preferred_title = (meta.title_translation or meta.title or "").strip()
        return preferred_title or meta.id

    def _sanitize_export_filename_component(self, value: str, fallback: str) -> str:
        """Keep the original title readable while removing invalid filename chars."""
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value)
        sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(".")
        return sanitized or fallback

    _VALID_EXPORT_FORMATS = {"en", "zh"}

    def _normalize_export_format(self, format: str = "zh") -> str:
        normalized = (format or "zh").strip().lower()
        if normalized not in self._VALID_EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format: {format!r}. Use 'en' or 'zh'.")
        return normalized

    def _build_export_filename(self, meta: ProjectMeta, format: str = "zh") -> str:
        normalized = self._normalize_export_format(format)
        title = self._sanitize_export_filename_component(
            self._preferred_export_title(meta),
            meta.id,
        )
        suffix = "_en.md" if normalized == "en" else "_zh.md"
        return f"{title}{suffix}"

    def get_export_filename(self, project_id: str, format: str = "zh") -> str:
        """Return the user-facing export filename for a project."""
        meta = self.get(project_id)
        return self._build_export_filename(meta, format=format)

    def get_export_path(self, project_id: str, format: str = "zh") -> Path:
        """Return the export file path for a project."""
        filename = self.get_export_filename(project_id, format=format)
        return self._project_dir(project_id) / filename

    def _looks_like_untranslated_residue(self, text: str) -> bool:
        normalized = (text or "").strip()
        if not normalized:
            return False
        if re.search(r"[\u4e00-\u9fff]", normalized) is None:
            return False
        if "来源：" in normalized and len(normalized) <= 80:
            return False

        english_spans = re.findall(
            r"[A-Za-z][A-Za-z0-9'’/+.-]*(?:\s+[A-Za-z][A-Za-z0-9'’/+.-]*){2,}",
            normalized,
        )
        if not english_spans:
            return False

        for span in english_spans:
            words = re.findall(r"[A-Za-z][A-Za-z0-9'’/+.-]*", span)
            if len(words) < 4:
                continue
            lowercase_words = [word for word in words if re.search(r"[a-z]", word)]
            if len(words) >= 6:
                return True
            if len(lowercase_words) >= 3:
                return True
            if ":" in span or "’" in span or "'" in span:
                return True
        return False

    def _build_export_lint_payload(
        self,
        meta: ProjectMeta,
        sections: list[Section],
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        missing_title_terms = find_missing_title_terms(
            meta.title,
            self._preferred_export_title(meta),
        )
        if missing_title_terms:
            issues.append(
                {
                    "type": "title_semantics",
                    "severity": "error",
                    "message": "导出标题缺少原题中的关键品牌/版本信息。",
                    "missing_terms": missing_title_terms,
                }
            )

        if (
            len(sections) > 1
            and self._is_front_matter_section(sections[0])
            and self._should_render_section_heading(sections, 0, sections[0])
            and self._should_render_section_heading(sections, 1, sections[1])
            and self._section_display_title(sections[0])
            and self._section_display_title(sections[0])
            == self._section_display_title(sections[1])
        ):
            issues.append(
                {
                    "type": "duplicate_intro_heading",
                    "severity": "error",
                    "message": "front matter 标题与正文首章标题重复，导出时可能出现重复 H2。",
                    "heading": self._section_display_title(sections[0]),
                }
            )

        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.is_metadata:
                    continue
                if paragraph.element_type in {ElementType.IMAGE, ElementType.TABLE, ElementType.CODE}:
                    continue

                translated = paragraph.best_translation_text(fallback_to_source=False).strip()
                if not translated:
                    issues.append(
                        {
                            "type": "missing_translation",
                            "severity": "error",
                            "section_id": section.section_id,
                            "paragraph_id": paragraph.id,
                            "message": "段落没有译文。",
                            "source_preview": paragraph.source[:160],
                        }
                    )
                    continue

                if translated == paragraph.source.strip():
                    issues.append(
                        {
                            "type": "untranslated_paragraph",
                            "severity": "error",
                            "section_id": section.section_id,
                            "paragraph_id": paragraph.id,
                            "message": "段落译文与原文完全相同。",
                            "source_preview": paragraph.source[:160],
                        }
                    )
                    continue

                if self._looks_like_untranslated_residue(translated):
                    issues.append(
                        {
                            "type": "residual_english",
                            "severity": "warning",
                            "section_id": section.section_id,
                            "paragraph_id": paragraph.id,
                            "message": "译文中存在较长英文残留片段，建议复核。",
                            "translation_preview": translated[:160],
                        }
                    )

        return {
            "project_id": meta.id,
            "generated_at": datetime.now().isoformat(),
            "issue_count": len(issues),
            "issues": issues,
        }

    def _write_export_lint_artifact(
        self,
        project_id: str,
        payload: dict[str, Any],
    ) -> None:
        artifact_path = (
            self._project_dir(project_id) / "artifacts" / "export-lint" / "latest.json"
        )
        self._write_json(artifact_path, payload)

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
        # 生成项目 ID
        project_id = slugify(name, max_length=50)
        project_dir = self._project_dir(project_id)

        # 检查是否已存在
        if project_dir.exists():
            raise ValueError(f"Project '{project_id}' already exists")

        # 创建项目目录
        project_dir.mkdir(parents=True)
        sections_dir = project_dir / "sections"
        sections_dir.mkdir()

        source_path = Path(html_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {html_path}")

        source_suffix = source_path.suffix.lower()
        is_html_source = source_suffix in {".html", ".htm"}
        is_markdown_source = source_suffix in {".md", ".markdown"}
        if not (is_html_source or is_markdown_source):
            raise ValueError("Only .html/.htm/.md/.markdown files are supported")

        markdown_parser = MarkdownProjectParser(
            max_paragraph_length=(config.max_paragraph_length if config else 800),
            merge_short_paragraphs=(config.merge_short_paragraphs if config else True),
        )
        source_file = "source.md"
        metadata = None

        if is_html_source:
            # HTML 链路：转 Markdown，保留原始远程图片 URL
            shutil.copy(source_path, project_dir / "source.html")
            source_file = "source.html"
            source_md, metadata = convert_html_to_markdown_text(
                html_path=html_path,
                output_dir=project_dir,
                copy_images=False,
            )
        else:
            # Markdown 输入：跳过 HTML 转换，直接进入解析流程
            source_md = source_path.read_text(encoding="utf-8-sig")

        parsed_project = markdown_parser.parse(source_md, metadata=metadata)
        title = parsed_project.title
        sections = parsed_project.sections

        # 自动批准 metadata 段落（图片等）；source metadata 走专用批翻链路
        structured_metadata_types = {"source", "subtitle", "byline", "date_access"}
        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.is_metadata:
                    if paragraph.metadata_type in structured_metadata_types:
                        continue
                    paragraph.status = ParagraphStatus.APPROVED
                    paragraph.confirmed = paragraph.source

        # 保存完整原文 Markdown
        self._write_text(project_dir / "source.md", source_md)

        # 保存各章节
        for section in sections:
            self._save_section(project_id, section)

        # 创建项目元信息
        meta = ProjectMeta(
            id=project_id,
            title=title,
            source_file=source_file,
            status=ProjectStatus.CREATED,
            config=config or ProjectConfig(),
            metadata=metadata,
        )
        meta.update_progress(sections)

        # 保存元信息
        self._save_meta(project_id, meta)

        # Copy related assets directory (e.g., *_files from saved HTML)
        if is_html_source:
            self._copy_assets_directory(source_path, project_dir)

        # 初始化项目术语表（合并全局术语表）
        self.glossary_manager.save_project(project_id, Glossary())

        return meta

    def _copy_assets_directory(self, html_source: Path, project_dir: Path) -> None:
        """Copy HTML asset folder (e.g., *_files) into project directory."""
        assets_dir = self._find_assets_directory(html_source)
        if not assets_dir:
            return

        dest_dir = project_dir / assets_dir.name
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(assets_dir, dest_dir)
        except Exception as e:
            # Non-fatal: assets copy failure should not block project creation
            logger.warning("Failed to copy assets directory: %s", e)

    def _find_assets_directory(self, html_source: Path) -> Optional[Path]:
        """Find related assets directory next to the HTML file."""
        stem = html_source.stem
        candidates = [
            html_source.parent / f"{stem}_files",
            html_source.parent / f"{stem}.files",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

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
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")

        shutil.rmtree(project_dir)

    def get_sections(self, project_id: str) -> List[Section]:
        """
        获取项目所有章节

        Args:
            project_id: 项目 ID

        Returns:
            List[Section]: 章节列表
        """
        sections_dir = self._project_dir(project_id) / "sections"
        if not sections_dir.exists():
            return []

        sections = []
        for section_dir in sorted(sections_dir.iterdir()):
            if section_dir.is_dir():
                section = self._load_section(project_id, section_dir.name)
                if section:
                    sections.append(section)

        return sections

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
        """
        导出项目

        Args:
            project_id: 项目 ID
            include_source: 是否包含原文
            format: 输出格式 ('en' 英文原文, 'zh' 中文译文)

        Returns:
            str: 导出内容
        """
        normalized = self._normalize_export_format(format)
        if normalized == "en":
            return self.export_source_markdown(project_id)
        return self.export_markdown(project_id, include_source)

    def export_source_markdown(self, project_id: str) -> str:
        """Export the original English source markdown with original remote image URLs."""
        project_dir = self._project_dir(project_id)

        # 新项目直接用 source.md（已保留远程 URL），兼容旧项目的 source_en.md
        for name in ("source_en.md", "source.md"):
            path = project_dir / name
            if path.exists():
                content = path.read_text(encoding="utf-8")
                break
        else:
            raise FileNotFoundError(f"Source markdown not found for project {project_id}")

        # 保存一份带英文后缀的导出文件
        meta = self.get(project_id)
        output_path = project_dir / self._build_export_filename(meta, format="en")
        self._write_text(output_path, content)

        return content

    def export_markdown(self, project_id: str, include_source: bool = False) -> str:
        """Export one project as markdown using parent-block reconstruction."""
        meta = self.get(project_id)
        sections = self.get_sections(project_id)

        article_title = self._preferred_export_title(meta)
        lines = [f"# {article_title}", ""]

        for index, section in enumerate(sections):
            if self._should_render_section_heading(sections, index, section):
                title = self._section_display_title(section)
                lines.append(f"## {title}")
                lines.append("")

            for block in self._group_section_blocks(section):
                if include_source and any(p.confirmed for p in block):
                    source_comment = block[0].parent_block_plain_text or " ".join(
                        p.source for p in block
                    )
                    lines.append(f"<!-- {source_comment} -->")
                lines.append(self._render_block_markdown(block, fallback_to_source=True))
                lines.append("")

        content = "\n".join(lines)

        # Markdown 安全后处理：转义 $ 等特殊字符，注入 CJK-Latin 空格
        from .markdown_postprocess import postprocess_markdown
        content = postprocess_markdown(content)

        # 保存到文件
        output_path = self._project_dir(project_id) / self._build_export_filename(
            meta,
            format="zh",
        )
        self._write_text(output_path, content)
        self._write_export_lint_artifact(
            project_id,
            self._build_export_lint_payload(meta, sections),
        )

        return content

    def generate_preview(self, project_id: str) -> str:
        """
        生成预览（包含未确认的译文）

        Args:
            project_id: 项目 ID

        Returns:
            str: Markdown 内容
        """
        meta = self.get(project_id)
        sections = self.get_sections(project_id)

        lines = [f"# {meta.title}", ""]

        for section in sections:
            title = section.title_translation or section.title
            lines.append(f"## {title}")
            lines.append("")

            for p in section.paragraphs:
                # 优先使用确认的译文，其次是任意翻译，最后是原文
                if p.has_confirmed_translation():
                    text = p.confirmed
                    status_mark = "✅"
                elif p.has_draft_translation():
                    text = self._best_translation_text(p, fallback_to_source=False)
                    status_mark = "🔄"
                else:
                    text = p.source
                    status_mark = "⏳"

                if p.element_type == ElementType.H3:
                    lines.append(f"### {status_mark} {text}")
                elif p.element_type == ElementType.H4:
                    lines.append(f"#### {status_mark} {text}")
                else:
                    lines.append(f"{status_mark} {text}")

                lines.append("")

        content = "\n".join(lines)

        # Markdown 安全后处理
        from .markdown_postprocess import postprocess_markdown
        content = postprocess_markdown(content)

        # 保存到文件
        preview_path = self._project_dir(project_id) / "preview.md"
        self._write_text(preview_path, content)

        return content

    def _save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息"""
        meta_path = self._project_dir(project_id) / "meta.json"
        self._write_json(meta_path, meta.model_dump(mode="json"))

    def _save_section(self, project_id: str, section: Section) -> None:
        """保存章节"""
        section_dir = self._project_dir(project_id) / "sections" / section.section_id
        section_dir.mkdir(parents=True, exist_ok=True)

        # 保存原文
        source_lines = []
        for block in self._group_section_blocks(section):
            source_lines.append(self._render_source_block_markdown(block))
            source_lines.append("")

        self._write_text(section_dir / "source.md", "\n".join(source_lines))

        # 保存译文
        trans_lines = []
        for p in section.paragraphs:
            text = self._best_translation_text(p, fallback_to_source=False)
            trans_lines.append(self._format_markdown_line(p.element_type, text))
            trans_lines.append("")

        self._write_text(section_dir / "translation.md", "\n".join(trans_lines))

        # 保存元数据
        meta_data = {
            "section_id": section.section_id,
            "title": section.title,
            "title_translation": section.title_translation,
            "paragraphs": [p.model_dump(mode='json') for p in section.paragraphs]
        }
        self._write_json(section_dir / "meta.json", meta_data)

    def _load_section(self, project_id: str, section_id: str) -> Optional[Section]:
        """加载章节"""
        section_dir = self._project_dir(project_id) / "sections" / section_id
        meta_path = section_dir / "meta.json"

        if not meta_path.exists():
            # 章节元数据文件不存在，返回 None
            return None

        try:
            data = self._read_json(meta_path)

            paragraphs = []
            for p in data.get("paragraphs", []):
                try:
                    paragraph = Paragraph(**p)
                    if paragraph.inline_elements and not paragraph.expected_tokens:
                        paragraph.expected_tokens = [
                            element.span_id
                            for element in assign_span_ids(paragraph.inline_elements)
                            if element.span_id
                        ]
                    if paragraph.inline_elements and not paragraph.parent_inline_elements:
                        paragraph.parent_inline_elements = assign_span_ids(
                            paragraph.inline_elements
                        )
                    if paragraph.parent_block_id is None:
                        paragraph.parent_block_id = paragraph.id
                    if paragraph.parent_block_index is None:
                        paragraph.parent_block_index = paragraph.index
                    if paragraph.parent_block_type is None:
                        paragraph.parent_block_type = paragraph.element_type
                    if paragraph.parent_block_plain_text is None:
                        paragraph.parent_block_plain_text = paragraph.source
                    if paragraph.parent_block_markdown is None:
                        paragraph.parent_block_markdown = self._render_source_block_markdown([paragraph])
                    if paragraph.segment_end is None:
                        paragraph.segment_end = paragraph.segment_start + len(paragraph.source)
                    paragraphs.append(paragraph)
                except (TypeError, ValueError):
                    # 跳过损坏的段落数据
                    continue

            if not data.get("section_id") or not data.get("title"):
                return None

            return Section(
                section_id=data["section_id"],
                title=data["title"],
                title_translation=data.get("title_translation"),
                paragraphs=paragraphs
            )
        except (json.JSONDecodeError, KeyError, TypeError, IOError) as e:
            # 元数据文件损坏，返回 None
            logger.warning("Failed to load section %s: %s", section_id, e)
            return None

    def _update_progress(self, project_id: str) -> None:
        """更新项目进度"""
        meta = self.get(project_id)
        sections = self.get_sections(project_id)
        meta.update_progress(sections)
        self._save_meta(project_id, meta)
