"""
Consistency review endpoints.
"""

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from ...services.consistency_service import (
    ConsistencyReviewer,
    generate_consistency_report_markdown,
)
from ...core.file_utils import write_json_atomic
from ..dependencies import GlossaryManagerDep, ProjectManagerDep
from ..middleware import BadRequestException, NotFoundException
from ..utils.concurrency import run_blocking
from .translate_utils import validate_path_component


router = APIRouter(prefix="/consistency", tags=["consistency"])


class ReviewRequest(BaseModel):
    """一致性审查请求"""

    project_id: str
    include_terminology: bool = True


class ReviewResponse(BaseModel):
    """一致性审查响应"""

    report: Dict[str, Any]
    markdown_report: str


class AutoFixRequest(BaseModel):
    """自动修复请求"""

    project_id: str
    issue_id: str


class AutoFixResponse(BaseModel):
    """自动修复响应"""

    fixed_count: int
    message: str


def _report_path(projects_root: Path, project_id: str) -> Path:
    return projects_root / project_id / "consistency_report.json"


def _review_consistency_sync(project_id: str, pm, gm) -> tuple[dict, str]:
    pm.get(project_id)
    sections = pm.get_sections(project_id)
    glossary = gm.load_project(project_id)
    reviewer = ConsistencyReviewer()
    report = reviewer.review(sections, glossary)
    report_data = report.model_dump(mode="json")
    write_json_atomic(_report_path(Path(pm.projects_path), project_id), report_data)
    return report_data, generate_consistency_report_markdown(report)


def _load_consistency_report_sync(project_id: str, pm) -> Dict[str, Any]:
    pm.get(project_id)
    path = _report_path(Path(pm.projects_path), project_id)
    if not path.exists():
        return {
            "project_id": project_id,
            "report": None,
            "message": "暂无审查报告",
        }
    try:
        with open(path, "r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {
            "project_id": project_id,
            "report": None,
            "message": "报告文件损坏，请重新执行审查",
        }
    return {"project_id": project_id, "report": report}


@router.post("/review")
async def review_consistency(
    request: ReviewRequest,
    pm: ProjectManagerDep,
    gm: GlossaryManagerDep,
) -> ReviewResponse:
    """
    执行一致性审查（术语和风格）。
    """
    if not validate_path_component(request.project_id):
        raise NotFoundException(detail="Project not found")
    try:
        report_data, markdown = await run_blocking(
            _review_consistency_sync,
            request.project_id,
            pm,
            gm,
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except Exception as e:
        raise BadRequestException(detail=f"加载项目失败: {e}")

    return ReviewResponse(report=report_data, markdown_report=markdown)


@router.post("/auto-fix")
async def auto_fix_issue(
    request: AutoFixRequest,
    pm: ProjectManagerDep,
) -> AutoFixResponse:
    """
    自动修复一致性问题（轻量实现，当前仅返回统计）。
    """
    if not validate_path_component(request.project_id):
        raise NotFoundException(detail="Project not found")
    try:
        await run_blocking(pm.get, request.project_id)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")

    return AutoFixResponse(
        fixed_count=0,
        message="自动修复功能暂未启用（报告生成正常）",
    )


@router.get("/report/{project_id}")
async def get_consistency_report(
    project_id: str,
    pm: ProjectManagerDep,
) -> Dict[str, Any]:
    """
    获取最近一次一致性报告。
    """
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    try:
        return await run_blocking(_load_consistency_report_sync, project_id, pm)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/settings")
async def get_consistency_settings() -> Dict[str, Any]:
    """获取一致性审查设置。"""
    return {
        "checks": [
            {
                "id": "terminology",
                "name": "术语一致性",
                "description": "检查同一术语的翻译是否一致",
                "enabled": True,
                "severity": "medium",
            },
            {
                "id": "number_format",
                "name": "数字格式",
                "description": "检查数字表示是否一致",
                "enabled": False,
                "severity": "low",
            },
        ],
        "auto_fix_enabled": False,
    }
