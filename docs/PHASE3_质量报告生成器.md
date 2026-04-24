# Phase 3: 质量报告生成器 - 设计方案

## 概述

**新定位**: Phase 3 从"一致性审查器"改为"质量报告生成器"

**核心功能**: 
- 输入：全文译文（不需要原文）
- 输出：质量报告（术语一致性、逻辑连贯性、表达流畅性问题）
- 方式：LLM 一次性生成报告 + 规则匹配定位

**不做的事**:
- ❌ 不自动修复
- ❌ 不调用多次 LLM
- ❌ 不需要原文对照

---

## 设计方案

### 1. LLM Prompt 设计

```python
def generate_quality_report_prompt(translations: Dict[str, List[str]]) -> str:
    """构建质量报告生成 prompt"""
    
    # 拼接全文译文
    full_text = []
    section_markers = []  # 记录章节边界
    
    for section_id, paragraphs in translations.items():
        section_markers.append({
            "section_id": section_id,
            "start_paragraph": len(full_text)
        })
        
        for para_idx, para_text in enumerate(paragraphs):
            full_text.append(f"[{section_id}:{para_idx}] {para_text}")
    
    full_text_str = "\n\n".join(full_text)
    
    prompt = f"""
你是一位资深的中文编辑，负责审阅翻译质量。

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
```

### 2. 规则匹配定位

```python
def locate_issues_in_document(
    issues: List[Dict],
    translations: Dict[str, List[str]]
) -> List[Dict]:
    """
    通过规则匹配将问题定位到具体段落
    
    Args:
        issues: LLM 返回的问题列表
        translations: 原始译文 {section_id: [paragraphs]}
    
    Returns:
        带位置信息的问题列表
    """
    located_issues = []
    
    for issue in issues:
        problematic_sentence = issue["problematic_sentence"]
        
        # 在全文中搜索这个句子
        location = find_sentence_location(problematic_sentence, translations)
        
        if location:
            issue["section_id"] = location["section_id"]
            issue["paragraph_index"] = location["paragraph_index"]
            issue["sentence_index"] = location["sentence_index"]
            located_issues.append(issue)
        else:
            # 如果找不到精确匹配，尝试模糊匹配
            fuzzy_location = fuzzy_find_sentence(problematic_sentence, translations)
            if fuzzy_location:
                issue["section_id"] = fuzzy_location["section_id"]
                issue["paragraph_index"] = fuzzy_location["paragraph_index"]
                issue["sentence_index"] = fuzzy_location["sentence_index"]
                issue["match_confidence"] = fuzzy_location["confidence"]
                located_issues.append(issue)
            else:
                # 实在找不到，标记为未定位
                issue["section_id"] = "unknown"
                issue["paragraph_index"] = -1
                issue["sentence_index"] = -1
                issue["match_confidence"] = 0.0
                located_issues.append(issue)
    
    return located_issues


def find_sentence_location(
    sentence: str,
    translations: Dict[str, List[str]]
) -> Optional[Dict]:
    """
    精确匹配：在译文中查找句子位置
    
    Returns:
        {
            "section_id": "chapter_1",
            "paragraph_index": 5,
            "sentence_index": 2
        }
    """
    for section_id, paragraphs in translations.items():
        for para_idx, para_text in enumerate(paragraphs):
            # 按句号、问号、感叹号分割句子
            sentences = split_sentences(para_text)
            
            for sent_idx, sent in enumerate(sentences):
                # 精确匹配（去除首尾空格）
                if sent.strip() == sentence.strip():
                    return {
                        "section_id": section_id,
                        "paragraph_index": para_idx,
                        "sentence_index": sent_idx
                    }
    
    return None


def fuzzy_find_sentence(
    sentence: str,
    translations: Dict[str, List[str]],
    threshold: float = 0.8
) -> Optional[Dict]:
    """
    模糊匹配：使用相似度算法查找最接近的句子
    
    使用场景：LLM 可能对句子做了轻微改写
    """
    from difflib import SequenceMatcher
    
    best_match = None
    best_score = 0.0
    
    for section_id, paragraphs in translations.items():
        for para_idx, para_text in enumerate(paragraphs):
            sentences = split_sentences(para_text)
            
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


def split_sentences(text: str) -> List[str]:
    """
    分割句子（中文）
    
    按句号、问号、感叹号分割
    """
    import re
    
    # 中文句子分隔符
    sentences = re.split(r'[。！？]', text)
    
    # 过滤空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences
```

