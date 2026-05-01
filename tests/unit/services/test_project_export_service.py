from pathlib import Path

from src.core.markdown_postprocess import postprocess_markdown
from src.core.inline_recovery_service import InlineRecoveryService
from src.core.models import ElementType, Paragraph, ProjectMeta, ProjectStatus, Section
from src.core.project_export_service import ProjectExportService


def _build_service(tmp_path: Path, sections: list[Section], meta: ProjectMeta) -> ProjectExportService:
    project_dir = tmp_path / meta.id
    project_dir.mkdir(parents=True, exist_ok=True)
    writes: dict[str, str] = {}

    def write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        writes[str(path)] = content

    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        writes[str(path)] = "json"

    return ProjectExportService(
        inline_recovery=InlineRecoveryService(),
        project_dir_resolver=lambda project_id: tmp_path / project_id,
        write_text=write_text,
        write_json=write_json,
        get_project=lambda _project_id: meta,
        get_sections=lambda _project_id: sections,
        best_translation_text=lambda paragraph, fallback_to_source=False: paragraph.best_translation_text(
            fallback_to_source=fallback_to_source
        ),
    )


def test_export_markdown_writes_expected_heading_and_artifact(tmp_path: Path) -> None:
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="OpenAI shipped a new model.",
        element_type=ElementType.P,
        confirmed="OpenAI 发布了一个新模型。",
    )
    section = Section(section_id="s1", title="Intro", title_translation="引言", paragraphs=[paragraph])
    meta = ProjectMeta(
        id="demo",
        title="Demo",
        title_translation="演示项目",
        source_file="source.md",
        status=ProjectStatus.CREATED,
    )
    service = _build_service(tmp_path, [section], meta)

    content = service.export_markdown("demo")

    assert "# 演示项目" in content
    assert "## 引言" in content
    assert "OpenAI 发布了一个新模型。" in content
    assert (tmp_path / "demo" / "演示项目_zh.md").exists()
    assert (tmp_path / "demo" / "artifacts" / "export-lint" / "latest.json").parent.exists()


def test_generate_preview_marks_confirmed_and_draft_paragraphs(tmp_path: Path) -> None:
    confirmed = Paragraph(
        id="p1",
        index=0,
        source="Confirmed text",
        confirmed="已确认译文",
        element_type=ElementType.P,
    )
    draft = Paragraph(
        id="p2",
        index=1,
        source="Draft text",
        element_type=ElementType.H3,
    )
    draft.add_translation("草稿译文", "test")
    section = Section(section_id="s1", title="Intro", paragraphs=[confirmed, draft])
    meta = ProjectMeta(
        id="preview-demo",
        title="Preview Demo",
        source_file="source.md",
    )
    service = _build_service(tmp_path, [section], meta)

    preview = service.generate_preview("preview-demo")

    assert "✅ 已确认译文" in preview
    assert "### 🔄 草稿译文" in preview
    assert (tmp_path / "preview-demo" / "preview.md").exists()


def test_postprocess_normalizes_latex_for_obsidian() -> None:
    content = (
        r"这是公式 \( TCO\_{\text{Goodput}} = \frac{TCO\_{\text{total}}}{Goodput} \)"
        "\n\n"
        "$$\n"
        r"\begin{align\*}"
        "\n"
        r"TCO\_{\text{total}} &= Cost\_{\text{hardware}}"
        "\n"
        r"\end{align\*}"
        "\n$$"
    )

    output = postprocess_markdown(content)

    assert r"$TCO_{\text{Goodput}} = \frac{TCO_{\text{total}}}{Goodput}$" in output
    assert r"\begin{align*}" in output
    assert r"TCO_{\text{total}} &= Cost_{\text{hardware}}" in output
    assert r"\end{align*}" in output
    assert r"\(" not in output
    assert r"\_" not in output
    assert r"align\*" not in output


def test_postprocess_converts_latex_display_brackets() -> None:
    output = postprocess_markdown(r"\[G\_{\text{total}} = \frac{1}{2}\]")

    assert output == "$$\n" + r"G_{\text{total}} = \frac{1}{2}" + "\n$$"


def test_postprocess_does_not_normalize_latex_inside_code_blocks() -> None:
    content = "```\n" + r"\( TCO\_{\text{Goodput}} \)" + "\n```"

    assert postprocess_markdown(content) == content
