"""Title failures must remain retryable and visible in run results."""
import threading

from src.core.export_completeness import build_translation_completeness
from src.core.title_validation import is_valid_title_translation
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.llm.base import LLMProvider
from src.services.batch_translation_service import BatchTranslationService
from src.services.progress_tracker import ProgressTracker
from src.core.models import ProjectStatus


def make_service(source="Why AI needs more power", existing=None, batch=None, fallback="为何 AI 需要更多电力"):
    section = SimpleNamespace(section_id="s1", title=source, title_translation=existing)
    project = SimpleNamespace(id="demo", title=source, title_translation=existing, metadata=None, sections=[section])
    service = BatchTranslationService.__new__(BatchTranslationService)
    service._progress_tracker = ProgressTracker()
    progress = service._progress_tracker.create("demo", 1, 1, ProjectStatus.CREATED)
    service._build_title_glossary_block = lambda *a: ""
    service.llm = SimpleNamespace(
        translate_all_section_titles=Mock(return_value=batch if batch is not None else {"s1": source}),
        translate_section_title=Mock(return_value=fallback),
        translate_title=Mock(return_value={"title": fallback}),
    )
    service.project_manager = SimpleNamespace(
        update_section_title_translation_locked=Mock(side_effect=lambda p, s, t, **kw: (SimpleNamespace(title_translation=t), True)),
        compare_and_set_meta_fields=Mock(side_effect=lambda p, **kw: (SimpleNamespace(title_translation=kw["fields"]["title_translation"], metadata=None), {"title_translation"})),
    )
    analysis = SimpleNamespace(theme="AI", structure_summary="", style=SimpleNamespace(target_audience="Readers"))
    return service, project, analysis, progress


def test_base_default_does_not_disguise_provider_failure_as_original():
    provider = SimpleNamespace(translate_section_title=Mock(side_effect=RuntimeError("upstream unavailable")))
    assert LLMProvider.translate_all_section_titles(provider, [{"id": "s1", "title": "A new era"}]) == {}


@pytest.mark.asyncio
async def test_english_batch_result_triggers_per_title_fallback():
    service, project, analysis, _ = make_service()
    await service._translate_section_titles("demo", project, analysis)
    service.llm.translate_section_title.assert_called_once()
    assert project.sections[0].title_translation == "为何 AI 需要更多电力"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["article", "section"])
async def test_historical_original_is_retried(kind):
    service, project, analysis, _ = make_service(existing="Why AI needs more power")
    if kind == "article":
        await service._translate_title_and_metadata(project, analysis)
        assert project.title_translation == "为何 AI 需要更多电力"
    else:
        await service._translate_section_titles("demo", project, analysis)
        assert project.sections[0].title_translation == "为何 AI 需要更多电力"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [None, "", "Why AI needs more power", "A different English sentence", 42])
@pytest.mark.parametrize("kind", ["article", "section"])
async def test_invalid_titles_not_saved_and_record_run_errors(kind, bad):
    service, project, analysis, progress = make_service(batch={"s1": bad}, fallback=bad)
    if kind == "article":
        await service._translate_title_and_metadata(project, analysis)
        service.project_manager.compare_and_set_meta_fields.assert_not_called()
    else:
        await service._translate_section_titles("demo", project, analysis)
        service.project_manager.update_section_title_translation_locked.assert_not_called()
    assert progress.errors
    assert progress.errors[0]["stage"] == "title_translation"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["article", "section"])
async def test_provider_exceptions_record_run_errors(kind):
    service, project, analysis, progress = make_service(batch={})
    service.llm.translate_title.side_effect = RuntimeError("offline")
    service.llm.translate_section_title.side_effect = RuntimeError("offline")
    if kind == "article":
        await service._translate_title_and_metadata(project, analysis)
    else:
        await service._translate_section_titles("demo", project, analysis)
    assert "offline" in progress.errors[0]["error"]


@pytest.mark.asyncio
async def test_pure_brand_is_valid_without_chinese():
    service, project, analysis, progress = make_service(source="OpenAI", fallback="OpenAI")
    await service._translate_title_and_metadata(project, analysis)
    await service._translate_section_titles("demo", project, analysis)
    assert project.title_translation == project.sections[0].title_translation == "OpenAI"
    assert not progress.errors
    service.llm.translate_section_title.assert_not_called()


def test_title_completeness_blocks_completed_even_when_body_is_complete():
    service, project, _, progress = make_service(existing="Why AI needs more power")
    assert service._titles_complete(project, progress) is False
    assert len(progress.errors) == 2
    project.title_translation = project.sections[0].title_translation = "为何 AI 需要更多电力"
    # A failed title operation in this run must not be hidden by completed.
    assert service._titles_complete(project, progress) is False
    progress.errors.clear()
    assert service._titles_complete(project, progress) is True


