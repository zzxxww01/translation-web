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


def _term_result(term: str = "chiplet"):
    return {
        "new_terms": [
            {
                "term": term,
                "suggested_translation": "芯粒",
                "context": f"{term} packaging",
            }
        ]
    }


def test_term_review_retries_transient_empty_upstream_response(tmp_path):
    class TransientLLM:
        calls = 0

        def prescan_section_with_flash(self, **_kwargs):
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
                paragraphs=[
                    Paragraph(
                        id="p1",
                        index=0,
                        source="A chiplet connects to another chiplet.",
                    )
                ],
            )
        ],
    )

    payload = service.prepare_review("demo")

    assert llm.calls == 2
    assert payload["is_partial"] is False
    assert payload["scanned_sections"] == 1
    assert payload["failed_sections"] == 0
    assert payload["total_candidates"] == 1


def test_term_review_preserves_other_sections_after_retry_exhaustion(tmp_path):
    class PartiallyUnavailableLLM:
        calls = Counter()

        def prescan_section_with_flash(self, **kwargs):
            section_id = kwargs["section_id"]
            self.calls[section_id] += 1
            if section_id == "s1":
                raise LLMUpstreamUnavailableError("empty response")
            return _term_result("interposer")

    llm = PartiallyUnavailableLLM()
    service = _build_service(
        tmp_path,
        llm,
        [
            Section(
                section_id="s1",
                title="Unavailable section",
                paragraphs=[Paragraph(id="p1", index=0, source="Source")],
            ),
            Section(
                section_id="s2",
                title="Interposer architecture",
                paragraphs=[
                    Paragraph(
                        id="p2",
                        index=0,
                        source="An interposer connects another interposer.",
                    )
                ],
            ),
        ],
    )

    payload = service.prepare_review("demo")

    assert llm.calls == {"s1": 3, "s2": 1}
    assert payload["is_partial"] is True
    assert payload["total_sections"] == 2
    assert payload["scanned_sections"] == 1
    assert payload["failed_sections"] == 1
    assert payload["scan_errors"][0]["section_id"] == "s1"
    assert payload["total_candidates"] == 1
