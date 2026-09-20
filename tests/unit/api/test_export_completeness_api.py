"""Public API retains explicit QA override and truthful section completion."""
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from src.api.middleware import BadRequestException
from src.api.routers.projects_management import export_project, get_project, get_sections
from src.core.models import Paragraph, ParagraphStatus, ProjectMeta, Section
from src.core.project_export_service import ExportBlockedError


def manager():
    pm = Mock()
    pm.get.return_value = ProjectMeta(id="demo", title="Demo", title_translation="演示", source_file="source.md")
    pm.get_sections.return_value = [Section(section_id="s", title="Market outlook", paragraphs=[
        Paragraph(id="p", index=0, source="Demand is growing.", confirmed="需求正在增长。", status=ParagraphStatus.APPROVED),
    ])]
    pm.export.return_value = "# 演示\n\n## Market outlook\n\n需求正在增长。"
    pm.get_export_filename.return_value = "演示_zh.md"
    return pm


def request():
    return Request({"type": "http", "method": "POST", "path": "/api/projects/demo/export", "headers": [], "client": ("127.0.0.1", 50000)})


@pytest.mark.asyncio
async def test_approved_body_does_not_make_untranslated_title_complete():
    pm = manager()
    before = pm.get_sections.return_value[0].model_dump()
    project = await get_project("demo", pm)
    sections = await get_sections("demo", pm)
    assert project["translation_completeness"]["missing_title_count"] == 1
    assert project["sections"][0]["is_complete"] is False
    assert sections[0]["is_complete"] is False
    assert pm.get_sections.return_value[0].model_dump() == before


@pytest.mark.asyncio
async def test_override_response_explicitly_labels_incomplete_content():
    pm = manager()
    result = await export_project(request(), "demo", pm, allow_qa_override=True)
    assert result["is_incomplete"] is True
    assert result["translation_completeness"]["missing_title_count"] == 1
    assert result["qa_override_requested"] is True
    pm.export.assert_called_once_with("demo", include_source=False, format="zh", allow_qa_override=True)


@pytest.mark.asyncio
async def test_blocked_export_keeps_existing_error_contract():
    pm = manager()
    pm.export.side_effect = ExportBlockedError("导出被 QA 阻断：中文稿未完成，章节标题 1")
    with pytest.raises(BadRequestException, match="导出被 QA 阻断"):
        await export_project(request(), "demo", pm)
    pm.export.assert_called_once_with("demo", include_source=False, format="zh", allow_qa_override=False)


@pytest.mark.asyncio
async def test_english_export_does_not_load_or_check_translations():
    pm = manager()
    result = await export_project(request(), "demo", pm, format="en")
    assert result["translation_completeness"] is None
    assert result["is_incomplete"] is False
    pm.get_sections.assert_not_called()
    pm.get.assert_not_called()
