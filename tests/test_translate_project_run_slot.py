import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from starlette.requests import Request

from src.api.middleware import BadRequestException
from src.api.routers.translate_models import FullTranslateRequest
from src.api.routers.translate_projects import (
    batch_translate_section,
    translate_full_document,
    translate_with_four_steps,
)
from src.core.format_tokens import TranslationPayload
from src.core.models import Paragraph, ParagraphStatus, ProjectStatus, Section
from src.llm.usage_metrics import llm_usage_metrics
from src.services.translation_artifact_service import TranslationArtifactService
from src.services.translation_run_registry import translation_run_registry


def _request(client_host: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": (client_host, 50000),
        }
    )


async def _consume_stream(response) -> None:
    async for _ in response.body_iterator:
        pass


@pytest.mark.asyncio
async def test_normal_stream_blocks_four_step_for_same_project() -> None:
    project_id = "normal-blocks-four-step"
    translation_run_registry.release_active_run(project_id)
    pm = Mock()
    pm.get_sections.return_value = []

    response = await translate_full_document(
        _request(),
        project_id,
        FullTranslateRequest(),
        pm=pm,
        gm=Mock(),
        llm=Mock(),
    )

    try:
        active = translation_run_registry.get_active_run(project_id)
        assert active is not None
        assert active.status == "starting"

        with pytest.raises(BadRequestException, match="already has an active translation"):
            await translate_with_four_steps(
                _request(),
                project_id,
                pm=pm,
                llm=Mock(),
                analysis_llm=Mock(),
                _body=FullTranslateRequest(),
            )
    finally:
        await _consume_stream(response)
        translation_run_registry.release_active_run(project_id)

    assert translation_run_registry.get_active_run(project_id) is None


@pytest.mark.asyncio
async def test_normal_stream_rejects_existing_project_slot() -> None:
    project_id = "four-step-blocks-normal"
    translation_run_registry.release_active_run(project_id)
    acquired = await translation_run_registry.claim_translation_slot(project_id)
    assert acquired["status"] == "acquired"

    try:
        with pytest.raises(BadRequestException, match="already has an active translation"):
            await translate_full_document(
                _request(),
                project_id,
                FullTranslateRequest(),
                pm=Mock(),
                gm=Mock(),
                llm=Mock(),
            )
    finally:
        translation_run_registry.release_active_run(project_id)


@pytest.mark.asyncio
async def test_normal_translation_continues_after_stream_is_closed(tmp_path) -> None:
    project_id = "normal-detached-background"
    translation_run_registry.release_active_run(project_id)
    started = threading.Event()
    allow_finish = threading.Event()
    paragraph = Paragraph(id="p1", index=0, source="One token.")
    section = Section(section_id="s1", title="Section", paragraphs=[paragraph])

    pm = Mock()
    pm.projects_path = tmp_path
    pm.get.return_value = SimpleNamespace(status=ProjectStatus.CREATED)
    pm.get_sections.return_value = [section]
    pm.get_section.return_value = section
    pm.merge_translation_updates_locked.return_value = (section, ["p1"], [])
    gm = Mock()
    gm.load_merged.return_value = Mock()

    def translate_paragraph(*_args, **_kwargs):
        started.set()
        assert allow_finish.wait(timeout=2)
        return TranslationPayload(text="一个token。")

    with patch(
        "src.api.routers.translate_projects.SourceMetadataTranslationService.translate_project_sources",
        return_value={"translated": 0},
    ), patch(
        "src.api.routers.translate_projects.TranslationAgent.translate_paragraph",
        side_effect=translate_paragraph,
    ):
        response = await translate_full_document(
            _request("normal-detached"),
            project_id,
            FullTranslateRequest(),
            pm=pm,
            gm=gm,
            llm=Mock(),
        )
        stream = response.body_iterator
        first_frame = await anext(stream)
        assert '"type": "start"' in first_frame
        assert await asyncio.to_thread(started.wait, 1)

        await stream.aclose()
        active = translation_run_registry.get_active_run(project_id)
        assert active is not None

        allow_finish.set()
        for _ in range(100):
            if translation_run_registry.get_active_run(project_id) is None:
                break
            await asyncio.sleep(0.01)

    assert translation_run_registry.get_active_run(project_id) is None
    generated = pm.merge_translation_updates_locked.call_args.args[2][0]
    assert generated.best_translation_text() == "一个token。"
    assert paragraph.best_translation_text() == ""