### 3. 报告数据结构

```python
from dataclasses import dataclass
from typing import List, Optional

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
```

### 4. 新的 QualityReportGenerator 类

```python
class QualityReportGenerator:
    """质量报告生成器（替代 ConsistencyReviewer）"""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    def generate_report(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> QualityReport:
        """
        生成质量报告
        
        Args:
            sections: 章节列表（用于统计）
            translations: 译文 {section_id: [paragraphs]}
        
        Returns:
            QualityReport: 质量报告
        """
        import time
        
        # 1. 构建 prompt
        prompt = self._build_prompt(translations)
        
        # 2. 调用 LLM 生成报告
        logger.info("Generating quality report with LLM...")
        response = self.llm.generate(prompt)
        
        # 3. 解析 LLM 响应
        report_data = self._parse_llm_response(response)
        
        # 4. 规则匹配定位问题
        logger.info(f"Locating {len(report_data['issues'])} issues in document...")
        located_issues = self._locate_issues(report_data["issues"], translations)
        
        # 5. 构建报告对象
        summary = QualityReportSummary(
            total_issues=report_data["summary"]["total_issues"],
            terminology_issues=report_data["summary"]["terminology_issues"],
            logic_issues=report_data["summary"]["logic_issues"],
            fluency_issues=report_data["summary"]["fluency_issues"],
            overall_quality=report_data["summary"]["overall_quality"],
            overall_score=report_data["summary"]["overall_score"],
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
        # 实现见上面的 generate_quality_report_prompt()
        pass
    
    def _parse_llm_response(self, response: str) -> dict:
        """解析 LLM 返回的 JSON"""
        import json
        
        try:
            # 提取 JSON（可能包含在 markdown 代码块中）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            data = json.loads(json_str)
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # 返回空报告
            return {
                "summary": {
                    "total_issues": 0,
                    "terminology_issues": 0,
                    "logic_issues": 0,
                    "fluency_issues": 0,
                    "overall_quality": "未知",
                    "overall_score": 0.0
                },
                "issues": []
            }
    
    def _locate_issues(
        self,
        issues: List[dict],
        translations: Dict[str, List[str]]
    ) -> List[QualityIssue]:
        """定位问题到具体位置"""
        located = []
        
        for issue_data in issues:
            # 查找句子位置
            location = self._find_sentence_location(
                issue_data["problematic_sentence"],
                translations
            )
            
            if location:
                issue = QualityIssue(
                    type=issue_data["type"],
                    severity=issue_data["severity"],
                    description=issue_data["description"],
                    problematic_sentence=issue_data["problematic_sentence"],
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
                    f"Could not locate sentence: {issue_data['problematic_sentence'][:50]}..."
                )
                issue = QualityIssue(
                    type=issue_data["type"],
                    severity=issue_data["severity"],
                    description=issue_data["description"],
                    problematic_sentence=issue_data["problematic_sentence"],
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
        """查找句子位置（精确匹配 + 模糊匹配）"""
        # 实现见上面的 find_sentence_location() 和 fuzzy_find_sentence()
        pass
```

---

## 前端展示

### 报告概览

