from pathlib import Path

import pytest

from src.core.markdown_postprocess import postprocess_markdown
from src.core.inline_recovery_service import InlineRecoveryService
from src.core.models import ElementType, Paragraph, ProjectMeta, ProjectStatus, Section
from src.core.project_export_service import ExportBlockedError, ProjectExportService


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


def test_postprocess_normalizes_latex_for_obsidian_when_enabled() -> None:
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

    output = postprocess_markdown(content, latex_obsidian_normalize=True)

    assert r"$TCO_{\text{Goodput}} = \frac{TCO_{\text{total}}}{Goodput}$" in output
    assert r"\begin{align*}" in output
    assert r"TCO_{\text{total}} &= Cost_{\text{hardware}}" in output
    assert r"\end{align*}" in output
    assert r"\(" not in output
    assert r"\_" not in output
    assert r"align\*" not in output


def test_postprocess_keeps_latex_delimiters_by_default() -> None:
    # A-15：Obsidian 定界符改写默认关闭——\( \) 与 en.md 保真，
    # 但 \_ / \* 这类有害转义仍要修。
    content = r"这是公式 \( TCO\_{\text{Goodput}} \) 结束"

    output = postprocess_markdown(content)

    assert r"\( TCO_{\text{Goodput}} \)" in output
    assert r"\_" not in output
    assert "$" not in output


def test_postprocess_converts_latex_display_brackets_when_enabled() -> None:
    output = postprocess_markdown(
        r"\[G\_{\text{total}} = \frac{1}{2}\]", latex_obsidian_normalize=True
    )

    assert output == "$$\n" + r"G_{\text{total}} = \frac{1}{2}" + "\n$$"


def test_postprocess_keeps_display_brackets_by_default() -> None:
    output = postprocess_markdown(r"\[G\_{\text{total}} = \frac{1}{2}\]")

    assert output == r"\[G_{\text{total}} = \frac{1}{2}\]"


def test_postprocess_does_not_normalize_latex_inside_code_blocks() -> None:
    content = "```\n" + r"\( TCO\_{\text{Goodput}} \)" + "\n```"

    assert postprocess_markdown(content, latex_obsidian_normalize=True) == content
    assert postprocess_markdown(content) == content


# --- 2026-07 新增：A-1 / A-4 / A-5 / A-14 / P2 ---


def _demo_meta(**overrides) -> ProjectMeta:
    payload = dict(
        id="demo",
        title="Demo",
        title_translation="演示项目",
        source_file="source.md",
        status=ProjectStatus.CREATED,
    )
    payload.update(overrides)
    return ProjectMeta(**payload)


def test_synthetic_intro_section_heading_skipped(tmp_path: Path) -> None:
    # A-4：合成 "00-intro" 章节不渲染标题行，zh 标题数 == en 标题数。
    intro_paragraph = Paragraph(
        id="p0",
        index=0,
        source="Lead-in paragraph.",
        element_type=ElementType.P,
        confirmed="导语段落。",
    )
    body_paragraph = Paragraph(
        id="p1",
        index=0,
        source="Body paragraph.",
        element_type=ElementType.P,
        confirmed="正文段落。",
    )
    intro = Section(
        section_id="00-intro",
        title="Introduction",
        title_translation="引言",
        synthetic=True,
        paragraphs=[intro_paragraph],
    )
    body = Section(
        section_id="01-market",
        title="Market",
        title_translation="市场",
        paragraphs=[body_paragraph],
    )
    meta = _demo_meta()
    service = _build_service(tmp_path, [intro, body], meta)
    (tmp_path / "demo" / "source_en.md").write_text(
        "## Market\n\nLead-in paragraph.\n\nBody paragraph.\n", encoding="utf-8"
    )

    content = service.export_markdown("demo")

    assert "## 引言" not in content
    assert "## 市场" in content
    en_headings = 1
    zh_headings = sum(
        1 for line in content.splitlines() if line.startswith("## ")
    )
    assert zh_headings == en_headings


def test_export_blocked_on_critical_qa_issue(tmp_path: Path) -> None:
    # A-5：critical 级 QA 问题阻断导出，正常文件名不落盘，lint 工件保留。
    # 用占位符残留做样本——它是真正「必须拦」的工程缺陷；功率单位汉化已
    # 降为 warning（无确定性 fixer 的 critical 等于永久阻断导出）。
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="Capacity is 5 GW.",
        element_type=ElementType.P,
        confirmed="容量为 5 GW\x00PROTECTED_7\x00。",
    )
    section = Section(section_id="s1", title="Intro", title_translation="引言", paragraphs=[paragraph])
    meta = _demo_meta()
    service = _build_service(tmp_path, [section], meta)

    with pytest.raises(ExportBlockedError) as excinfo:
        service.export_markdown("demo")

    assert not (tmp_path / "demo" / "演示项目_zh.md").exists()
    assert (tmp_path / "demo" / "artifacts" / "export-lint" / "latest.json").parent.exists()
    # 阻断前先落盘：翻译成本已经花掉，用户必须拿得到可交付文本。
    blocked = tmp_path / "demo" / "演示项目_zh.blocked.md"
    assert blocked.exists()
    assert excinfo.value.blocked_path == blocked
    assert "演示项目_zh.blocked.md" in str(excinfo.value)


