import logging
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Callable, Optional
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from slugify import slugify

from ..html2md import convert_html_to_markdown_text
from .glossary import Glossary, GlossaryManager
from .image_assets import BROWSER_IMAGE_EXTENSIONS, parse_markdown_image_reference
from .markdown_project_parser import MarkdownProjectParser
from .models import (
    ElementType,
    ParagraphStatus,
    ProjectConfig,
    ProjectMeta,
    ProjectStatus,
    Section,
)
from .structured_metadata import STRUCTURED_METADATA_TYPES


class ProjectLifecycleService:
    """Own project creation, deletion, and asset-folder copy concerns."""

    def __init__(
        self,
        *,
        project_dir_resolver: Callable[[str], Path],
        write_text: Callable[[Path, str], None],
        save_section: Callable[[str, Section], None],
        save_meta: Callable[[str, ProjectMeta], None],
        glossary_manager: GlossaryManager,
        logger_: logging.Logger | None = None,
    ) -> None:
        self._project_dir = project_dir_resolver
        self._write_text = write_text
        self._save_section = save_section
        self._save_meta = save_meta
        self._glossary_manager = glossary_manager
        self._logger = logger_ or logging.getLogger(__name__)

    def _ensure_allowed_source_path(self, html_path: str, *, projects_root: Path) -> None:
        """限制源文件只能取自 inbox 目录与系统临时目录(上传流程把文件落在后者)。"""
        try:
            resolved = Path(html_path).resolve()
        except OSError as error:
            raise ValueError(f"Invalid source path: {html_path}") from error

        allowed_roots = [
            projects_root.parent / "inbox",
            Path(tempfile.gettempdir()),
        ]
        for root in allowed_roots:
            try:
                if resolved.is_relative_to(root.resolve()):
                    return
            except OSError:
                continue

        raise ValueError(
            "html_path must be inside the inbox directory or the upload temp directory"
        )

    def create_project(
        self,
        *,
        name: str,
        html_path: str,
        config: Optional[ProjectConfig] = None,
    ) -> ProjectMeta:
        project_id = slugify(name, max_length=50)
        if not project_id:
            # slugify 对纯符号/非 ASCII 标题会返回空串，回退到唯一 ID 避免路径冲突与空目录名。
            project_id = f"project-{uuid4().hex[:8]}"
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise ValueError(f"Project '{project_id}' already exists")

        # html_path 由客户端直接指定,不限制允许根即构成任意本地文件读取
        # (读出的内容会写进 projects/ 并被静态挂载取回,审计 BE4)。
        self._ensure_allowed_source_path(html_path, projects_root=project_dir.parent)

        source_path = Path(html_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {html_path}")
        if not source_path.is_file():
            raise ValueError(f"Source path is not a file: {html_path}")

        source_suffix = source_path.suffix.lower()
        is_html_source = source_suffix in {".html", ".htm"}
        is_markdown_source = source_suffix in {".md", ".markdown"}
        if not (is_html_source or is_markdown_source):
            raise ValueError("Only .html/.htm/.md/.markdown files are supported")

        # 先完成不会写项目状态的校验，再创建目录。创建之后的步骤按事务处理：
        # 解析、章节落盘或术语表初始化任一步失败，都只清理由本次调用刚创建的
        # 精确目录，避免留下没有 meta.json、却会永久阻止同名重试的“幽灵项目”。
        try:
            project_dir.mkdir(parents=True)
        except FileExistsError as error:
            raise ValueError(f"Project '{project_id}' already exists") from error

        try:
            (project_dir / "sections").mkdir()

            parser = MarkdownProjectParser(
                max_paragraph_length=(config.max_paragraph_length if config else 800),
                merge_short_paragraphs=(config.merge_short_paragraphs if config else True),
            )
            source_file = "source.md"
            metadata = None

            if is_html_source:
                shutil.copy(source_path, project_dir / "source.html")
                source_file = "source.html"
                source_md, metadata = convert_html_to_markdown_text(
                    html_path=html_path,
                    output_dir=project_dir,
                    copy_images=False,
                )
            else:
                source_md = source_path.read_text(encoding="utf-8-sig")

            parsed_project = parser.parse(source_md, metadata=metadata)
            sections = parsed_project.sections
            self._auto_approve_structured_metadata(sections)

            self._write_text(project_dir / "source.md", source_md)
            for section in sections:
                self._save_section(project_id, section)

            meta = ProjectMeta(
                id=project_id,
                title=parsed_project.title,
                source_file=source_file,
                status=ProjectStatus.CREATED,
                config=config or ProjectConfig(),
                metadata=metadata,
            )
            meta.update_progress(sections)
            self._save_meta(project_id, meta)

            if is_html_source:
                self.copy_assets_directory(source_path, project_dir)
            self.copy_referenced_assets(
                source_root=source_path.parent,
                project_dir=project_dir,
                sections=sections,
            )

            self._glossary_manager.save_project(project_id, Glossary())
            return meta
        except Exception:
            try:
                shutil.rmtree(project_dir)
            except OSError as cleanup_error:
                self._logger.error(
                    "Failed to clean incomplete project directory %s: %s",
                    project_dir,
                    cleanup_error,
                )
            raise

    def delete_project(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        shutil.rmtree(project_dir)

    def copy_assets_directory(self, html_source: Path, project_dir: Path) -> None:
        assets_dir = self.find_assets_directory(html_source)
        if not assets_dir:
            return

        dest_dir = project_dir / assets_dir.name
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(assets_dir, dest_dir)
        except Exception as error:
            self._logger.warning("Failed to copy assets directory: %s", error)

    def find_assets_directory(self, html_source: Path) -> Optional[Path]:
        stem = html_source.stem
        candidates = [
            html_source.parent / f"{stem}_files",
            html_source.parent / f"{stem}.files",
            html_source.parent / f"{stem}_images",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

    def copy_referenced_assets(
        self,
        *,
        source_root: Path,
        project_dir: Path,
        sections: list[Section],
    ) -> int:
        """Copy referenced local images before an upload staging dir disappears."""
        source_root = source_root.resolve()
        project_dir = project_dir.resolve()
        copied = 0
        seen: set[PurePosixPath] = set()

        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.element_type != ElementType.IMAGE:
                    continue

                value = paragraph.source.strip()
                markdown_reference = parse_markdown_image_reference(value)
                if markdown_reference is not None:
                    value = markdown_reference.source
                if not value or value.startswith(("//", "data:", "blob:")):
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc:
                    continue

                normalized = unquote(parsed.path).replace("\\", "/")
                if normalized.startswith("./"):
                    normalized = normalized[2:]
                relative = PurePosixPath(normalized)
                if (
                    not normalized
                    or relative.is_absolute()
                    or relative in seen
                    or relative.suffix.lower() not in BROWSER_IMAGE_EXTENSIONS
                    or any(part in {"", ".", ".."} for part in relative.parts)
                    or relative.parts[0] in {"artifacts", "sections"}
                ):
                    continue
                seen.add(relative)

                source_candidate = source_root.joinpath(*relative.parts)
                if source_candidate.is_symlink():
                    continue
                resolved_source = source_candidate.resolve()
                if (
                    source_root not in resolved_source.parents
                    or not resolved_source.is_file()
                ):
                    continue

                destination = project_dir.joinpath(*relative.parts)
                resolved_destination = destination.resolve()
                if project_dir not in resolved_destination.parents:
                    continue
                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(resolved_source, destination)
                    copied += 1
                except OSError as error:
                    self._logger.warning(
                        "Failed to copy referenced image %s: %s",
                        relative,
                        error,
                    )

        return copied

    @staticmethod
    def _auto_approve_structured_metadata(sections: list[Section]) -> None:
        for section in sections:
            for paragraph in section.paragraphs:
                if not paragraph.is_metadata:
                    continue
                if paragraph.metadata_type in STRUCTURED_METADATA_TYPES:
                    continue
                paragraph.status = ParagraphStatus.APPROVED
                paragraph.confirmed = paragraph.source
