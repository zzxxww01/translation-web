import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .format_tokens import assign_span_ids
from .models import Paragraph, ProjectMeta, Section


class ProjectRepository:
    """Own project metadata/section persistence and progress recomputation."""

    def __init__(
        self,
        *,
        project_dir_resolver: Callable[[str], Path],
        read_json: Callable[[Path], Any],
        write_json: Callable[[Path, Any], None],
        write_text: Callable[[Path, str], None],
        get_project: Callable[[str], ProjectMeta],
        render_source_block_markdown: Callable[[list[Paragraph]], str],
        render_markdown_line: Callable[[Any, str], str],
        best_translation_text: Callable[..., str],
        logger_: logging.Logger | None = None,
    ) -> None:
        self._project_dir = project_dir_resolver
        self._read_json = read_json
        self._write_json = write_json
        self._write_text = write_text
        self._get_project = get_project
        self._render_source_block_markdown = render_source_block_markdown
        self._render_markdown_line = render_markdown_line
        self._best_translation_text = best_translation_text
        self._logger = logger_ or logging.getLogger(__name__)

    def save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        self._write_json(self._project_dir(project_id) / "meta.json", meta.model_dump(mode="json"))

    def save_section(
        self,
        project_id: str,
        section: Section,
        *,
        grouped_blocks: list[list[Paragraph]],
    ) -> None:
        section_dir = self._project_dir(project_id) / "sections" / section.section_id
        section_dir.mkdir(parents=True, exist_ok=True)

        source_lines: list[str] = []
        for block in grouped_blocks:
            source_lines.append(self._render_source_block_markdown(block))
            source_lines.append("")
        self._write_text(section_dir / "source.md", "\n".join(source_lines))

        trans_lines: list[str] = []
        for paragraph in section.paragraphs:
            text = self._best_translation_text(paragraph, fallback_to_source=False)
            trans_lines.append(self._render_markdown_line(paragraph.element_type, text))
            trans_lines.append("")
        self._write_text(section_dir / "translation.md", "\n".join(trans_lines))

        payload = {
            "section_id": section.section_id,
            "title": section.title,
            "title_translation": section.title_translation,
            "paragraphs": [paragraph.model_dump(mode="json") for paragraph in section.paragraphs],
        }
        self._write_json(section_dir / "meta.json", payload)

    def load_section(self, project_id: str, section_id: str) -> Optional[Section]:
        section_dir = self._project_dir(project_id) / "sections" / section_id
        meta_path = section_dir / "meta.json"
        if not meta_path.exists():
            return None

        try:
            data = self._read_json(meta_path)
            paragraphs: list[Paragraph] = []
            for paragraph_data in data.get("paragraphs", []):
                try:
                    paragraph = Paragraph(**paragraph_data)
                    if paragraph.inline_elements and not paragraph.expected_tokens:
                        paragraph.expected_tokens = [
                            element.span_id
                            for element in assign_span_ids(paragraph.inline_elements)
                            if element.span_id
                        ]
                    if paragraph.inline_elements and not paragraph.parent_inline_elements:
                        paragraph.parent_inline_elements = assign_span_ids(paragraph.inline_elements)
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
                    continue

            if not data.get("section_id") or not data.get("title"):
                return None

            return Section(
                section_id=data["section_id"],
                title=data["title"],
                title_translation=data.get("title_translation"),
                paragraphs=paragraphs,
            )
        except (json.JSONDecodeError, KeyError, TypeError, IOError) as error:
            self._logger.warning("Failed to load section %s: %s", section_id, error)
            return None

    def get_sections(self, project_id: str) -> list[Section]:
        sections_dir = self._project_dir(project_id) / "sections"
        if not sections_dir.exists():
            return []
        sections: list[Section] = []
        for section_dir in sorted(sections_dir.iterdir()):
            if section_dir.is_dir():
                section = self.load_section(project_id, section_dir.name)
                if section:
                    sections.append(section)
        return sections

    def update_progress(
        self,
        project_id: str,
        *,
        get_sections: Callable[[str], list[Section]],
    ) -> None:
        meta = self._get_project(project_id)
        sections = get_sections(project_id)
        meta.update_progress(sections)
        self.save_meta(project_id, meta)
