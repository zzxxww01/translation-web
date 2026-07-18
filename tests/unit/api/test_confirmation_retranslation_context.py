from src.api.routers import confirmation_translation
from src.core.models import Glossary, Paragraph, Section


def test_prepare_retranslation_uses_persisted_drafts_and_scans_term_usage(
    monkeypatch,
):
    previous = Paragraph(id="p1", index=0, source="Previous")
    previous.add_translation("已持久化草稿", "default")
    current = Paragraph(id="p2", index=1, source="Current")
    following = Paragraph(id="p3", index=2, source="Following")
    sections = [
        Section(
            section_id="s1",
            title="Section",
            paragraphs=[previous, current, following],
        )
    ]
    glossary = Glossary(terms=[])
    captured = {}

    def fake_build_term_usage(
        supplied_sections,
        supplied_glossary,
        *,
        current_section_id,
        current_paragraph_id,
    ):
        captured["sections"] = supplied_sections
        captured["glossary"] = supplied_glossary
        captured["section_id"] = current_section_id
        captured["paragraph_id"] = current_paragraph_id
        return {"token": ["token"]}

    monkeypatch.setattr(
        confirmation_translation,
        "build_term_usage_from_project",
        fake_build_term_usage,
    )

    section_id, paragraph, expected, context, old_translation = (
        confirmation_translation._prepare_retranslation_sync(
            sections,
            glossary,
            ["保持简洁"],
            "p2",
        )
    )

    assert section_id == "s1"
    assert paragraph is current
    assert expected == current
    assert expected is not current
    assert context.previous_paragraphs == [("Previous", "已持久化草稿")]
    assert context.next_preview == ["Following"]
    assert context.term_usage == {"token": ["token"]}
    assert old_translation is None
    assert captured == {
        "sections": sections,
        "glossary": glossary,
        "section_id": "s1",
        "paragraph_id": "p2",
    }