@pytest.mark.asyncio
async def test_normal_stream_stays_open_after_recoverable_paragraph_error(
    tmp_path,
) -> None:
    project_id = "normal-paragraph-error"
    translation_run_registry.release_active_run(project_id)
    first = Paragraph(id="p1", index=0, source="First")
    second = Paragraph(id="p2", index=1, source="Second")
    section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[first, second],
    )

    pm = Mock()
    pm.projects_path = tmp_path
    pm.get.return_value = SimpleNamespace(status=ProjectStatus.CREATED)
    pm.get_sections.return_value = [section]
    pm.get_section.return_value = section
    pm.merge_translation_updates_locked.return_value = (section, ["p2"], [])
    gm = Mock()
    gm.load_merged.return_value = Mock()

    call_count = 0

    def translate_paragraph(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("first paragraph failed")
        return TranslationPayload(text="第二段")

    with patch(
        "src.api.routers.translate_projects.SourceMetadataTranslationService.translate_project_sources",
        return_value={"translated": 0},
    ), patch(
        "src.api.routers.translate_projects.TranslationAgent.translate_paragraph",
        side_effect=translate_paragraph,
    ):
        response = await translate_full_document(
            _request("normal-paragraph-error"),
            project_id,
            FullTranslateRequest(),
            pm=pm,
            gm=gm,
            llm=Mock(),
        )
        chunks = [chunk async for chunk in response.body_iterator]

    assert any(
        '"type": "error"' in chunk and '"paragraph_id": "p1"' in chunk
        for chunk in chunks
    )
    assert any(
        '"type": "translated"' in chunk and '"paragraph_id": "p2"' in chunk
        for chunk in chunks
    )
    assert any('"type": "incomplete"' in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_translate_all_uses_persisted_manual_translation_in_next_prompt() -> None:
    project_id = "translate-all-persisted-context"
    first = Paragraph(id="p1", index=0, source="First")
    second = Paragraph(id="p2", index=1, source="Second")
    initial_section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[first, second],
    )
    manual_section = initial_section.model_copy(deep=True)
    manual_section.paragraphs[0].add_translation("人工第一段", "manual")
    manual_section.paragraphs[0].status = ParagraphStatus.MODIFIED
    completed_section = manual_section.model_copy(deep=True)
    completed_section.paragraphs[1].add_translation("第二段译文", "pro")

    pm = Mock()
    pm.get_section.side_effect = [initial_section, initial_section]
    pm.merge_translation_updates_locked.side_effect = [
        (manual_section, [], ["p1"]),
        (completed_section, ["p2"], []),
    ]
    gm = Mock()
    gm.load_merged.return_value = Mock()
    contexts = []

    def translate_paragraph(_paragraph, context):
        contexts.append(context)
        if len(contexts) == 1:
            return TranslationPayload(text="过期的 AI 第一段")
        return TranslationPayload(text="第二段译文")

    with patch(
        "src.api.routers.translate_projects.SourceMetadataTranslationService.translate_project_sources",
        return_value={"translated": 0, "reused": 0},
    ), patch(
        "src.api.routers.translate_projects.TranslationAgent.translate_paragraph",
        side_effect=translate_paragraph,
    ):
        result = await batch_translate_section(
            _request(),
            project_id,
            "s1",
            pm=pm,
            gm=gm,
            llm=Mock(),
        )

    assert contexts[1].previous_paragraphs == [("First", "人工第一段")]
    assert initial_section.paragraphs[0].best_translation_text() == ""
    assert result["translated_count"] == 1
    assert result["conflict_paragraph_ids"] == ["p1"]
    pm.update_progress.assert_called_once_with(project_id)


@pytest.mark.asyncio
async def test_normal_stream_uses_persisted_manual_translation_in_next_prompt(
    tmp_path,
) -> None:
    project_id = "normal-persisted-context"
    translation_run_registry.release_active_run(project_id)
    first = Paragraph(id="p1", index=0, source="First")
    second = Paragraph(id="p2", index=1, source="Second")
    initial_section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[first, second],
    )
    manual_section = initial_section.model_copy(deep=True)
    manual_section.paragraphs[0].add_translation("人工第一段", "manual")
    manual_section.paragraphs[0].status = ParagraphStatus.MODIFIED
    completed_section = manual_section.model_copy(deep=True)
    completed_section.paragraphs[1].add_translation("第二段译文", "default")

    pm = Mock()
    pm.projects_path = tmp_path
    pm.get.return_value = SimpleNamespace(status=ProjectStatus.CREATED)
    pm.get_sections.return_value = [completed_section]
    pm.get_section.side_effect = [
        initial_section,
        manual_section,
    ]
    pm.merge_translation_updates_locked.side_effect = [
        (manual_section, [], ["p1"]),
        (completed_section, ["p2"], []),
    ]
    gm = Mock()
    gm.load_merged.return_value = Mock()
    contexts = []

    def translate_paragraph(_paragraph, context):
        contexts.append(context)
        if len(contexts) == 1:
            return TranslationPayload(text="过期的 AI 第一段")
        return TranslationPayload(text="第二段译文")

    with patch(
        "src.api.routers.translate_projects.SourceMetadataTranslationService.translate_project_sources",
        return_value={"translated": 0},
    ), patch(
        "src.api.routers.translate_projects.TranslationAgent.translate_paragraph",
        side_effect=translate_paragraph,
    ):
        response = await translate_full_document(
            _request("normal-persisted-context"),
            project_id,
            FullTranslateRequest(),
            pm=pm,
            gm=gm,
            llm=Mock(),
        )
        chunks = [chunk async for chunk in response.body_iterator]

    assert contexts[1].previous_paragraphs == [("First", "人工第一段")]
    assert initial_section.paragraphs[0].best_translation_text() == ""
    assert any(
        '"type": "error"' in chunk and '"paragraph_id": "p1"' in chunk
        for chunk in chunks
    )
    assert any(
        '"type": "translated"' in chunk and '"paragraph_id": "p2"' in chunk
        for chunk in chunks
    )


