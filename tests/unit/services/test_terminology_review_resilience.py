import json
from collections import Counter

from src.core.glossary import GlossaryManager
from src.core.models import Paragraph, ProjectMeta, Section
from src.core.project import ProjectManager
from src.llm.errors import LLMUpstreamUnavailableError
from src.services.terminology_review_service import TerminologyReviewService


def _build_service(tmp_path, llm, sections):
    projects_path = tmp_path / "projects"
    manager = ProjectManager(projects_path=str(projects_path))
    manager.save_meta(
        ProjectMeta(
            id="demo",
            title="Demo",
            source_file="source.md",
            progress={
                "total_sections": len(sections),
                "total_paragraphs": sum(len(section.paragraphs) for section in sections),
            },
        )
    )
    for section in sections:
        manager.save_section_only("demo", section)
    glossary_manager = GlossaryManager(
        global_path=str(tmp_path / "glossary"),
        projects_path=str(projects_path),
    )
    service = TerminologyReviewService(
        project_manager=manager,
        glossary_manager=glossary_manager,
        llm_provider=llm,
    )
    service.PRESCAN_RETRY_BASE_DELAY_SECONDS = 0
    return service


def _term_result(term: str = "chiplet") -> str:
    return json.dumps({"terms": [{"term": term, "suggested_translation": "芯粒", "reason": f"{term} 有几种常见译法"}]},
                      ensure_ascii=False)


def test_term_review_retries_transient_empty_upstream_response(tmp_path):
    class TransientLLM:
        calls = 0

        def generate(self, prompt, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise LLMUpstreamUnavailableError("empty response")
            return _term_result()

    llm = TransientLLM()
    service = _build_service(
        tmp_path,
        llm,
        [
            Section(
                section_id="s1",
                title="Chiplet architecture",
                paragraphs=[Paragraph(id="p1", index=0, source="A chiplet connects to another chiplet.")],
            )
        ],
    )

    payload = service.prepare_review("demo")

    assert llm.calls == 2
    assert payload["is_partial"] is False
    assert payload["scanned_sections"] == 1
    assert payload["failed_sections"] == 0
    assert payload["total_candidates"] == 1
    candidate = payload["sections"][0]["candidates"][0]
    assert candidate["term"] == "chiplet" and "needs_decision" in candidate["reasons"]
    assert candidate["occurrence_count"] == 2


def test_failed_chunk_loses_only_its_own_sections(tmp_path):
    class PartiallyUnavailableLLM:
        calls = Counter()

        def generate(self, prompt, **_kwargs):
            chunk = "s1" if "[s1]" in prompt else "s2"
            self.calls[chunk] += 1
            if chunk == "s1":
                raise LLMUpstreamUnavailableError("empty response")
            return _term_result("interposer")

    llm = PartiallyUnavailableLLM()
    service = _build_service(
        tmp_path,
        llm,
        [
            Section(section_id="s1", title="Unavailable section",
                    paragraphs=[Paragraph(id="p1", index=0, source="Source")]),
            Section(section_id="s2", title="Interposer architecture",
                    paragraphs=[Paragraph(id="p2", index=0, source="An interposer connects another interposer.")]),
        ],
    )
    service.ARTICLE_CHUNK_CHARS = 10  # one section per chunk

    payload = service.prepare_review("demo")

    assert llm.calls == {"s1": 3, "s2": 1}
    assert payload["is_partial"] is True
    assert payload["total_sections"] == 2
    assert payload["scanned_sections"] == 1
    assert payload["failed_sections"] == 1
    assert payload["scan_errors"][0]["section_id"] == "s1"
    assert payload["total_candidates"] == 1


def test_whole_article_goes_in_one_call_and_unseen_or_known_terms_are_dropped(tmp_path):
    class OneCallLLM:
        prompts = []

        def generate(self, prompt, **_kwargs):
            self.prompts.append(prompt)
            return json.dumps({"terms": [
                {"term": "interposer", "suggested_translation": "中介层", "reason": "r"},
                {"term": "made-up term", "suggested_translation": "x", "reason": "not in the text"},
                {"term": "known", "suggested_translation": "y", "reason": "already in the glossary"},
            ]})

    llm = OneCallLLM()
    sections = [Section(section_id=f"s{i}", title=f"Part {i}",
                        paragraphs=[Paragraph(id=f"p{i}", index=0, source=f"The interposer and a known part {i}.")])
                for i in range(3)]
    service = _build_service(tmp_path, llm, sections)
    glossary = service.glossary_manager.load_project("demo")
    service.glossary_manager.add_term(glossary, "known", "已知")
    service.glossary_manager.save_project("demo", glossary)

    payload = service.prepare_review("demo")

    assert len(llm.prompts) == 1 and all(f"[s{i}]" in llm.prompts[0] for i in range(3))
    terms = [c["term"] for section in payload["sections"] for c in section["candidates"]]
    assert terms == ["interposer"]
    assert payload["sections"][0]["candidates"][0]["occurrence_count"] == 3


def test_alternative_suggestions_keep_one_rendering_for_auto_accept(tmp_path):
    class AlternativesLLM:
        def generate(self, prompt, **_kwargs):
            return json.dumps({"terms": [{"term": "rack scale", "suggested_translation": "机架级 / 整机柜级",
                                          "reason": "两种常见说法"}]}, ensure_ascii=False)

    service = _build_service(tmp_path, AlternativesLLM(), [
        Section(section_id="s1", title="Rack scale inference",
                paragraphs=[Paragraph(id="p1", index=0, source="Rack scale systems beat rack scale rivals.")])])

    candidate = service.prepare_review("demo")["sections"][0]["candidates"][0]
    assert candidate["suggested_translation"] == "机架级"
    assert "机架级 / 整机柜级" in candidate["contexts"][0]
