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
        prompt = self._build_prompt(translations)

        # 2. 调用 LLM 生成报告
        logger.info("Calling LLM to generate quality report...")
        try:
            response = self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._create_empty_report(sections, translations)

        # 3. 解析 LLM 响应
        report_data = self._parse_llm_response(response)

        if not report_data or not report_data.get("issues"):
            logger.warning("LLM returned empty or invalid report")
            return self._create_empty_report(sections, translations)

        # 4. 规则匹配定位问题
        logger.info(f"Locating {len(report_data['issues'])} issues in document...")
        located_issues = self._locate_issues(report_data["issues"], translations)

        # 5. 构建报告对象
        summary_data = report_data.get("summary", {})
        summary = QualityReportSummary(
            total_issues=len(located_issues),
            terminology_issues=summary_data.get("terminology_issues", 0),
            logic_issues=summary_data.get("logic_issues", 0),
            fluency_issues=summary_data.get("fluency_issues", 0),
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

    def _build_prompt(self, translations: Dict[str, List[str]]) -> str:
        """构建 LLM prompt"""

        # 拼接全文译文
        full_text = []

        for section_id, paragraphs in translations.items():
            for para_idx, para_text in enumerate(paragraphs):
                full_text.append(f"[{section_id}:{para_idx}] {para_text}")

        full_text_str = "\n\n".join(full_text)

        prompt = f"""你是一位资深的中文编辑，负责审阅翻译质量。

## 待审阅译文

{full_text_str}

## 审阅任务

请从以下三个维度检查译文质量，找出所有问题：

### 1. 术语一致性
- 检查同一概念是否使用了不同的翻译
- 例如："GPU" 有时翻译为"图形处理器"，有时保留"GPU"
- 例如："machine learning" 有时翻译为"机器学习"，有时翻译为"机器学习技术"

### 2. 逻辑连贯性
- 检查段落之间、句子之间的逻辑是否连贯
- 检查代词指代是否清晰（"它"、"这"、"该"指代不明）
- 检查转折、因果关系是否合理
- 检查前后文是否矛盾

### 3. 表达流畅性
- 检查是否有翻译腔（"对...进行..."、"以便在..."）
- 检查是否有语句不通顺、表达别扭的地方
- 检查是否有冗余表达
- 检查标点符号使用是否恰当

## 输出格式

返回 JSON 格式：

```json
{{
  "summary": {{
    "total_issues": 15,
    "terminology_issues": 5,
    "logic_issues": 4,
    "fluency_issues": 6,
    "overall_quality": "良好",
    "overall_score": 8.2
  }},
  "issues": [
    {{
      "type": "terminology",
      "severity": "medium",
      "description": "术语 'GPU' 翻译不一致",
      "problematic_sentence": "这些图形处理器在训练过程中发挥了关键作用",
      "context": "前文使用 'GPU'，此处使用 '图形处理器'",
      "suggestion": "建议统一使用 'GPU'"
    }},
    {{
      "type": "logic",
      "severity": "high",
      "description": "代词指代不清",
      "problematic_sentence": "它在这个过程中起到了关键作用",
      "context": "前文提到了多个主体，'它' 指代不明确",
      "suggestion": "明确指出是哪个主体"
    }},
    {{
      "type": "fluency",
      "severity": "low",
      "description": "存在翻译腔",
      "problematic_sentence": "为了对模型进行优化，研究人员采取了多种措施",
      "context": "'对...进行...' 是典型的翻译腔",
      "suggestion": "改为 '为了优化模型，研究人员采取了多种措施'"
    }}
  ]
}}
```

## 注意事项

1. **必须提供完整的问题句子**：`problematic_sentence` 字段必须是完整的句子，便于后续定位
2. **severity 分级**：
   - `high`: 严重影响理解或准确性
   - `medium`: 影响阅读体验或专业性
   - `low`: 轻微瑕疵，不影响理解
3. **只报告真实问题**：不要为了凑数而报告不存在的问题
4. **提供可操作的建议**：`suggestion` 应该具体、可执行

请开始审阅。
"""

        return prompt

    def _parse_llm_response(self, response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""

        try:
            # 提取 JSON（可能包含在 markdown 代码块中）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response

            data = json.loads(json_str)

            # 验证必需字段
            if "summary" not in data or "issues" not in data:
                logger.error("LLM response missing required fields")
                return None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}...")
            return None

    def _locate_issues(
        self,
        issues: List[dict],
        translations: Dict[str, List[str]]
    ) -> List[QualityIssue]:
        """定位问题到具体位置"""

        located = []

        for issue_data in issues:
            problematic_sentence = issue_data.get("problematic_sentence", "")

            if not problematic_sentence:
                logger.warning(f"Issue missing problematic_sentence: {issue_data.get('description')}")
                continue

            # 查找句子位置
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