```
┌─────────────────────────────────────────────┐
│ 质量报告                                     │
├─────────────────────────────────────────────┤
│ 总体评分: 8.2/10 (良好)                      │
│ 问题总数: 15                                 │
│   - 严重 (High):   2                        │
│   - 中等 (Medium): 7                        │
│   - 轻微 (Low):    6                        │
├─────────────────────────────────────────────┤
│ 问题分类:                                    │
│   - 术语一致性: 5                            │
│   - 逻辑连贯性: 4                            │
│   - 表达流畅性: 6                            │
└─────────────────────────────────────────────┘
```

### 问题列表

```
┌─────────────────────────────────────────────┐
│ 问题 #1 [严重]                               │
├─────────────────────────────────────────────┤
│ 类型: 逻辑连贯性                             │
│ 位置: Chapter 3, 段落 5, 句子 2              │
│                                             │
│ 问题句子:                                    │
│ "它在这个过程中起到了关键作用。"              │
│                                             │
│ 问题描述:                                    │
│ 代词指代不清，前文提到了多个主体              │
│                                             │
│ 修改建议:                                    │
│ 明确指出是哪个主体（GPU/模型/算法）           │
│                                             │
│ [查看上下文] [标记已修复] [忽略]              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 问题 #2 [中等]                               │
├─────────────────────────────────────────────┤
│ 类型: 术语一致性                             │
│ 位置: Chapter 5, 段落 12, 句子 1             │
│                                             │
│ 问题句子:                                    │
│ "这些图形处理器在训练过程中发挥了关键作用。"   │
│                                             │
│ 问题描述:                                    │
│ 术语 'GPU' 翻译不一致，前文使用 'GPU'        │
│                                             │
│ 修改建议:                                    │
│ 建议统一使用 'GPU'                           │
│                                             │
│ [查看上下文] [标记已修复] [忽略]              │
└─────────────────────────────────────────────┘
```

---

## 成本分析

### 单次报告生成

**输入**:
- 650 段译文
- 约 50,000 tokens（中文）

**输出**:
- 报告 JSON
- 约 2,000 tokens

**成本** (DeepSeek v3):
- Input: 50,000 × $0.27/1M = $0.0135
- Output: 2,000 × $1.10/1M = $0.0022
- **总计: ~$0.016**

**耗时**:
- LLM 调用: ~10-15 秒
- 规则匹配: ~1-2 秒
- **总计: ~12-17 秒**

---

## 实施步骤

### 第 1 步：重命名和重构

```bash
# 重命名文件
mv src/agents/consistency_reviewer.py src/agents/quality_report_generator.py

# 更新类名
ConsistencyReviewer → QualityReportGenerator
ConsistencyReport → QualityReport
ConsistencyIssue → QualityIssue
```

### 第 2 步：实现新的 prompt

- 创建 `src/prompts/longform/review/quality_report.txt`
- 实现 `_build_prompt()` 方法

### 第 3 步：实现规则匹配

- 实现 `_find_sentence_location()`
- 实现 `fuzzy_find_sentence()`
- 实现 `split_sentences()`

### 第 4 步：更新数据模型

- 在 `src/core/models.py` 中添加新的数据类
- 移除 `auto_fixable` 字段（不再需要）

### 第 5 步：更新调用方

- 修改 `src/services/batch_translation_service.py`
- 更新 API 返回格式

### 第 6 步：前端适配

- 更新前端展示组件
- 支持按严重程度筛选
- 支持跳转到具体位置

---

## 优势

✅ **简单高效**:
- 只需 1 次 LLM 调用
- 成本低（~$0.016）
- 耗时短（~15 秒）

✅ **功能全面**:
- 术语一致性
- 逻辑连贯性
- 表达流畅性

✅ **易于使用**:
- 前端可视化展示
- 可跳转到具体位置
- 可标记已修复/忽略

✅ **可扩展**:
- 可以添加更多检查维度
- 可以调整严重程度阈值
- 可以自定义报告格式

---

**文档版本**: 1.0  
**创建时间**: 2026-04-25  
**状态**: 设计方案
