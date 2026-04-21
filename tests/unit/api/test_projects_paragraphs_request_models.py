from types import SimpleNamespace

import pytest

from src.api.routers import projects_paragraphs
from src.api.routers.projects_models import TranslateRequest, WordMeaningMessage, WordMeaningRequest
from src.core.models import Paragraph, Section


class _FakeProjectManager:
    def __init__(self) -> None:
        self.section = Section(
            section_id="s1",
            title="Section",
            paragraphs=[Paragraph(id="p1", index=0, source="HBM bandwidth")],
        )

    def get_section(self, _project_id: str, _section_id: str):
        return self.section

    def get_sections(self, _project_id: str):
        return [self.section]

    def update_paragraph_locked(self, _project_id: str, _section_id: str, paragraph_id: str, **kwargs):
        paragraph = self.section.paragraphs[0]
        paragraph.id = paragraph_id
        paragraph.confirmed = kwargs.get("translation")
        paragraph.status = kwargs.get("status")
        return paragraph


class _FakeGlossaryManager:
    def load_merged(self, _project_id: str):
        return SimpleNamespace(terms=[])


class _FakeMemoryService:
    def get_rules_for_prompt(self):
        return []


def test_translate_paragraph_sync_uses_body_option_id(monkeypatch):
    captured = {}

    class FakeAgent:
        def __init__(self, _llm, timeout=None):
            captured["timeout"] = timeout

        def retranslate_paragraph(self, _paragraph, _context, formatted_instruction):
            captured["formatted_instruction"] = formatted_instruction
            return SimpleNamespace(text="重译结果", tokenized_text=None, format_issues=[])

        def translate_paragraph(self, _paragraph, _context):
            raise AssertionError("translate_paragraph should not be called when option_id is provided")

    monkeypatch.setattr(projects_paragraphs, "TranslationAgent", FakeAgent)
    monkeypatch.setattr(projects_paragraphs.TimeoutConfig, "get_timeout", lambda _key: 5)
    monkeypatch.setattr(
        projects_paragraphs,
        "resolve_retranslate_instruction",
        lambda instruction, option_id: f"resolved:{instruction or ''}:{option_id or ''}",
    )
    monkeypatch.setattr(
        projects_paragraphs,
        "build_retranslate_instruction",
        lambda instruction, source, current: f"{instruction}|{source}|{current}",
    )
    monkeypatch.setattr(projects_paragraphs, "get_latest_translation_text", lambda _paragraph: "旧译文")

    result = projects_paragraphs._translate_paragraph_sync(
        "demo",
        "s1",
        "p1",
        TranslateRequest(option_id="readable"),
        _FakeProjectManager(),
        _FakeGlossaryManager(),
        object(),
        _FakeMemoryService(),
    )

    assert result["translation"] == "重译结果"
    assert captured["formatted_instruction"] == "resolved::readable|HBM bandwidth|旧译文"


def test_query_word_meaning_sync_reads_body_fields():
    class FakeProjectManager:
        def get_section(self, _project_id: str, _section_id: str):
            return Section(
                section_id="s1",
                title="Section",
                paragraphs=[Paragraph(id="p1", index=0, source="HBM bandwidth")],
            )

    class FakeLLM:
        def __init__(self):
            self.prompt = None

        def generate(self, prompt, temperature=0.3, max_retries=2):
            self.prompt = prompt
            return "词义解释"

    llm = FakeLLM()
    response = projects_paragraphs._query_word_meaning_sync(
        "demo",
        "s1",
        "p1",
        WordMeaningRequest(
            word="HBM",
            query="这里的 HBM 是什么含义？",
            history=[WordMeaningMessage(role="user", content="先解释缩写")],
        ),
        FakeProjectManager(),
        llm,
    )

    assert response.answer == "词义解释"
    assert "这里的 HBM 是什么含义？" in llm.prompt

