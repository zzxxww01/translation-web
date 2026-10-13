"""
Consistency review service.

This module provides a lightweight, file-based consistency check implementation
for terminology signals plus a reserved style score field.
"""

from collections import Counter
from ..core.term_consistency import check_terminology
from typing import Dict, List, Optional, Tuple

from ..core.models import (
    ConsistencyIssue,
    ConsistencyReport,
    Glossary,
    Section,
)


class TermConsistencyChecker:
    """Check whether glossary terms are translated consistently."""

    def check_term_consistency(
        self,
        sections: List[Section],
        glossary: Optional[Glossary] = None,
    ) -> Tuple[List[ConsistencyIssue], Dict[str, Dict]]:
        translations = {section.section_id: [para.best_translation_text() or '' for para in section.paragraphs] for section in sections}
        return check_terminology(sections, translations, glossary.terms if glossary else [])


class StyleConsistencyChecker:
    """Placeholder style checker. Style-specific checks are currently disabled."""

    def check_style_consistency(self, sections: List[Section]) -> Tuple[List[ConsistencyIssue], float]:
        """保留兼容字段，当前不执行额外风格检查。"""
        return [], 100.0


class ConsistencyReviewer:
    """Consistency reviewer facade."""

    def __init__(self):
        self.term_checker = TermConsistencyChecker()
        self.style_checker = StyleConsistencyChecker()

    def review(
        self,
        sections: List[Section],
        glossary: Optional[Glossary] = None,
    ) -> ConsistencyReport:
        term_issues, term_stats = self.term_checker.check_term_consistency(sections, glossary)
        style_issues, style_score = self.style_checker.check_style_consistency(sections)
        all_issues = term_issues + style_issues

        auto_fixable = [issue for issue in all_issues if issue.auto_fixable]
        manual_review = [issue for issue in all_issues if not issue.auto_fixable]

        suggestions = [
            {
                "issue_type": issue.issue_type,
                "section_id": issue.section_id,
                "paragraph_index": issue.paragraph_index,
                "suggestion": issue.fix_suggestion,
            }
            for issue in manual_review
            if issue.fix_suggestion
        ]

        return ConsistencyReport(
            is_consistent=len(all_issues) == 0,
            issues=all_issues,
            auto_fixable=auto_fixable,
            manual_review=manual_review,
            term_stats=term_stats,
            style_score=style_score,
            style_checked=False,
            terminology_checked=bool(glossary and glossary.terms),
            reviewed_paragraphs=sum(bool(p.best_translation_text()) for section in sections for p in section.paragraphs),
            total_paragraphs=sum(len(section.paragraphs) for section in sections),
            suggestions=suggestions,
        )

    def auto_fix(self, sections: List[Section], issue: ConsistencyIssue) -> int:
        # This lightweight implementation currently only reports, without mutation.
        _ = sections
        _ = issue
        return 0


def generate_consistency_report_markdown(report: ConsistencyReport) -> str:
    """Generate a concise Markdown report for API responses."""
    lines = [
        "# 一致性审查报告",
        "",
        f"- 是否一致: {'是' if report.is_consistent else '否'}",
        f"- 问题总数: {len(report.issues)}",
        f"- 风格评估: {report.style_score if report.style_checked else '未执行'}",
        f"- 已检查译文: {report.reviewed_paragraphs}/{report.total_paragraphs} 段",
        "",
        "## 问题列表",
        "",
    ]

    if not report.issues:
        lines.append("无明显一致性问题。")
        return "\n".join(lines)

    by_type = Counter(issue.issue_type for issue in report.issues)
    for issue_type, count in by_type.items():
        lines.append(f"- {issue_type}: {count}")
    lines.append("")

    for idx, issue in enumerate(report.issues, start=1):
        lines.append(
            f"{idx}. [{issue.issue_type}] {issue.description} "
            f"(section={issue.section_id}, paragraph_index={issue.paragraph_index})"
        )
        if issue.fix_suggestion:
            lines.append(f"   建议: {issue.fix_suggestion}")

    return "\n".join(lines)
