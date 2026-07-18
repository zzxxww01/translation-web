from src.core.models import (
    Paragraph,
    ParagraphConfirmation,
    ParagraphStatus,
    ProjectMeta,
    Section,
)
from src.core.project import ConcurrentParagraphUpdateError, ProjectManager


def _build_manager(tmp_path):
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[
            Paragraph(id="p1", index=0, source="First"),
            Paragraph(id="p2", index=1, source="Second"),
        ],
    )
    manager.save_section_only("demo", section)
    return manager


def test_merge_translation_preserves_unrelated_manual_edit(tmp_path):
    manager = _build_manager(tmp_path)
    section = manager.get_section("demo", "s1")
    expected = section.paragraphs[0].model_copy(deep=True)
    generated = section.paragraphs[0].model_copy(deep=True)
    generated.add_translation("第一段", "pro")

    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p2",
        translation="人工修改第二段",
        status=ParagraphStatus.MODIFIED,
        recompute_progress=False,
    )

    persisted, applied_ids, conflict_ids = (
        manager.merge_translation_updates_locked(
            "demo",
            "s1",
            [generated],
            {"p1": expected},
            recompute_progress=False,
        )
    )

    assert applied_ids == ["p1"]
    assert conflict_ids == []
    assert persisted.paragraphs[0].best_translation_text() == "第一段"
    assert persisted.paragraphs[1].best_translation_text() == "人工修改第二段"


def test_merge_translation_rejects_edit_to_target_paragraph(tmp_path):
    manager = _build_manager(tmp_path)
    section = manager.get_section("demo", "s1")
    expected = section.paragraphs[0].model_copy(deep=True)
    generated = section.paragraphs[0].model_copy(deep=True)
    generated.add_translation("过期 AI 译文", "pro")

    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p1",
        translation="人工新译文",
        status=ParagraphStatus.MODIFIED,
        recompute_progress=False,
    )

    persisted, applied_ids, conflict_ids = (
        manager.merge_translation_updates_locked(
            "demo",
            "s1",
            [generated],
            {"p1": expected},
            recompute_progress=False,
        )
    )

    assert applied_ids == []
    assert conflict_ids == ["p1"]
    assert persisted.paragraphs[0].best_translation_text() == "人工新译文"


def test_conditional_single_update_rejects_stale_generation(tmp_path):
    manager = _build_manager(tmp_path)
    section = manager.get_section("demo", "s1")
    expected = section.paragraphs[0].model_copy(deep=True)

    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p1",
        translation="人工新译文",
        status=ParagraphStatus.MODIFIED,
        recompute_progress=False,
    )

    try:
        manager.update_paragraph_locked(
            "demo",
            "s1",
            "p1",
            translation="过期 AI 译文",
            status=ParagraphStatus.TRANSLATED,
            model="pro",
            expected_paragraph=expected,
            recompute_progress=False,
        )
    except ConcurrentParagraphUpdateError as error:
        assert error.paragraph_id == "p1"
    else:
        raise AssertionError("stale translation should have raised a conflict")

    persisted = manager.get_section("demo", "s1")
    assert persisted.paragraphs[0].best_translation_text() == "人工新译文"


def test_conditional_update_returns_latest_section_with_one_locked_read(
    tmp_path,
    monkeypatch,
):
    manager = _build_manager(tmp_path)
    section = manager.get_section("demo", "s1")
    expected = section.paragraphs[0].model_copy(deep=True)
    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p2",
        translation="人工第二段",
        status=ParagraphStatus.MODIFIED,
        recompute_progress=False,
    )

    original_load = manager._load_section
    load_count = 0

    def counted_load(project_id, section_id):
        nonlocal load_count
        load_count += 1
        return original_load(project_id, section_id)

    monkeypatch.setattr(manager, "_load_section", counted_load)
    persisted_paragraph, persisted_section = manager.update_paragraph_locked(
        "demo",
        "s1",
        "p1",
        translation="AI 第一段",
        status=ParagraphStatus.TRANSLATED,
        expected_paragraph=expected,
        recompute_progress=False,
        return_section=True,
    )

    assert load_count == 1
    assert persisted_paragraph.best_translation_text() == "AI 第一段"
    assert persisted_section.paragraphs[1].best_translation_text() == "人工第二段"


def test_editing_approved_paragraph_removes_stale_confirmation_map(tmp_path):
    manager = _build_manager(tmp_path)
    manager.project_repository.save_meta(
        "demo",
        ProjectMeta(id="demo", title="Demo", source_file="source.md"),
    )
    confirmation = ParagraphConfirmation(
        paragraph_id="p1",
        selected_version_id="ai",
    )
    manager.update_paragraph_confirmation_locked(
        "demo",
        "s1",
        "p1",
        translation="已确认译文",
        confirmation=confirmation,
    )

    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p1",
        translation="重新编辑的译文",
        status=ParagraphStatus.MODIFIED,
    )

    paragraph = manager.get_section("demo", "s1").paragraphs[0]
    assert paragraph.confirmed is None
    assert "p1" not in manager.get("demo").confirmation_map


def test_confirming_reference_version_does_not_replace_ai_draft(tmp_path):
    manager = _build_manager(tmp_path)
    manager.project_repository.save_meta(
        "demo",
        ProjectMeta(id="demo", title="Demo", source_file="source.md"),
    )
    manager.update_paragraph_locked(
        "demo",
        "s1",
        "p1",
        translation="AI 草稿",
        status=ParagraphStatus.TRANSLATED,
        model="ai-model",
    )
    original_translations = manager.get_section(
        "demo", "s1"
    ).paragraphs[0].translations.copy()

    manager.update_paragraph_confirmation_locked(
        "demo",
        "s1",
        "p1",
        translation="参考版本译文",
        confirmation=ParagraphConfirmation(
            paragraph_id="p1",
            selected_version_id="reference-v1",
        ),
        model="reference-v1",
    )

    confirmed = manager.get_section("demo", "s1").paragraphs[0]
    assert confirmed.confirmed == "参考版本译文"
    assert confirmed.translations == original_translations
    assert confirmed.latest_translation().text == "AI 草稿"
