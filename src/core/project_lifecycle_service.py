import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

from slugify import slugify

from ..html2md import convert_html_to_markdown_text
from .glossary import Glossary, GlossaryManager
from .markdown_project_parser import MarkdownProjectParser
from .models import ParagraphStatus, ProjectConfig, ProjectMeta, ProjectStatus, Section


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

    def create_project(
        self,
        *,
        name: str,
        html_path: str,
        config: Optional[ProjectConfig] = None,
    ) -> ProjectMeta:
        project_id = slugify(name, max_length=50)
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise ValueError(f"Project '{project_id}' already exists")

        project_dir.mkdir(parents=True)
        (project_dir / "sections").mkdir()

        source_path = Path(html_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {html_path}")

        source_suffix = source_path.suffix.lower()
        is_html_source = source_suffix in {".html", ".htm"}
        is_markdown_source = source_suffix in {".md", ".markdown"}
        if not (is_html_source or is_markdown_source):
            raise ValueError("Only .html/.htm/.md/.markdown files are supported")

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

        self._glossary_manager.save_project(project_id, Glossary())
        return meta

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
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

    @staticmethod
    def _auto_approve_structured_metadata(sections: list[Section]) -> None:
        structured_metadata_types = {"source", "subtitle", "byline", "date_access"}
        for section in sections:
            for paragraph in section.paragraphs:
                if not paragraph.is_metadata:
                    continue
                if paragraph.metadata_type in structured_metadata_types:
                    continue
                paragraph.status = ParagraphStatus.APPROVED
                paragraph.confirmed = paragraph.source
