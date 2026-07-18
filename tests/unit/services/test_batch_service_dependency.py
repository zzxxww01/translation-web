from unittest.mock import Mock

from src.api import dependencies


def test_batch_service_dependency_isolates_run_context(monkeypatch) -> None:
    llm = object()
    analysis_llm = object()
    project_manager = Mock()
    project_manager.projects_path = "projects"

    monkeypatch.setattr(dependencies, "get_longform_llm_provider", lambda: llm)
    monkeypatch.setattr(dependencies, "get_analysis_llm_provider", lambda: analysis_llm)
    monkeypatch.setattr(dependencies, "get_project_manager", lambda: project_manager)
    monkeypatch.setattr(
        dependencies.BatchTranslationService,
        "_get_provider_for_phase",
        lambda self, _phase: llm,
    )

    first = dependencies.get_batch_service()
    second = dependencies.get_batch_service()

    assert first is not second
    assert first.context_manager is not second.context_manager
    assert first.translator.context_manager is first.context_manager
    assert second.translator.context_manager is second.context_manager
