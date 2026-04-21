"""Quality report API endpoints."""

from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query

from src.api.middleware import NotFoundException
from src.services.quality_report_service import QualityReportService
from src.core.models.analysis import QualityReportSummary, TranslationIssue

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

router = APIRouter(prefix="/api/quality-report", tags=["quality-report"])


@router.get("/projects/{project_id}/quality-report", response_model=QualityReportSummary)
async def get_latest_quality_report(project_id: str) -> QualityReportSummary:
    """获取项目最新的质量报告"""
    service = QualityReportService(PROJECT_ROOT)
    report = service.get_latest_report(project_id)
    if not report:
        raise NotFoundException(detail="No quality report found")
    return report


@router.get("/runs/{run_id}", response_model=QualityReportSummary)
async def get_quality_report_by_run(
    run_id: str,
    project_id: Optional[str] = Query(None, description="Project ID (optional)")
) -> QualityReportSummary:
    """根据 run_id 获取质量报告"""
    service = QualityReportService(PROJECT_ROOT)
    report = service.get_report_by_run_id(run_id, project_id)
    if not report:
        raise NotFoundException(detail="Quality report not found")
    return report


@router.get("/projects/{project_id}/history")
async def get_quality_report_history(
    project_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of reports to return")
):
    """获取项目的历史报告列表"""
    service = QualityReportService(PROJECT_ROOT)
    return service.list_report_history(project_id, limit)


@router.get("/projects/{project_id}/sections/{section_id}/quality-report")
async def get_section_quality_report(
    project_id: str, section_id: str
) -> Dict[str, Any]:
    """获取章节质量报告"""
    service = QualityReportService(PROJECT_ROOT)
    report = service.get_latest_report(project_id)
    if not report:
        raise NotFoundException(detail="No quality report found")

    # 查找章节
    section = next((s for s in report.sections if s.section_id == section_id), None)
    if not section:
        raise NotFoundException(detail="Section not found")

    # 获取章节问题
    issues = service.get_section_issues(report.run_id, section_id, project_id)

    return {
        "section_id": section.section_id,
        "section_title": section.section_title,
        "overall_score": section.overall_score,
        "readability_score": section.readability_score,
        "accuracy_score": section.accuracy_score,
        "conciseness_score": section.conciseness_score,
        "is_excellent": section.is_excellent,
        "issues": [issue.model_dump() for issue in issues],
        "revision_count": 0,
    }


@router.get("/runs/{run_id}/sections/{section_id}/issues", response_model=List[TranslationIssue])
async def get_section_issues(
    run_id: str,
    section_id: str,
    project_id: Optional[str] = Query(None, description="Project ID (optional)")
) -> List[TranslationIssue]:
    """获取特定章节的问题列表"""
    service = QualityReportService(PROJECT_ROOT)
    issues = service.get_section_issues(run_id, section_id, project_id)
    return issues