@pytest.mark.asyncio
@pytest.mark.parametrize("translated, expected", [("Still an English sentence", "incomplete"), ("正确的中文标题", "completed")])
async def test_run_summary_cannot_hide_title_failures(monkeypatch, tmp_path, translated, expected):
    service, project, analysis, _ = make_service(fallback=translated)
    project.status = ProjectStatus.CREATED
    project.sections[0].paragraphs = [SimpleNamespace()]
    analysis.terminology = []
    service.translation_mode = "section"
    service.context_manager = Mock()
    service.translator = Mock()
    service._load_project_with_sections = Mock(return_value=project)
    service._count_project_translated_paragraphs = Mock(return_value=1)
    service._count_translated_paragraphs = Mock(return_value=1)
    service._create_run_artifact_dir = Mock(return_value=("title-test-run", tmp_path))
    service._artifact_service = Mock()
    service._artifact_service.get_latest_run_dir.return_value = None
    service._retranslate_scope = "resume"
    service._load_latest_analysis_snapshot = Mock(return_value=analysis)
    service._merge_analysis_with_project_glossary = Mock(return_value=analysis)
    service._is_cancelled = Mock(return_value=False)
    for name in (
        "_touch_progress", "_set_active_run", "_write_artifact_json",
        "_build_source_manifest", "_build_structure_map", "_set_active_status",
        "_get_provider_for_phase", "_seed_project_glossary",
        "_rebuild_persisted_translation_context", "_build_section_plan",
        "_build_prompt_context_snapshot", "_save_meta", "_clear_cancelled",
        "_release_active_run", "_get_quality_report_generator",
    ):
        setattr(service, name, Mock())
    service._translate_sections_in_document_order = AsyncMock(return_value=[])
    service.project_manager.get_sections = Mock(return_value=project.sections)
    service.project_manager.update_progress = Mock()
    service.project_manager.get_export_path = Mock(return_value=tmp_path / "zh.md")
    service.project_manager.export_markdown = Mock(return_value="正文已经译好")
    monkeypatch.setattr("src.services.batch_translation_service.DeepAnalyzer", Mock())
    monkeypatch.setattr("src.services.batch_translation_service.SourceMetadataTranslationService", Mock())

    result = await service.translate_project("demo")

    assert result["status"] == expected
    assert result["translated_paragraphs"] == result["total_paragraphs"] == 1
    assert result["export"]["markdown"]["generated"] is True
    assert result["error_count"] == (2 if expected == "incomplete" else 0)
    assert service._progress_tracker.get("demo").final_status == expected
    summaries = [call.args[1] for call in service._write_artifact_json.call_args_list
                 if call.args[0].name == "run-summary.json"]
    assert summaries == [result]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "Google Cloud", "Hugging Face", "Azure", "Intel", "google cloud",
    "Microsoft Azure", "Amazon Web Services", "Semi Analysis", "Tokenomics",
    "GLM 5.3", "MiniMax M3", "DeepSeek V4 Pro 0813", "Qwen3.5 397B", "Kimi K2.X",
])
@pytest.mark.parametrize("mode", ["existing", "batch", "fallback"])
async def test_protected_names_agree_across_generation_resume_and_export(name, mode):
    service, project, analysis, progress = make_service(
        source=name, existing=name if mode == "existing" else None,
        batch={} if mode == "fallback" else {"s1": name}, fallback=name,
    )
    project.sections[0].synthetic = False
    project.sections[0].paragraphs = []

    await service._translate_title_and_metadata(project, analysis)
    await service._translate_section_titles("demo", project, analysis)

    assert project.title_translation == project.sections[0].title_translation == name
    assert not progress.errors
    assert service._titles_complete(project, progress)
    assert build_translation_completeness(project.sections, project)["is_complete"]
    if mode == "existing":
        service.llm.translate_title.assert_not_called()
        service.llm.translate_all_section_titles.assert_not_called()
        service.llm.translate_section_title.assert_not_called()
        service.project_manager.compare_and_set_meta_fields.assert_not_called()
        service.project_manager.update_section_title_translation_locked.assert_not_called()
    else:
        service.project_manager.compare_and_set_meta_fields.assert_called_once()
        service.project_manager.update_section_title_translation_locked.assert_called_once()
        assert service.llm.translate_section_title.call_count == (mode == "fallback")


@pytest.mark.parametrize("source", [
    "Google Cloud is catching up", "Hugging Face launches a model",
    "Azure powers the next generation", "Intel is growing",
    "Introduction", "Trillion Parameters", "DeepSeek V4 Pro is catching up",
])
def test_protected_name_does_not_exempt_english_prose_across_layers(source):
    service, project, _, progress = make_service(source=source, existing=source)
    project.sections[0].synthetic = False
    project.sections[0].paragraphs = []
    assert not is_valid_title_translation(source, source)
    assert not service._titles_complete(project, progress)
    report = build_translation_completeness(project.sections, project)
    assert not report["is_complete"]
    assert report["missing_count"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("method", [
    "translate_title", "translate_all_section_titles", "translate_section_title",
])
async def test_title_provider_calls_execute_in_worker_thread(method):
    service, project, analysis, progress = make_service(batch={})
    loop_thread = threading.get_ident()
    assert threading.current_thread() is threading.main_thread()
    observed = []

    def provider_call(*args, **kwargs):
        observed.append((threading.get_ident(), threading.current_thread() is threading.main_thread()))
        if method == "translate_title":
            return {"title": "有效中文标题"}
        if method == "translate_all_section_titles":
            return {"s1": "有效中文标题"}
        return "有效中文标题"

    getattr(service.llm, method).side_effect = provider_call
    if method == "translate_title":
        await service._translate_title_and_metadata(project, analysis)
        assert project.title_translation == "有效中文标题"
    else:
        await service._translate_section_titles("demo", project, analysis)
        assert project.sections[0].title_translation == "有效中文标题"
    assert len(observed) == 1
    assert observed[0][0] != loop_thread
    assert observed[0][1] is False
    assert not progress.errors
