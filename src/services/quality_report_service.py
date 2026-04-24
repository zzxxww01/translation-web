"""Quality report service for aggregating translation quality data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from src.core.models.analysis import (
    TranslationIssue,
    ReflectionResult,
    SectionQualityScore,
    QualityReportSummary,
)

logger = logging.getLogger(__name__)


class QualityReportService:
    """Service for generating quality reports from translation artifacts."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.artifacts_dir = self.project_root / "artifacts"

    def get_latest_report(self, project_id: str) -> Optional[QualityReportSummary]:
        """获取项目最新的质量报告"""
        project_dir = self.project_root / "projects" / project_id / "artifacts" / "runs"

        if not project_dir.exists():
            return None

        # 找到最新的完整 run_id（按目录名排序，格式为 YYYYMMDD-HHMMSS-XXXXXX）。
        # 运行中或中断的目录可能已经创建，但还没有质量报告所需产物。
        run_dirs = sorted([d for d in project_dir.iterdir() if d.is_dir()], reverse=True)

        for run_dir in run_dirs:
            if not self._has_report_artifacts(run_dir):
                continue

            report = self.get_report_by_run_id(run_id=run_dir.name, project_id=project_id)
            if report:
                return report

        return None

    def _has_report_artifacts(self, run_dir: Path) -> bool:
        """Return whether a run contains enough data to build a quality summary."""
        return (
            (run_dir / "run-summary.json").exists()
            and (run_dir / "section-critique").is_dir()
        )

    def get_report_by_run_id(
        self, run_id: str, project_id: Optional[str] = None
    ) -> Optional[QualityReportSummary]:
        """根据 run_id 生成质量报告"""
        try:
            # 如果没有提供 project_id，尝试从所有项目中查找
            if project_id:
                run_dir = (
                    self.project_root
                    / "projects"
                    / project_id
                    / "artifacts"
                    / "runs"
                    / run_id
                )
            else:
                # 搜索所有项目
                projects_dir = self.project_root / "projects"
                run_dir = None
                for project_path in projects_dir.iterdir():
                    if not project_path.is_dir():
                        continue
                    candidate = project_path / "artifacts" / "runs" / run_id
                    if candidate.exists():
                        run_dir = candidate
                        project_id = project_path.name
                        break

                if not run_dir:
                    return None

            # 读取 run-summary.json
            summary_file = run_dir / "run-summary.json"
            if not summary_file.exists():
                return None

            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    run_summary = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to read run-summary.json: {e}")
                return None

            # 读取 consistency.json
            consistency_stats = {}
            consistency_file = run_dir / "consistency.json"
            if consistency_file.exists():
                try:
                    with open(consistency_file, "r", encoding="utf-8") as f:
                        consistency_data = json.load(f)
                        consistency_stats = consistency_data.get("report", {})
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to read consistency.json: {e}")
                    # 继续执行，consistency_stats 为空

            # 处理章节数据（一次性读取，避免重复）
            sections, all_issues, auto_fixed_count, manual_review_count = (
                self._process_section_data(run_dir, consistency_stats)
            )

            # 计算全文评分（按段落数加权平均）
            if sections:
                total_paragraphs = sum(s.paragraph_count for s in sections)
                if total_paragraphs > 0:
                    overall_score = sum(
                        s.overall_score * s.paragraph_count for s in sections
                    ) / total_paragraphs
                else:
                    # 如果没有段落数据，使用简单平均
                    overall_score = sum(s.overall_score for s in sections) / len(sections)
            else:
                overall_score = 0.0

            return QualityReportSummary(
                run_id=run_id,
                project_id=project_id or run_summary.get("project_id", ""),
                timestamp=run_summary.get("started_at", ""),
                overall_score=round(overall_score, 2),
                sections=sections,
                total_issues=len(all_issues),
                auto_fixed_issues=auto_fixed_count,
                manual_review_issues=manual_review_count,
                consistency_stats=consistency_stats,
            )
        except Exception as e:
            logger.error(f"Unexpected error in get_report_by_run_id: {e}", exc_info=True)
            return None

    def list_report_history(
        self, project_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """列出项目的历史报告（简化版）"""
        project_dir = self.project_root / "projects" / project_id / "artifacts" / "runs"

        if not project_dir.exists():
            return []

        run_dirs = sorted([d for d in project_dir.iterdir() if d.is_dir()], reverse=True)
        history = []

        for run_dir in run_dirs[:limit]:
            summary_file = run_dir / "run-summary.json"
            if not summary_file.exists():
                continue

            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    run_summary = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read {summary_file}: {e}")
                continue

            # 快速计算评分（使用新的合并方法）
            sections, _, _, _ = self._process_section_data(run_dir, {})
            overall_score = (
                sum(s.overall_score for s in sections) / len(sections)
                if sections
                else 0.0
            )

            total_issues = sum(s.issue_count for s in sections)

            history.append({
                "run_id": run_dir.name,
                "timestamp": run_summary.get("started_at", ""),
                "overall_score": round(overall_score, 2),
                "total_issues": total_issues,
                "status": run_summary.get("status", "unknown"),
            })

        return history

    def get_section_issues(
        self, run_id: str, section_id: str, project_id: Optional[str] = None
    ) -> List[TranslationIssue]:
        """获取特定章节的问题列表（带修复状态）"""
        # 查找 run_dir
        if project_id:
            run_dir = (
                self.project_root
                / "projects"
                / project_id
                / "artifacts"
                / "runs"
                / run_id
            )
        else:
            projects_dir = self.project_root / "projects"
            run_dir = None
            for project_path in projects_dir.iterdir():
                if not project_path.is_dir():
                    continue
                candidate = project_path / "artifacts" / "runs" / run_id
                if candidate.exists():
                    run_dir = candidate
                    break

            if not run_dir:
                return []

        # 读取 section-critique
        critique_file = run_dir / "section-critique" / f"{section_id}.json"
        if not critique_file.exists():
            return []

        try:
            with open(critique_file, "r", encoding="utf-8") as f:
                critique_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {critique_file}: {e}")
            return []

        reflection = critique_data.get("reflection", {})

        # 安全解析问题列表
        issues = []
        for issue_data in reflection.get("issues", []):
            try:
                issues.append(TranslationIssue(**issue_data))
            except Exception as e:
                logger.warning(f"Failed to parse issue in {section_id}: {e}")
                continue

        # 检查是否有 section-revision
        revision_file = run_dir / "section-revision" / f"{section_id}.json"
        if revision_file.exists() and not reflection.get("is_excellent", False):
            try:
                with open(revision_file, "r", encoding="utf-8") as f:
                    revision_data = json.load(f)

                revised_translations = revision_data.get("translations", [])

                for issue in issues:
                    issue.auto_fixed = True
                    issue.fix_method = "step4_refine"
                    # 尝试匹配修复后的文本
                    if 0 <= issue.paragraph_index < len(revised_translations):
                        issue.revised_text = revised_translations[issue.paragraph_index]
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read {revision_file}: {e}")
                # 继续执行，但不标记为已修复

        return issues

    def _process_section_data(
        self, run_dir: Path, consistency_stats: Dict[str, Any]
    ) -> Tuple[List[SectionQualityScore], List[TranslationIssue], int, int]:
        """一次性处理所有章节数据，返回评分和问题列表（避免重复文件读取）"""
        critique_dir = run_dir / "section-critique"
        if not critique_dir.exists():
            return [], [], 0, 0

        sections = []
        all_issues = []
        auto_fixed_count = 0
        manual_review_count = 0

        for critique_file in sorted(critique_dir.glob("*.json")):
            try:
                with open(critique_file, "r", encoding="utf-8") as f:
                    critique_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read {critique_file}: {e}")
                continue

            section_id = critique_data.get("section_id", critique_file.stem)
            reflection = critique_data.get("reflection", {})

            # 获取段落数：优先从 section-revision，其次 section-draft
            paragraph_count = 0
            revision_file = run_dir / "section-revision" / f"{section_id}.json"
            draft_file = run_dir / "section-draft" / f"{section_id}.json"

            if revision_file.exists():
                try:
                    with open(revision_file, "r", encoding="utf-8") as f:
                        revision_data = json.load(f)
                        paragraph_count = len(revision_data.get("translations", []))
                except (json.JSONDecodeError, IOError):
                    pass

            if paragraph_count == 0 and draft_file.exists():
                try:
                    with open(draft_file, "r", encoding="utf-8") as f:
                        draft_data = json.load(f)
                        paragraph_count = len(draft_data.get("translations", []))
                except (json.JSONDecodeError, IOError):
                    pass

            # 安全解析问题列表
            issues = []
            for issue_data in reflection.get("issues", []):
                try:
                    issues.append(TranslationIssue(**issue_data))
                except Exception as e:
                    logger.warning(f"Failed to parse issue in {section_id}: {e}")
                    continue

            issue_count = len(issues)

            # 检查是否有修复
            section_auto_fixed = 0
            if revision_file.exists() and not reflection.get("is_excellent", False):
                # 标记所有问题为已修复
                for issue in issues:
                    issue.auto_fixed = True
                    issue.fix_method = "step4_refine"
                section_auto_fixed = issue_count
                auto_fixed_count += section_auto_fixed
            else:
                manual_review_count += issue_count

            all_issues.extend(issues)

            # 创建章节评分
            sections.append(
                SectionQualityScore(
                    section_id=section_id,
                    section_title=section_id.replace("-", " ").title(),
                    overall_score=reflection.get("overall_score", 0.0),
                    readability_score=reflection.get("readability_score", 0.0),
                    accuracy_score=reflection.get("accuracy_score", 0.0),
                    conciseness_score=reflection.get("conciseness_score", 0.0),
                    is_excellent=reflection.get("is_excellent", False),
                    issue_count=issue_count,
                    auto_fixed_count=section_auto_fixed,
                    manual_review_count=issue_count - section_auto_fixed,
                    paragraph_count=paragraph_count,
                )
            )

        # 检查 consistency.json 中的 auto_fixable 问题
        auto_fixable_issues = consistency_stats.get("auto_fixable", [])
        for issue_data in auto_fixable_issues:
            try:
                issue = TranslationIssue(
                    paragraph_index=issue_data.get("paragraph_index", 0),
                    issue_type=issue_data.get("issue_type", "consistency"),
                    severity="medium",
                    description=issue_data.get("description", ""),
                    auto_fixed=True,
                    fix_method="consistency_auto_fix",
                )
                all_issues.append(issue)
                auto_fixed_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse consistency issue: {e}")
                continue

        return sections, all_issues, auto_fixed_count, manual_review_count
