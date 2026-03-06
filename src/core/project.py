"""
Translation Agent - Project Manager

Manage translation projects: create, read, update, delete.
"""

import json
import os
import shutil
import threading
from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from uuid import uuid4

from slugify import slugify

from .models import (
    ProjectMeta, ProjectStatus, ProjectProgress, ProjectConfig,
    Section, Paragraph, ParagraphStatus, ElementType
)
from .parser import HTMLParser
from .glossary import GlossaryManager, create_default_semiconductor_glossary


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
        self.parser = HTMLParser()
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
            # Evict oldest entries when exceeding the cap
            while len(self._section_locks) > self._section_locks_max:
                self._section_locks.popitem(last=False)
            return new_lock

    def _best_translation_text(self, paragraph: Paragraph, fallback_to_source: bool = True) -> str:
        """Get best available translation text for a paragraph."""
        if paragraph.confirmed:
            return paragraph.confirmed
        if paragraph.translations:
            return list(paragraph.translations.values())[0].text
        return paragraph.source if fallback_to_source else ""

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

        # 复制 HTML 文件
        html_source = Path(html_path)
        if not html_source.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        shutil.copy(html_source, project_dir / "source.html")

        # 解析 HTML
        parser = HTMLParser(
            max_paragraph_length=(config.max_paragraph_length if config else 800),
            merge_short_paragraphs=(config.merge_short_paragraphs if config else True),
            download_images=True,
            images_dir=str(project_dir / "images"),
        )
        title, sections, metadata = parser.parse_file(html_path)

        # 保存完整原文 Markdown
        source_md = parser.to_markdown(
            sections,
            include_translation=False,
            title=title,
            metadata=metadata,
        )
        self._write_text(project_dir / "source.md", source_md)

        # 保存各章节
        for section in sections:
            self._save_section(project_id, section)

        # 创建项目元信息
        meta = ProjectMeta(
            id=project_id,
            title=title,
            source_file="source.html",
            status=ProjectStatus.CREATED,
            config=config or ProjectConfig(),
            metadata=metadata,
        )
        meta.update_progress(sections)

        # 保存元信息
        self._save_meta(project_id, meta)

        # Copy related assets directory (e.g., *_files from saved HTML)
        self._copy_assets_directory(html_source, project_dir)

        # 初始化项目术语表（合并全局术语表）
        global_glossary = create_default_semiconductor_glossary()
        self.glossary_manager.save_project(project_id, global_glossary)

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
            print(f"[Project] Warning: Failed to copy assets directory: {e}")

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
            print(f"Warning: Project {project_id} meta.json is corrupted: {e}")
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
                print(f"Warning: Failed to recalculate progress for {project_id}: {e}")

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

        # Don't downgrade an already-approved paragraph back to TRANSLATED
        # (e.g. when a retranslation API returns TRANSLATED as the default status).
        if paragraph.status == ParagraphStatus.APPROVED and status == ParagraphStatus.TRANSLATED:
            status = None

        # 更新译文
        if translation is not None:
            paragraph.add_translation(translation, model)
            if status == ParagraphStatus.APPROVED:
                paragraph.confirm(translation, model)

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

    def export(self, project_id: str, include_source: bool = False, format: str = 'markdown') -> str:
        """
        导出项目

        Args:
            project_id: 项目 ID
            include_source: 是否包含原文
            format: 输出格式 ('markdown' 或 'html')

        Returns:
            str: 导出内容
        """
        if format == 'html':
            return self.export_html(project_id)
        return self.export_markdown(project_id, include_source)

    def export_markdown(self, project_id: str, include_source: bool = False) -> str:
        """
        导出项目为 Markdown

        Args:
            project_id: 项目 ID
            include_source: 是否包含原文

        Returns:
            str: Markdown 内容
        """
        meta = self.get(project_id)
        sections = self.get_sections(project_id)

        lines = [f"# {meta.title}", ""]

        for section in sections:
            # 章节标题
            title = section.title_translation or section.title
            lines.append(f"## {title}")
            lines.append("")

            for p in section.paragraphs:
                # 图片使用原始 HTML
                if p.element_type == ElementType.IMAGE:
                    if p.source_html:
                        lines.append(p.source_html)
                    lines.append("")
                    continue

                # 使用确认的译文，如果没有则使用原文
                text = self._best_translation_text(p, fallback_to_source=True)

                if include_source and p.confirmed:
                    lines.append(f"<!-- {p.source} -->")

                # 根据元素类型格式化
                if p.element_type == ElementType.CODE:
                    lines.append(f"```\n{text}\n```")
                elif p.element_type == ElementType.TABLE:
                    # 表格使用原始 HTML（Markdown 表格支持有限）
                    if p.source_html:
                        lines.append(p.source_html)
                    else:
                        lines.append(text)
                else:
                    lines.append(self._format_markdown_line(p.element_type, text))

                lines.append("")

        content = "\n".join(lines)

        # 保存到文件
        output_path = self._project_dir(project_id) / "output.md"
        self._write_text(output_path, content)

        return content

    def export_html(self, project_id: str) -> str:
        """
        导出项目为 HTML（保持原始格式）

        Args:
            project_id: 项目 ID

        Returns:
            str: HTML 内容
        """
        meta = self.get(project_id)
        sections = self.get_sections(project_id)

        # 读取原始 HTML 作为模板
        source_html_path = self._project_dir(project_id) / "source.html"
        if source_html_path.exists():
            with open(source_html_path, "r", encoding="utf-8") as f:
                original_html = f.read()

            # 尝试从原始 HTML 中提取 body 内容
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(original_html, 'lxml')

            # 构建新的 HTML
            html_parts = []

            # 保留 head
            head = soup.find('head')
            if head:
                html_parts.append(str(head))
            else:
                html_parts.append('<head><meta charset="utf-8"><title>' + meta.title + '</title></head>')

            html_parts.append('<body>')

            # 添加标题
            html_parts.append(f'<h1>{meta.title}</h1>')

            # 遍历章节和段落
            for section in sections:
                # 章节标题
                title = section.title_translation or section.title
                html_parts.append(f'<h2>{title}</h2>')

                for p in section.paragraphs:
                    # 图片使用原始 HTML
                    if p.element_type == ElementType.IMAGE and p.source_html:
                        html_parts.append(p.source_html)
                        continue

                    # 表格使用原始 HTML
                    if p.element_type == ElementType.TABLE and p.source_html:
                        html_parts.append(p.source_html)
                        continue

                    # 获取要显示的文本
                    text = self._best_translation_text(p, fallback_to_source=True)

                    # 根据元素类型生成 HTML
                    if p.element_type == ElementType.H3:
                        html_parts.append(f'<h3>{text}</h3>')
                    elif p.element_type == ElementType.H4:
                        html_parts.append(f'<h4>{text}</h4>')
                    elif p.element_type == ElementType.LI:
                        html_parts.append(f'<li>{text}</li>')
                    elif p.element_type == ElementType.BLOCKQUOTE:
                        html_parts.append(f'<blockquote>{text}</blockquote>')
                    elif p.element_type == ElementType.CODE:
                        html_parts.append(f'<pre><code>{text}</code></pre>')
                    else:
                        # 普通段落
                        html_parts.append(f'<p>{text}</p>')

            html_parts.append('</body>')

            content = '<!DOCTYPE html>\n<html>' + '\n'.join(html_parts) + '</html>'
        else:
            # 如果没有原始 HTML，回退到 Markdown
            content = self.export_markdown(project_id, include_source=False)

        # 保存到文件
        output_path = self._project_dir(project_id) / "output.html"
        self._write_text(output_path, content)

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
                if p.confirmed:
                    text = p.confirmed
                    status_mark = "✅"
                elif p.translations:
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
        for p in section.paragraphs:
            source_lines.append(self._format_markdown_line(p.element_type, p.source))
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
                    paragraphs.append(Paragraph(**p))
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
            print(f"Warning: Failed to load section {section_id}: {e}")
            return None

    def _update_progress(self, project_id: str) -> None:
        """更新项目进度"""
        meta = self.get(project_id)
        sections = self.get_sections(project_id)
        meta.update_progress(sections)
        self._save_meta(project_id, meta)