@pytest.mark.asyncio
async def test_normal_stream_survives_auxiliary_artifact_write_failure(
    tmp_path,
) -> None:
    project_id = "normal-artifact-write-failure"
    translation_run_registry.release_active_run(project_id)
    paragraph = Paragraph(id="p1", index=0, source="One token.")
    initial_section = Section(
        section_id="s1",
        title="Section",
        paragraphs=[paragraph],
    )
    completed_section = initial_section.model_copy(deep=True)
    completed_section.paragraphs[0].add_translation("一个token。", "default")

    pm = Mock()
    pm.projects_path = tmp_path
    pm.get.return_value = SimpleNamespace(status=ProjectStatus.CREATED)
    pm.get_sections.return_value = [completed_section]
    pm.get_section.return_value = initial_section
    pm.merge_translation_updates_locked.return_value = (
        completed_section,
        ["p1"],
        [],
    )
    gm = Mock()
    gm.load_merged.return_value = Mock()

    with patch(
        "src.api.routers.translate_projects.SourceMetadataTranslationService.translate_project_sources",
        return_value={"translated": 0},
    ), patch(
        "src.api.routers.translate_projects.TranslationAgent.translate_paragraph",
        return_value=TranslationPayload(text="一个token。"),
    ), patch.object(
        TranslationArtifactService,
        "write_json",
        side_effect=OSError("artifact storage unavailable"),
    ), patch.object(
        llm_usage_metrics,
        "finish_run",
        wraps=llm_usage_metrics.finish_run,
    ) as finish_run:
        response = await translate_full_document(
            _request("normal-artifact-write-failure"),
            project_id,
            FullTranslateRequest(),
            pm=pm,
            gm=gm,
            llm=Mock(),
        )
        chunks = []
        stream = response.body_iterator
        async for chunk in stream:
            chunks.append(chunk)
            if '"type": "complete"' in chunk:
                assert translation_run_registry.get_active_run(project_id) is None
                break
        await stream.aclose()

    assert any('"type": "complete"' in chunk for chunk in chunks)
    assert not any(
        '"type": "error"' in chunk and '"paragraph_id"' not in chunk
        for chunk in chunks
    )
    assert translation_run_registry.get_active_run(project_id) is None
    finish_run.assert_called_once()