def test_power_unit_no_longer_blocks_export(tmp_path: Path) -> None:
    # 功率单位汉化降为 warning 后，正常译文必须能导出。
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="Capacity is 5 GW.",
        element_type=ElementType.P,
        confirmed="容量为 5 吉瓦。",
    )
    section = Section(section_id="s1", title="Intro", title_translation="引言", paragraphs=[paragraph])
    service = _build_service(tmp_path, [section], _demo_meta())

    content = service.export_markdown("demo")

    assert (tmp_path / "demo" / "演示项目_zh.md").exists()
    assert "吉瓦" in content


def test_export_repairs_redundant_link_shells_before_qa_gate(tmp_path: Path) -> None:
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="AMD announced ROCm.ai and published GEAK.",
        element_type=ElementType.P,
        confirmed=(
            "AMD 宣布了[[[ROCm.ai](https://www.amd.com/rocm)]](https://rocm.ai)，"
            "代码位于[[AMD-AGI 组织]](https://github.com/AMD-AGI)，"
            "核心是[[[GEAK](https://github.com/AMD-AGI/GEAK)]]。"
        ),
    )
    section = Section(
        section_id="s1",
        title="Intro",
        title_translation="引言",
        paragraphs=[paragraph],
    )
    service = _build_service(tmp_path, [section], _demo_meta())

    content = service.export_markdown("demo")

    assert "[ROCm.ai](https://www.amd.com/rocm)" in content
    assert "[AMD-AGI 组织](https://github.com/AMD-AGI)" in content
    assert "[GEAK](https://github.com/AMD-AGI/GEAK)" in content
    assert "[[[" not in content
    assert "]](" not in content
    assert (tmp_path / "demo" / "演示项目_zh.md").exists()


def test_export_lint_records_inline_recovery_fallbacks(tmp_path: Path) -> None:
    # P2：兜底段计数进导出报告。
    meta = _demo_meta()
    section = Section(section_id="s1", title="Intro", title_translation="引言", paragraphs=[])
    service = _build_service(tmp_path, [section], meta)

    payload = service.build_export_lint_payload(
        meta, [section], content="正文。", fallback_block_ids=["b1", "b2"]
    )

    fallback_issues = [
        issue for issue in payload["issues"]
        if issue["type"] == "inline_recovery_fallback"
    ]
    assert len(fallback_issues) == 1
    assert fallback_issues[0]["severity"] == "warning"
    assert fallback_issues[0]["block_ids"] == ["b1", "b2"]
    assert "2 段" in fallback_issues[0]["message"]


def test_export_filename_strips_fullwidth_punctuation(tmp_path: Path) -> None:
    # A-1：全角 ：？！、 不得进入导出文件名。
    meta = _demo_meta(title_translation="Token 预算：全新监控方案")
    service = _build_service(tmp_path, [], meta)

    filename = service.build_export_filename(meta, format="zh")

    assert "：" not in filename
    assert filename.endswith("_zh.md")


def test_double_title_regression_filenames(tmp_path: Path) -> None:
    # A-1 验收：三个实测标题走完标题守卫 + 文件名构建后，导出文件名为
    # 纯中文标题 + _zh.md，无双标题、无全角冒号残留。
    from src.core.title_guard import enforce_translated_title

    cases = [
        ("Anthropic 3Q26 Profit Over $1B: X", "Anthropic 2026 年第三季度利润超 10 亿美元：X 展望"),
        ("TokenBudgeting: X", "Token 预算：X 方案"),
        ("Cerebras — Faster Tokens Please", "Cerebras：更快的 token 供给"),
    ]
    for source_title, translated_title in cases:
        enforced = enforce_translated_title(source_title, translated_title)
        assert enforced == translated_title  # 不回插英文前缀

        meta = _demo_meta(title=source_title, title_translation=enforced)
        service = _build_service(tmp_path, [], meta)

        filename = service.build_export_filename(meta, format="zh")

        assert "：" not in filename
        assert filename.endswith("_zh.md")

    # 双标题指纹逐一确认不存在
    meta = _demo_meta(title="TokenBudgeting: X", title_translation="Token 预算：X 方案")
    service = _build_service(tmp_path, [], meta)
    assert "TokenBudgeting" not in service.build_export_filename(meta, format="zh")


def test_preferred_export_title_normalizes_cjk_ascii_spacing(tmp_path: Path) -> None:
    # A-14：标题译文过 CJK↔ASCII 空格归一后再进文件名/H1。
    meta = _demo_meta(title_translation="挑战DRAM巨头：迈向2028年")
    service = _build_service(tmp_path, [], meta)

    assert service.preferred_export_title(meta) == "挑战 DRAM 巨头：迈向 2028 年"
