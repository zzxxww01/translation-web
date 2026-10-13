"""
Translation Agent - Quality Report Generator

质量报告生成器（Phase 3）

使用 LLM 生成全文质量报告，检查：
- 术语一致性
- 逻辑连贯性
- 表达流畅性
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re
import json
import logging
from difflib import SequenceMatcher

from ..core.models import Section, ArticleAnalysis
from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """质量问题"""

    # 问题类型
    type: str  # "terminology", "logic", "fluency"

    # 严重程度
    severity: str  # "high", "medium", "low"

    # 问题描述
    description: str

    # 有问题的句子（完整）
    problematic_sentence: str

    # 上下文说明
    context: str

    # 修改建议
    suggestion: str

    # 位置信息（通过规则匹配得到）
    section_id: str
    paragraph_index: int
    sentence_index: int

    # 匹配置信度（精确匹配=1.0，模糊匹配<1.0）
    match_confidence: float = 1.0


@dataclass
class QualityReportSummary:
    """质量报告摘要"""

    total_issues: int
    terminology_issues: int
    logic_issues: int
    fluency_issues: int

    overall_quality: str  # "优秀", "良好", "合格", "需改进"
    overall_score: float  # 0-10 分

    # 按严重程度统计
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int


@dataclass
class QualityReport:
    """质量报告"""

    summary: QualityReportSummary
    issues: List[QualityIssue]

    # 元数据
    generated_at: str
    total_paragraphs: int
    total_sections: int

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "summary": {
                "total_issues": self.summary.total_issues,
                "terminology_issues": self.summary.terminology_issues,
                "logic_issues": self.summary.logic_issues,
                "fluency_issues": self.summary.fluency_issues,
                "overall_quality": self.summary.overall_quality,
                "overall_score": self.summary.overall_score,
                "high_severity_count": self.summary.high_severity_count,
                "medium_severity_count": self.summary.medium_severity_count,
                "low_severity_count": self.summary.low_severity_count
            },
            "issues": [
                {
                    "type": issue.type,
                    "severity": issue.severity,
                    "description": issue.description,
                    "problematic_sentence": issue.problematic_sentence,
                    "context": issue.context,
                    "suggestion": issue.suggestion,
                    "location": {
                        "section_id": issue.section_id,
                        "paragraph_index": issue.paragraph_index,
                        "sentence_index": issue.sentence_index
                    },
                    "match_confidence": issue.match_confidence
                }
                for issue in self.issues
            ],
            "metadata": {
                "generated_at": self.generated_at,
                "total_paragraphs": self.total_paragraphs,
                "total_sections": self.total_sections
            }
        }


class QualityReportGenerator:
    """质量报告生成器"""

    def __init__(self, llm_provider: LLMProvider):
        """
        初始化质量报告生成器

        Args:
            llm_provider: LLM Provider（默认使用 Gemini Preview）
        """
        self.llm = llm_provider

    def generate_report(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]],
        article_analysis: Optional[ArticleAnalysis] = None
    ) -> QualityReport:
        """
        生成质量报告

        Args:
            sections: 章节列表（用于统计）
            translations: 译文 {section_id: [paragraphs]}
            article_analysis: 文章分析结果（可选，暂未使用）

        Returns:
            QualityReport: 质量报告
        """
        import time

        logger.info("Starting quality report generation...")

        # 1. 构建 prompt
        prompt = self._build_prompt(translations, sections, article_analysis)

        # 2. 调用 LLM 生成报告
        logger.info("Calling LLM to generate quality report...")
        try:
            response = self.llm.generate(prompt, response_format="json")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError("Quality review failed; not a clean report") from e

        # 3. 解析 LLM 响应
        report_data = self._parse_llm_response(response)

        if report_data is None:
            raise ValueError("Quality review response is invalid; no clean report was produced")

        # 4. 规则匹配定位问题
        logger.info(f"Locating {len(report_data['issues'])} issues in document...")
        located_issues = self._locate_issues(report_data["issues"], translations)

        # 5. 构建报告对象
        summary_data = report_data.get("summary", {})
        summary = QualityReportSummary(
            total_issues=len(located_issues),
            terminology_issues=sum(i.type == "terminology" for i in located_issues),
            logic_issues=sum(i.type == "logic" for i in located_issues),
            fluency_issues=sum(i.type == "fluency" for i in located_issues),
            overall_quality=summary_data.get("overall_quality", "未知"),
            overall_score=summary_data.get("overall_score", 0.0),
            high_severity_count=len([i for i in located_issues if i.severity == "high"]),
            medium_severity_count=len([i for i in located_issues if i.severity == "medium"]),
            low_severity_count=len([i for i in located_issues if i.severity == "low"])
        )

        report = QualityReport(
            summary=summary,
            issues=located_issues,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_paragraphs=sum(len(paras) for paras in translations.values()),
            total_sections=len(sections)
        )

        logger.info(
            f"Quality report generated: {summary.total_issues} issues found "
            f"(H:{summary.high_severity_count}, M:{summary.medium_severity_count}, L:{summary.low_severity_count})"
        )

        return report

    def _build_prompt(self, translations: Dict[str, List[str]], sections: Optional[List[Section]] = None,
                      article_analysis: Optional[ArticleAnalysis] = None) -> str:
        from src.prompts import get_prompt_manager
        sources = {s.section_id: s.paragraphs for s in (sections or [])}
        pairs = []
        for sid, paragraphs in translations.items():
            for index, text in enumerate(paragraphs):
                originals = sources.get(sid, [])
                source = originals[index].source if index < len(originals) else "（未提供原文，仅作中文编辑检查）"
                pairs.append({"section_id":sid,"paragraph_index":index,"source":source,"translation":text})
        context = article_analysis.model_dump(mode="json") if article_analysis else {}
        return get_prompt_manager().render("longform/review/quality_report", pairs=json.dumps(pairs, ensure_ascii=False), article_context=json.dumps(context, ensure_ascii=False))

    def _parse_llm_response(self, response: str) -> Optional[dict]:
        from src.prompts.contracts import object_response
        result = object_response(response, ("summary", "issues"))
        if not isinstance(result["summary"], dict) or not isinstance(result["issues"], list):
            raise ValueError("Invalid quality report schema")
        return result

    def _locate_issues(
        self,
        issues: List[dict],
        translations: Dict[str, List[str]]
    ) -> List[QualityIssue]:
        """定位问题到具体位置"""

        located = []

        for issue_data in issues:
            problematic_sentence = issue_data.get("problematic_sentence", "")

            if not isinstance(problematic_sentence, str) or not problematic_sentence.strip():
                raise ValueError("Review finding has no translated evidence; cannot produce a clean report")

            # Prefer the explicit location in v2, never silently map a duplicate sentence elsewhere.
            sid, idx = issue_data.get("section_id"), issue_data.get("paragraph_index")
            if sid is not None or idx is not None:
                if sid not in translations or type(idx) is not int or not 0 <= idx < len(translations[sid]):
                    raise ValueError("Invalid quality finding location")
                paragraph = translations[sid][idx]
                if problematic_sentence not in paragraph:
                    raise ValueError("Quality finding evidence is not present at its supplied location")
                sentence_index = sum(len(part) > 0 for part in re.split(r"[。！？]", paragraph[:paragraph.index(problematic_sentence)]))
                location = {"section_id": sid, "paragraph_index": idx, "sentence_index": sentence_index, "confidence": 1.0}
            else:
                # Historical reports can still be displayed with their match confidence.
                location = self._find_sentence_location(problematic_sentence, translations)

            if location:
                issue = QualityIssue(
                    type=issue_data.get("type", "unknown"),
                    severity=issue_data.get("severity", "medium"),
                    description=issue_data.get("description", ""),
                    problematic_sentence=problematic_sentence,
                    context=issue_data.get("context", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    section_id=location["section_id"],
                    paragraph_index=location["paragraph_index"],
                    sentence_index=location["sentence_index"],
                    match_confidence=location.get("confidence", 1.0)
                )
                located.append(issue)
            else:
                # 找不到位置，仍然记录问题
                logger.warning(
                    f"Could not locate sentence: {problematic_sentence[:50]}..."
                )
                issue = QualityIssue(
                    type=issue_data.get("type", "unknown"),
                    severity=issue_data.get("severity", "medium"),
                    description=issue_data.get("description", ""),
                    problematic_sentence=problematic_sentence,
                    context=issue_data.get("context", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    section_id="unknown",
                    paragraph_index=-1,
                    sentence_index=-1,
                    match_confidence=0.0
                )
                located.append(issue)

        return located

    def _find_sentence_location(
        self,
        sentence: str,
        translations: Dict[str, List[str]]
    ) -> Optional[dict]:
        """
        查找句子位置（精确匹配 + 模糊匹配）

        Returns:
            {
                "section_id": "chapter_1",
                "paragraph_index": 5,
                "sentence_index": 2,
                "confidence": 1.0
            }
        """

        # 1. 精确匹配
        for section_id, paragraphs in translations.items():
            for para_idx, para_text in enumerate(paragraphs):
                sentences = self._split_sentences(para_text)

                for sent_idx, sent in enumerate(sentences):
                    # 精确匹配（去除首尾空格）
                    if sent.strip() == sentence.strip():
                        return {
                            "section_id": section_id,
                            "paragraph_index": para_idx,
                            "sentence_index": sent_idx,
                            "confidence": 1.0
                        }

        # 2. 模糊匹配
        best_match = None
        best_score = 0.0
        threshold = 0.8

        for section_id, paragraphs in translations.items():
            for para_idx, para_text in enumerate(paragraphs):
                sentences = self._split_sentences(para_text)

                for sent_idx, sent in enumerate(sentences):
                    # 计算相似度
                    score = SequenceMatcher(None, sent.strip(), sentence.strip()).ratio()

                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = {
                            "section_id": section_id,
                            "paragraph_index": para_idx,
                            "sentence_index": sent_idx,
                            "confidence": score
                        }

        return best_match

    def _split_sentences(self, text: str) -> List[str]:
        """
        分割句子（中文）

        按句号、问号、感叹号分割
        """
        # 中文句子分隔符
        sentences = re.split(r'[。！？]', text)

        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _create_empty_report(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> QualityReport:
        """创建空报告（LLM 调用失败时）"""

        import time

        summary = QualityReportSummary(
            total_issues=0,
            terminology_issues=0,
            logic_issues=0,
            fluency_issues=0,
            overall_quality="未知",
            overall_score=0.0,
            high_severity_count=0,
            medium_severity_count=0,
            low_severity_count=0
        )

        return QualityReport(
            summary=summary,
            issues=[],
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_paragraphs=sum(len(paras) for paras in translations.values()),
            total_sections=len(sections)
        )


def create_quality_report_generator(llm_provider: LLMProvider) -> QualityReportGenerator:
    """
    创建质量报告生成器

    Args:
        llm_provider: LLM Provider

    Returns:
        QualityReportGenerator: 质量报告生成器实例
    """
    return QualityReportGenerator(llm_provider=llm_provider)
