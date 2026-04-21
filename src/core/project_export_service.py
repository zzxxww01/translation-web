import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .inline_recovery_service import InlineRecoveryService
from .markdown_postprocess import postprocess_markdown
from .models import ElementType, ProjectMeta, Section
from .title_guard import find_missing_title_terms


class ProjectExportService:
    """Own export filenames, export linting, markdown export, and preview rendering."""

    _VALID_EXPORT_FORMATS = {"en", "zh"}

    def __init__(
        self,
        *,
        inline_recovery: InlineRecoveryService,
        project_dir_resolver: Callable[[str], Path],
        write_text: Callable[[Path, str], None],
        write_json: Callable[[Path, Any], None],
        get_project: Callable[[str], ProjectMeta],
        get_sections: Callable[[str], list[Section]],
        best_translation_text: Callable[..., str],
    ) -> None:
        self._inline_recovery = inline_recovery
        self._project_dir = project_dir_resolver
        self._write_text = write_text
        self._write_json = write_json
        self._get_project = get_project
        self._get_sections = get_sections
        self._best_translation_text = best_translation_text

    def preferred_export_title(self, meta: ProjectMeta) -> str:
        preferred_title = (meta.title_translation or meta.title or "").strip()
        return preferred_title or meta.id

    def sanitize_export_filename_component(self, value: str, fallback: str) -> str:
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value)
        sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(".")
        return sanitized or fallback

    def normalize_export_format(self, format: str = "zh") -> str:
        normalized = (format or "zh").strip().lower()
        if normalized not in self._VALID_EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format: {format!r}. Use 'en' or 'zh'.")
        return normalized

    def build_export_filename(self, meta: ProjectMeta, format: str = "zh") -> str:
        normalized = self.normalize_export_format(format)
        title = self.sanitize_export_filename_component(self.preferred_export_title(meta), meta.id)
        suffix = "_en.md" if normalized == "en" else "_zh.md"
        return f"{title}{suffix}"

    def get_export_filename(self, project_id: str, format: str = "zh") -> str:
        meta = self._get_project(project_id)
        return self.build_export_filename(meta, format=format)

    def get_export_path(self, project_id: str, format: str = "zh") -> Path:
        return self._project_dir(project_id) / self.get_export_filename(project_id, format=format)

    def section_display_title(self, section: Section) -> str:
        return (section.title_translation or section.title or "").strip()

    def is_front_matter_section(self, section: Section) -> bool:
        paragraphs = section.paragraphs
        if not paragraphs or len(paragraphs) > 4:
            return False
        first = paragraphs[0]
        if not first.is_heading or first.heading_level not in {3, 4}:
            return False
        return all(
            paragraph.element_type
            in {ElementType.H3, ElementType.H4, ElementType.P, ElementType.IMAGE}
            for paragraph in paragraphs
        )

    def should_render_section_heading(
        self, sections: list[Section], index: int, section: Section
    ) -> bool:
        if index != 0 or index + 1 >= len(sections):
            return True

        current_title = self.section_display_title(section)
        next_title = self.section_display_title(sections[index + 1])
        if not current_title or current_title != next_title:
            return True
        return not self.is_front_matter_section(section)

    def looks_like_untranslated_residue(self, text: str) -> bool:
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
            if len(words) >= 6 or len(lowercase_words) >= 3:
                return True
            if ":" in span or "’" in span or "'" in span:
                return True
        return False

    def build_export_lint_payload(
        self,
        meta: ProjectMeta,
        sections: list[Section],
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        missing_title_terms = find_missing_title_terms(
            meta.title,
            self.preferred_export_title(meta),
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
            and self.is_front_matter_section(sections[0])
            and self.should_render_section_heading(sections, 0, sections[0])
            and self.should_render_section_heading(sections, 1, sections[1])
            and self.section_display_title(sections[0])
            and self.section_display_title(sections[0]) == self.section_display_title(sections[1])
        ):
            issues.append(
                {
                    "type": "duplicate_intro_heading",
                    "severity": "error",
                    "message": "front matter 标题与正文首章标题重复，导出时可能出现重复 H2。",
                    "heading": self.section_display_title(sections[0]),
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

                if self.looks_like_untranslated_residue(translated):
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

    def write_export_lint_artifact(self, project_id: str, payload: dict[str, Any]) -> None:
        artifact_path = self._project_dir(project_id) / "artifacts" / "export-lint" / "latest.json"
        self._write_json(artifact_path, payload)

    def export(self, project_id: str, include_source: bool = False, format: str = "zh") -> str:
        normalized = self.normalize_export_format(format)
        if normalized == "en":
            return self.export_source_markdown(project_id)
        return self.export_markdown(project_id, include_source)

    def export_source_markdown(self, project_id: str) -> str:
        project_dir = self._project_dir(project_id)
        for name in ("source_en.md", "source.md"):
            path = project_dir / name
            if path.exists():
                content = path.read_text(encoding="utf-8")
                break
        else:
            raise FileNotFoundError(f"Source markdown not found for project {project_id}")

        meta = self._get_project(project_id)
        output_path = project_dir / self.build_export_filename(meta, format="en")
        self._write_text(output_path, content)
        return content

    def export_markdown(self, project_id: str, include_source: bool = False) -> str:
        meta = self._get_project(project_id)
        sections = self._get_sections(project_id)
        lines = [f"# {self.preferred_export_title(meta)}", ""]

        for index, section in enumerate(sections):
            if self.should_render_section_heading(sections, index, section):
                lines.append(f"## {self.section_display_title(section)}")
                lines.append("")

            for block in self._inline_recovery.group_section_blocks(section):
                if include_source and any(paragraph.confirmed for paragraph in block):
                    source_comment = block[0].parent_block_plain_text or " ".join(
                        paragraph.source for paragraph in block
                    )
                    lines.append(f"<!-- {source_comment} -->")
                lines.append(self._inline_recovery.render_block_markdown(block, fallback_to_source=True))
                lines.append("")

        content = postprocess_markdown("\n".join(lines))
        output_path = self._project_dir(project_id) / self.build_export_filename(meta, format="zh")
        self._write_text(output_path, content)
        self.write_export_lint_artifact(project_id, self.build_export_lint_payload(meta, sections))
        return content

    def generate_preview(self, project_id: str) -> str:
        meta = self._get_project(project_id)
        sections = self._get_sections(project_id)
        lines = [f"# {meta.title}", ""]

        for section in sections:
            lines.append(f"## {section.title_translation or section.title}")
            lines.append("")
            for paragraph in section.paragraphs:
                if paragraph.has_confirmed_translation():
                    text = paragraph.confirmed
                    status_mark = "✅"
                elif paragraph.has_draft_translation():
                    text = self._best_translation_text(paragraph, fallback_to_source=False)
                    status_mark = "🔄"
                else:
                    text = paragraph.source
                    status_mark = "⏳"

                if paragraph.element_type == ElementType.H3:
                    lines.append(f"### {status_mark} {text}")
                elif paragraph.element_type == ElementType.H4:
                    lines.append(f"#### {status_mark} {text}")
                else:
                    lines.append(f"{status_mark} {text}")
                lines.append("")

        content = postprocess_markdown("\n".join(lines))
        self._write_text(self._project_dir(project_id) / "preview.md", content)
        return content
