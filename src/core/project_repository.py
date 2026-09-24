import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .format_tokens import assign_span_ids
from .models import Paragraph, ProjectMeta, Section


class SectionDataError(ValueError):
    """An existing section is damaged; refusing partial loads protects user text."""


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
        from collections import OrderedDict
        from threading import RLock
        self._parsed_cache = OrderedDict()
        self._parsed_cache_lock = RLock()
        self._parsed_cache_bytes = 0

    def _resolve_section_dir(self, project_id: str, section_id: str) -> Optional[Path]:
        """兜底路径边界校验:section_id 含 ../ 或 ..\\ 时不得越出本项目的 sections 目录。

        路由层已有 validate_path_component,这里是不依赖调用方的第二道防线(审计 BE10)。
        get_sections 用真实目录名回调,不受影响。
        """
        # 与路由层保持跨平台一致：POSIX 会把 ``..\evil`` 当普通文件名，
        # 但同一值在 Windows 上是父目录跳转，必须在 resolve 前拒绝。
        if (
            not section_id
            or section_id in {".", ".."}
            or "/" in section_id
            or "\\" in section_id
        ):
            return None

        base = (self._project_dir(project_id) / "sections").resolve()
        resolved = (self._project_dir(project_id) / "sections" / section_id).resolve()
        # `resolved == base` 也要拒：""、"."、"a/.." 会解析回 sections 根，
        # 随后 save_section 就把 meta.json 写到根目录上，污染整个 sections。
        if resolved == base or not resolved.is_relative_to(base):
            return None
        # 返回归一化后的路径，避免把 "a/.." 这类未归一化路径传给下游 mkdir。
        return resolved

    def save_meta(self, project_id: str, meta: ProjectMeta) -> None:
        # 不把内存中的 sections 全量写进 meta.json:sections 持久化在
        # sections/<id>/meta.json,写进顶层 meta.json 会造成双数据源、陈旧快照与
        # 体积膨胀(审计 N10)。ProjectMeta.sections 有默认空值,读取时不受影响。
        self._write_json(
            self._project_dir(project_id) / "meta.json",
            meta.model_dump(mode="json", exclude={"sections"}),
        )

    def save_section(
        self,
        project_id: str,
        section: Section,
        *,
        grouped_blocks: list[list[Paragraph]],
    ) -> None:
        # Assignment to existing Pydantic objects is not automatically validated.
        # Check the complete candidate before touching any of the three files.
        section = Section.model_validate(section.model_dump(mode="json"))
        ids = [paragraph.id for paragraph in section.paragraphs]
        if any(not key.strip() for key in ids) or len(set(ids)) != len(ids):
            raise SectionDataError("Section paragraph identities are blank or duplicated")
        section_dir = self._resolve_section_dir(project_id, section.section_id)
        if section_dir is None:
            raise ValueError(f"Invalid section_id: {section.section_id}")
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

        # Persist all section-level provenance, including synthetic/title_source.
        self._write_json(section_dir / "meta.json", section.model_dump(mode="json"))

    def load_section(self, project_id: str, section_id: str) -> Optional[Section]:
        section_dir = self._resolve_section_dir(project_id, section_id)
        if section_dir is None:
            return None
        meta_path = section_dir / "meta.json"
        if not meta_path.exists():
            if section_dir.exists():
                raise SectionDataError(f"Section {section_id!r} has no metadata; restore it before editing/exporting")
            return None

        try:
            stat = meta_path.stat()
            stamp = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            cache_key = (project_id, section_id)
            with self._parsed_cache_lock:
                cached = self._parsed_cache.get(cache_key)
                if cached is not None and cached[0] == stamp:
                    self._parsed_cache.move_to_end(cache_key)
                    return cached[1].model_copy(deep=True)
            data = self._read_json(meta_path)
            if not isinstance(data, dict) or not isinstance(data.get("paragraphs"), list):
                raise ValueError("paragraphs must be an array")
            if data.get("section_id") != section_id:
                raise ValueError("stored section identity differs from its directory")
            section = Section.model_validate(data)
            ids = [p.id for p in section.paragraphs]
            if any(not key.strip() for key in ids) or len(set(ids)) != len(ids):
                raise ValueError("paragraph identities are blank or duplicated")
            # Enrich legacy fields only after validating the ENTIRE chapter.
            # A single invalid paragraph must never disappear on the next save.
            for paragraph in section.paragraphs:
                if paragraph.inline_elements and not paragraph.expected_tokens:
                    paragraph.expected_tokens = [
                        element.span_id for element in assign_span_ids(paragraph.inline_elements)
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
            after = meta_path.stat()
            after_stamp = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            if after_stamp == stamp and stat.st_size <= 8 * 1024 * 1024:
                with self._parsed_cache_lock:
                    previous = self._parsed_cache.pop(cache_key, None)
                    if previous is not None:
                        self._parsed_cache_bytes -= previous[2]
                    self._parsed_cache[cache_key] = (stamp, section.model_copy(deep=True), stat.st_size)
                    self._parsed_cache_bytes += stat.st_size
                    while len(self._parsed_cache) > 128 or self._parsed_cache_bytes > 32 * 1024 * 1024:
                        _, removed = self._parsed_cache.popitem(last=False)
                        self._parsed_cache_bytes -= removed[2]
            return section
        except (ValueError, KeyError, TypeError, OSError) as error:
            self._logger.warning("Failed to load complete section %s: %s", section_id, error)
            raise SectionDataError(f"Section {section_id!r} is invalid; no partial content was loaded") from error

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
