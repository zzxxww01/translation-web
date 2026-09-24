"""Version-aware quality gate.

Only unresolved serious issues, incomplete coverage and structural errors block.
Numeric scores/legacy mode thresholds remain diagnostic compatibility fields;
low model scores alone never authorize a rewrite or prove an error.
"""

from typing import List, Dict, Optional

from ..core.models import (
    Section, ReflectionResult, TranslationIssue,
    QualityAssessment
)


class QualityGate:
    """质量门禁"""

    # 评估维度权重
    WEIGHTS = {
        "readability": 0.35,
        "accuracy": 0.30,
        "terminology": 0.15,
        "completeness": 0.15,
        "style": 0.05
    }

    # 严格模式阈值
    STRICT_THRESHOLDS = {
        "overall": 8.5,
        "readability": 8.0,
        "critical_errors": 0  # 不允许关键错误
    }

    # 标准模式阈值
    STANDARD_THRESHOLDS = {
        "overall": 7.0,
        "readability": 6.5,
        "critical_errors": 2
    }

    # 宽松模式阈值
    RELAXED_THRESHOLDS = {
        "overall": 6.0,
        "readability": 5.5,
        "critical_errors": 5
    }

    def __init__(self, mode: str = "strict"):
        """
        初始化质量门禁

        Args:
            mode: 模式，可选 "strict", "standard", "relaxed"
        """
        self.mode = mode
        self.thresholds = self._get_thresholds(mode)

    def _get_thresholds(self, mode: str) -> Dict[str, float]:
        """获取对应模式的阈值"""
        if mode == "strict":
            return self.STRICT_THRESHOLDS
        elif mode == "standard":
            return self.STANDARD_THRESHOLDS
        elif mode == "relaxed":
            return self.RELAXED_THRESHOLDS
        else:
            return self.STRICT_THRESHOLDS

    def assess(self, section: Section, translations: List[str], reflection: ReflectionResult) -> QualityAssessment:
        from ..prompts.contracts import text_version
        scores = {"readability":reflection.readability_score, "accuracy":reflection.accuracy_score,
                  "terminology":self._assess_terminology(section, translations, reflection),
                  "completeness":self._assess_completeness(section, translations), "style":self._assess_style(reflection)}
        overall = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        failed = []
        if reflection.review_status != "complete" or reflection.coverage != 1.0:
            failed.append("review_incomplete")
        if not reflection.reviewed_version or reflection.reviewed_version != text_version([p.source for p in section.paragraphs], translations):
            failed.append("review_version_mismatch")
        if len(translations) != len(section.paragraphs) or any(not t.strip() for t in translations):
            failed.append("missing_or_empty_translation")
        if any(issue.severity in {"critical", "high"} for issue in reflection.issues):
            failed.append("unresolved_serious_issues")
        return QualityAssessment(passed=not failed, overall_score=overall, scores=scores,
                                 failed_criteria=failed, action="manual_review" if failed else "pass")

    def _assess_terminology(
        self,
        section: Section,
        translations: List[str],
        reflection: ReflectionResult
    ) -> float:
        """
        评估术语一致性

        基于反思结果中的术语问题数量计算
        """
        # 统计术语相关问题
        terminology_issues = [
            issue for issue in reflection.issues
            if issue.issue_type == "terminology"
        ]

        # 如果没有术语问题，满分
        if not terminology_issues:
            return 10.0

        # 每个术语问题扣 1 分，最低 0 分
        deduction = len(terminology_issues) * 1.0
        return max(0.0, 10.0 - deduction)

    def _assess_completeness(
        self,
        section: Section,
        translations: List[str]
    ) -> float:
        """
        评估完整性

        检查译文数量是否与原文段落数量一致
        检查是否有空译文
        """
        if len(translations) != len(section.paragraphs):
            return 5.0  # 数量不匹配，严重问题

        # 检查空译文
        empty_count = sum(1 for t in translations if not t.strip())
        if empty_count > 0:
            return max(0.0, 10.0 - empty_count * 2.0)

        # 检查译文长度是否合理（不应该比原文短太多）
        length_issues = 0
        for para, trans in zip(section.paragraphs, translations):
            source_len = len(para.source)
            trans_len = len(trans)
            # 如果译文长度不到原文的 30%，可能有遗漏
            if source_len > 50 and trans_len < source_len * 0.3:
                length_issues += 1

        return max(0.0, 10.0 - length_issues * 1.5)

    def _assess_style(self, reflection: ReflectionResult) -> float:
        """
        评估风格一致性

        基于反思结果中的风格问题数量计算
        """
        style_issues = [
            issue for issue in reflection.issues
            if issue.issue_type in {"style", "tone", "readability", "annotation"}
        ]

        if not style_issues:
            return 10.0

        deduction = len(style_issues) * 1.5
        return max(0.0, 10.0 - deduction)

    def _count_critical_errors(self, issues: List[TranslationIssue]) -> int:
        return sum(issue.severity == "critical" for issue in issues)

    def _determine_action(
        self,
        passed: bool,
        overall_score: float,
        critical_errors: int
    ) -> str:
        """
        决定建议动作

        Returns:
            str: "pass" / "refine" / "retranslate"
        """
        if passed:
            return "pass"

        # 如果有关键错误，建议重译
        if critical_errors > self.thresholds["critical_errors"]:
            return "retranslate"

        # 如果评分太低，建议重译
        if overall_score < self.thresholds["overall"] - 1.5:
            return "retranslate"

        # 否则建议润色
        return "refine"

    def get_quality_report(self, assessment: QualityAssessment) -> str:
        """
        生成质量报告

        Args:
            assessment: 质量评估结果

        Returns:
            str: 格式化的质量报告
        """
        lines = [
            "=" * 50,
            "翻译质量评估报告",
            "=" * 50,
            "",
            f"模式: {self.mode}",
            f"通过: {'✅ 是' if assessment.passed else '❌ 否'}",
            f"建议动作: {self._action_to_chinese(assessment.action)}",
            "",
            "评分详情:",
            "-" * 30,
        ]

        # 各维度评分
        dimension_names = {
            "readability": "可读性",
            "accuracy": "准确性",
            "terminology": "术语一致",
            "completeness": "完整性",
            "style": "风格"
        }

        for dim, score in assessment.scores.items():
            weight = self.WEIGHTS.get(dim, 0) * 100
            name = dimension_names.get(dim, dim)
            lines.append(f"  {name} ({weight:.0f}%): {score:.1f}/10")

        lines.extend([
            "-" * 30,
            f"综合评分: {assessment.overall_score:.1f}/10",
            "",
        ])

        # 未通过的标准
        if assessment.failed_criteria:
            lines.append("未通过的标准:")
            for criteria in assessment.failed_criteria:
                lines.append(f"  ❌ {criteria}")

        lines.append("=" * 50)

        return "\n".join(lines)

    def _action_to_chinese(self, action: str) -> str:
        """将动作转换为中文"""
        mapping = {
            "pass": "通过",
            "refine": "润色优化",
            "retranslate": "重新翻译",
            "manual_review": "待人工审核"
        }
        return mapping.get(action, action)


def create_quality_gate(mode: str = "strict") -> QualityGate:
    """
    创建质量门禁

    Args:
        mode: 模式，可选 "strict", "standard", "relaxed"

    Returns:
        QualityGate: 质量门禁实例
    """
    return QualityGate(mode=mode)
