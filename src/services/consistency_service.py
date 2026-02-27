"""
Consistency review service.

This module provides a lightweight, file-based consistency check implementation
for terminology and style signals.
"""

from collections import Counter, defaultdict
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
        issues: List[ConsistencyIssue] = []
        term_stats: Dict[str, Dict] = {}

        if not glossary or not glossary.terms:
            return issues, term_stats

        # term -> translation -> [(section_id, paragraph_index), ...]
        usage: Dict[str, Dict[str, List[Tuple[str, int]]]] = defaultdict(lambda: defaultdict(list))

        for section in sections:
            for para in section.paragraphs:
                if not para.confirmed:
                    continue
                for term in glossary.terms:
                    source_term = term.original
                    expected = term.translation or ""
                    if not expected:
                        continue
                    if source_term.lower() in para.source.lower():
                        used_expected = expected in para.confirmed
                        key = expected if used_expected else "__other__"
                        usage[source_term][key].append((section.section_id, para.index))

        for term, translations in usage.items():
            expected_count = len(translations.get(next((k for k in translations if k != "__other__"), ""), []))
            other_count = len(translations.get("__other__", []))
            term_stats[term] = {
                "expected_hits": expected_count,
                "other_hits": other_count,
                "total_hits": expected_count + other_count,
            }

            if other_count > 0:
                location = translations["__other__"][0]
                issues.append(
                    ConsistencyIssue(
                        section_id=location[0],
                        paragraph_index=location[1],
                        issue_type="terminology",
                        description=f'术语 "{term}" 可能存在不一致译法',
                        auto_fixable=False,
                        fix_suggestion="请统一为术语表推荐译法",
                    )
                )

        return issues, term_stats


class StyleConsistencyChecker:
    """Check simple punctuation style consistency in confirmed translations."""

    def check_style_consistency(self, sections: List[Section]) -> Tuple[List[ConsistencyIssue], float]:
        issues: List[ConsistencyIssue] = []
        english_punct = 0
        chinese_punct = 0
        first_mixed_location: Optional[Tuple[str, int]] = None

        for section in sections:
            for para in section.paragraphs:
                if not para.confirmed:
                    continue
                text = para.confirmed
                has_cn_char = any("\u4e00" <= c <= "\u9fff" for c in text)
                has_en_punct = "," in text or "." in text
                has_cn_punct = "，" in text or "。" in text

                if has_en_punct:
                    english_punct += 1
                if has_cn_punct:
                    chinese_punct += 1

                if has_cn_char and has_en_punct and first_mixed_location is None:
                    first_mixed_location = (section.section_id, para.index)

        if first_mixed_location and chinese_punct > 0:
            issues.append(
                ConsistencyIssue(
                    section_id=first_mixed_location[0],
                    paragraph_index=first_mixed_location[1],
                    issue_type="style",
                    description="检测到中文语句内可能混用英文标点",
                    auto_fixable=False,
                    fix_suggestion="中文语句建议统一使用中文标点（，。）",
                )
            )

        total_punct = english_punct + chinese_punct
        if total_punct == 0:
            style_score = 100.0
        else:
            dominant = max(english_punct, chinese_punct)
            style_score = round((dominant / total_punct) * 100, 2)

        return issues, style_score


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
        f"- 风格分数: {report.style_score}",
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
