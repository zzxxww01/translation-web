"""
Translation Agent - Consistency Reviewer

全文一致性审查器（Phase 2）

检查项：
1. 术语一致性 - 同一术语翻译是否统一
2. 风格一致性 - 语气、正式程度是否统一
3. 逻辑连贯性 - 上下文是否连贯
4. 交叉引用准确性 - 前后引用是否正确
5. 数据一致性 - 数字、单位是否准确

增强功能：
- 术语使用统计
- 风格一致性评分
- 建议修正列表
"""

from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import re
import logging

from ..core.models import (
    Section,
    ArticleAnalysis, EnhancedTerm,
    TermUsageTracker, ConsistencyIssue, ConsistencyReport
)
from ..llm.base import LLMProvider


logger = logging.getLogger(__name__)


class ConsistencyReviewer:
    """全文一致性审查器"""

    def __init__(self, llm_provider: LLMProvider):
        """
        初始化一致性审查器

        Args:
            llm_provider: LLM Provider
        """
        self.llm = llm_provider
        # 增强功能：统计数据
        self.term_stats: Dict[str, Dict] = {}
        self.style_score: float = 100.0
        self.suggestions: List[Dict] = []

    def review(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]],
        article_analysis: Optional[ArticleAnalysis] = None,
        term_tracker: Optional[TermUsageTracker] = None
    ) -> ConsistencyReport:
        """
        执行全文一致性审查

        Args:
            sections: 章节列表
            translations: 翻译结果 {section_id: [translations]}
            article_analysis: 全文分析结果
            term_tracker: 术语使用追踪

        Returns:
            ConsistencyReport: 一致性审查报告
        """
        all_issues = []
        self.suggestions = []
        self.style_score = 100.0
        self.term_stats = {}

        # 1. 术语一致性检查（增强版）
        if article_analysis and term_tracker:
            terminology_issues, term_stats = self._check_terminology_consistency_enhanced(
                sections, translations, article_analysis.terminology, term_tracker
            )
            all_issues.extend(terminology_issues)
            self.term_stats = term_stats
        elif article_analysis:
            # 即使没有term_tracker，也进行基础术语检查
            terminology_issues, term_stats = self._check_terminology_basic(
                sections, translations, article_analysis.terminology
            )
            all_issues.extend(terminology_issues)
            self.term_stats = term_stats

        # 2. 风格一致性检查（增强版）
        style_issues, style_score = self._check_style_consistency_enhanced(sections, translations)
        all_issues.extend(style_issues)
        self.style_score = style_score

        # 3. 交叉引用检查
        reference_issues = self._check_cross_references(sections, translations)
        all_issues.extend(reference_issues)

        # 4. 数字和数据一致性检查
        data_issues = self._check_data_consistency(sections, translations)
        all_issues.extend(data_issues)

        # 5. 新增：标点符号一致性检查
        punctuation_issues = self._check_punctuation_consistency(sections, translations)
        all_issues.extend(punctuation_issues)

        # 6. 新增：专有名词一致性检查
        proper_noun_issues = self._check_proper_nouns(sections, translations)
        all_issues.extend(proper_noun_issues)

        # 生成建议修正列表
        self._generate_suggestions(all_issues, sections, translations)

        # 分类问题
        auto_fixable = [i for i in all_issues if i.auto_fixable]
        manual_review = [i for i in all_issues if not i.auto_fixable]

        # 创建增强版报告
        report = ConsistencyReport(
            is_consistent=len(all_issues) == 0,
            issues=all_issues,
            auto_fixable=auto_fixable,
            manual_review=manual_review
        )

        # 添加增强数据到报告
        report.term_stats = self.term_stats
        report.style_score = self.style_score
        report.suggestions = self.suggestions

        return report

    def auto_fix(
        self,
        translations: Dict[str, List[str]],
        issues: List[ConsistencyIssue]
    ) -> Dict[str, List[str]]:
        """
        自动修正可修复的问题

        Args:
            translations: 翻译结果
            issues: 问题列表

        Returns:
            Dict[str, List[str]]: 修正后的翻译结果
        """
        fixed = {k: v.copy() for k, v in translations.items()}

        for issue in issues:
            if issue.auto_fixable and issue.fix_suggestion:
                section_id = issue.section_id
                para_index = issue.paragraph_index

                if section_id in fixed and 0 <= para_index < len(fixed[section_id]):
                    # 应用修正建议
                    current = fixed[section_id][para_index]
                    # 简单替换（实际应用中可能需要更复杂的逻辑）
                    fixed[section_id][para_index] = issue.fix_suggestion

        return fixed

    def _check_terminology_consistency_enhanced(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]],
        terminology: List[EnhancedTerm],
        term_tracker: TermUsageTracker
    ) -> Tuple[List[ConsistencyIssue], Dict[str, Dict]]:
        """
        增强版术语一致性检查

        返回问题列表和术语使用统计
        """
        issues = []
        term_stats = {}

        # 构建术语到首选翻译的映射
        term_preferred = {}
        for term in terminology:
            if term.translation:
                term_preferred[term.term.lower()] = term.translation

        # 统计每个术语的使用情况
        term_usage = defaultdict(lambda: {"count": 0, "translations": Counter(), "locations": []})

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            section_trans = translations[section_id]

            for para_idx, (para, trans) in enumerate(zip(section.paragraphs, section_trans)):
                source_lower = para.source.lower()

                for term in terminology:
                    term_lower = term.term.lower()
                    if term_lower not in source_lower:
                        continue

                    # 记录术语出现
                    term_usage[term.term]["count"] += 1
                    term_usage[term.term]["locations"].append({
                        "section_id": section_id,
                        "paragraph_index": para_idx
                    })

                    # 检测使用的翻译
                    if term.translation and term.translation in trans:
                        term_usage[term.term]["translations"][term.translation] += 1
                    else:
                        # 尝试检测其他可能的翻译
                        used_trans = term_tracker.used_translations.get(term.term, [])
                        for ut in used_trans:
                            if ut in trans:
                                term_usage[term.term]["translations"][ut] += 1
                                break

        # 分析术语一致性
        for term_name, usage in term_usage.items():
            trans_counts = usage["translations"]
            term_stats[term_name] = {
                "total_count": usage["count"],
                "translations": dict(trans_counts),
                "is_consistent": len(trans_counts) <= 1,
                "preferred": term_preferred.get(term_name.lower())
            }

            # 如果有多种翻译，报告不一致
            if len(trans_counts) > 1:
                most_common = trans_counts.most_common()
                issues.append(ConsistencyIssue(
                    section_id=usage["locations"][0]["section_id"],
                    paragraph_index=usage["locations"][0]["paragraph_index"],
                    issue_type="terminology",
                    description=f"术语 '{term_name}' 有多种翻译: {', '.join([f'{t}({c}次)' for t, c in most_common])}",
                    auto_fixable=True,
                    fix_suggestion=f"建议统一使用 '{most_common[0][0]}'"
                ))

        return issues, term_stats

    def _check_terminology_consistency(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]],
        terminology: List[EnhancedTerm],
        term_tracker: TermUsageTracker
    ) -> List[ConsistencyIssue]:
        """
        检查术语一致性

        检查同一术语在不同位置是否翻译一致
        """
        issues = []

        # 构建术语到首选翻译的映射
        term_preferred = {}
        for term in terminology:
            if term.translation:
                term_preferred[term.term.lower()] = term.translation

        # 检查每个章节的翻译
        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            section_trans = translations[section_id]

            for para_idx, (para, trans) in enumerate(zip(section.paragraphs, section_trans)):
                # 检查原文中的术语
                source_lower = para.source.lower()

                for term in terminology:
                    term_lower = term.term.lower()
                    if term_lower not in source_lower:
                        continue

                    # 检查译文中是否使用了正确的翻译
                    if term.translation and term.translation not in trans:
                        # 检查是否使用了其他翻译
                        used_trans = term_tracker.used_translations.get(term.term, [])
                        if used_trans and used_trans[0] != term.translation:
                            # 使用了不同的翻译，可能是不一致
                            issues.append(ConsistencyIssue(
                                section_id=section_id,
                                paragraph_index=para_idx,
                                issue_type="terminology",
                                description=f"术语 '{term.term}' 的翻译可能不一致。建议使用 '{term.translation}'，但可能使用了 '{used_trans[0]}'",
                                auto_fixable=False,
                                fix_suggestion=None
                            ))

        return issues

    def _check_terminology_basic(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]],
        terminology: List[EnhancedTerm]
    ) -> Tuple[List[ConsistencyIssue], Dict[str, Dict]]:
        """
        基础术语一致性检查（不需要 term_tracker）

        Returns:
            Tuple of (issues, term_stats)
        """
        issues = []
        term_stats = {}
        term_usage = defaultdict(lambda: {"count": 0, "translations": Counter(), "locations": []})

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            section_trans = translations[section_id]

            for para_idx, (para, trans) in enumerate(zip(section.paragraphs, section_trans)):
                source_lower = para.source.lower()

                for term in terminology:
                    term_lower = term.term.lower()
                    if term_lower not in source_lower:
                        continue

                    term_usage[term.term]["count"] += 1
                    term_usage[term.term]["locations"].append({
                        "section_id": section_id,
                        "paragraph_index": para_idx
                    })

                    # 检测翻译
                    if term.translation and term.translation in trans:
                        term_usage[term.term]["translations"][term.translation] += 1

        # 统计结果
        for term_name, usage in term_usage.items():
            trans_counts = usage["translations"]
            term_stats[term_name] = {
                "total_count": usage["count"],
                "translations": dict(trans_counts),
                "is_consistent": len(trans_counts) <= 1
            }

            if len(trans_counts) > 1:
                most_common = trans_counts.most_common()
                issues.append(ConsistencyIssue(
                    section_id=usage["locations"][0]["section_id"],
                    paragraph_index=usage["locations"][0]["paragraph_index"],
                    issue_type="terminology",
                    description=f"术语 '{term_name}' 有多种翻译: {', '.join([f'{t}({c}次)' for t, c in most_common])}",
                    auto_fixable=True,
                    fix_suggestion=f"建议统一使用 '{most_common[0][0]}'"
                ))

        return issues, term_stats

    def _check_style_consistency_enhanced(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> Tuple[List[ConsistencyIssue], float]:
        """
        增强版风格一致性检查

        Returns:
            Tuple of (issues, style_score)
        """
        issues = []
        style_score = 100.0
        deductions = []

        # 人称检查
        first_person_patterns = [r'我们', r'我', r'本文']
        third_person_patterns = [r'该', r'其', r'此']

        first_person_count = 0
        third_person_count = 0
        total_paragraphs = 0

        # 正式程度检查
        formal_patterns = [r'因此', r'故', r'亦', r'予以', r'进行']
        informal_patterns = [r'嘛', r'啊', r'呢', r'吧', r'挺', r'蛮']

        formal_count = 0
        informal_count = 0

        # 句式检查
        long_sentences = 0  # 超长句子
        short_sentences = 0  # 过短句子

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            for para_idx, trans in enumerate(translations[section_id]):
                total_paragraphs += 1

                # 人称检查
                for p in first_person_patterns:
                    first_person_count += len(re.findall(p, trans))
                for p in third_person_patterns:
                    third_person_count += len(re.findall(p, trans))

                # 正式程度检查
                for p in formal_patterns:
                    formal_count += len(re.findall(p, trans))
                for p in informal_patterns:
                    if re.search(p, trans):
                        informal_count += 1
                        issues.append(ConsistencyIssue(
                            section_id=section_id,
                            paragraph_index=para_idx,
                            issue_type="style",
                            description=f"发现口语化表达，可能影响专业性",
                            auto_fixable=False,
                            fix_suggestion=None
                        ))

                # 句子长度检查
                sentences = re.split(r'[。！？]', trans)
                for sent in sentences:
                    if len(sent) > 150:
                        long_sentences += 1
                    elif 0 < len(sent) < 10:
                        short_sentences += 1

        # 计算风格分数
        if first_person_count > 0 and third_person_count > 0:
            ratio = min(first_person_count, third_person_count) / max(first_person_count, third_person_count)
            if ratio > 0.3:  # 混用比例较高
                deductions.append(("人称混用", 10))
                issues.append(ConsistencyIssue(
                    section_id=sections[0].section_id if sections else "",
                    paragraph_index=0,
                    issue_type="style",
                    description=f"人称使用不统一: 第一人称{first_person_count}次, 第三人称{third_person_count}次",
                    auto_fixable=False,
                    fix_suggestion="建议统一使用一种人称表述"
                ))

        if formal_count > 0 and informal_count > 0:
            deductions.append(("正式/口语混用", 5 * informal_count))

        if long_sentences > total_paragraphs * 0.2:
            deductions.append(("过长句子较多", 5))
            issues.append(ConsistencyIssue(
                section_id=sections[0].section_id if sections else "",
                paragraph_index=0,
                issue_type="style",
                description=f"发现{long_sentences}个超长句子（超过150字），建议拆分",
                auto_fixable=False,
                fix_suggestion=None
            ))

        # 计算最终分数
        for reason, points in deductions:
            style_score -= points
            logger.debug(f"Style deduction: {reason} (-{points})")

        style_score = max(0, min(100, style_score))

        return issues, style_score

    def _check_style_consistency(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> List[ConsistencyIssue]:
        """
        检查风格一致性

        检查各章节的语气、正式程度是否统一
        """
        issues = []

        # 简单的风格检查：检查是否混用了不同的人称
        first_person_patterns = [r'\b我们\b', r'\b我\b', r'\b本文\b']
        third_person_patterns = [r'\b该\b', r'\b其\b', r'\b此\b']

        first_person_sections = []
        third_person_sections = []

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            section_text = " ".join(translations[section_id])

            has_first = any(re.search(p, section_text) for p in first_person_patterns)
            has_third = any(re.search(p, section_text) for p in third_person_patterns)

            if has_first:
                first_person_sections.append(section_id)
            if has_third:
                third_person_sections.append(section_id)

        # 如果同时存在第一人称和第三人称，可能存在风格不一致
        if first_person_sections and third_person_sections:
            # 只报告一次
            issues.append(ConsistencyIssue(
                section_id=first_person_sections[0],
                paragraph_index=0,
                issue_type="style",
                description="文章中混用了第一人称（我们/本文）和第三人称表述，建议统一风格",
                auto_fixable=False,
                fix_suggestion=None
            ))

        return issues

    def _check_cross_references(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> List[ConsistencyIssue]:
        """
        检查交叉引用

        检查"如前所述"、"后文将讨论"等引用是否准确
        """
        issues = []

        # 交叉引用模式
        forward_refs = [r'后文', r'下文', r'稍后', r'接下来']
        backward_refs = [r'如前所述', r'前文', r'上文', r'之前提到']

        section_ids = [s.section_id for s in sections]

        for i, section in enumerate(sections):
            section_id = section.section_id
            if section_id not in translations:
                continue

            for para_idx, trans in enumerate(translations[section_id]):
                # 检查前向引用（在最后一个章节不应该有）
                if i == len(sections) - 1:
                    for pattern in forward_refs:
                        if re.search(pattern, trans):
                            issues.append(ConsistencyIssue(
                                section_id=section_id,
                                paragraph_index=para_idx,
                                issue_type="reference",
                                description=f"最后一个章节中出现了前向引用 '{pattern}'，但后面没有更多内容",
                                auto_fixable=False,
                                fix_suggestion=None
                            ))
                            break

                # 检查后向引用（在第一个章节不应该有）
                if i == 0:
                    for pattern in backward_refs:
                        if re.search(pattern, trans):
                            issues.append(ConsistencyIssue(
                                section_id=section_id,
                                paragraph_index=para_idx,
                                issue_type="reference",
                                description=f"第一个章节中出现了后向引用 '{pattern}'，但前面没有相关内容",
                                auto_fixable=False,
                                fix_suggestion=None
                            ))
                            break

        return issues

    def _check_data_consistency(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> List[ConsistencyIssue]:
        """
        检查数字和数据一致性

        确保原文中的数字在译文中保持一致
        """
        issues = []

        # 数字模式
        number_pattern = r'\b\d+(?:\.\d+)?(?:%|billion|million|thousand)?\b'

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            for para_idx, (para, trans) in enumerate(zip(section.paragraphs, translations[section_id])):
                # 提取原文中的数字
                source_numbers = set(re.findall(number_pattern, para.source.lower()))
                # 提取译文中的数字
                trans_numbers = set(re.findall(number_pattern, trans.lower()))

                # 检查是否有数字丢失
                missing = source_numbers - trans_numbers
                if missing:
                    # 过滤掉可能被转换的数字（如 billion -> 亿）
                    significant_missing = [n for n in missing if not any(
                        c in n for c in ['billion', 'million', 'thousand']
                    )]

                    if significant_missing:
                        issues.append(ConsistencyIssue(
                            section_id=section_id,
                            paragraph_index=para_idx,
                            issue_type="data",
                            description=f"译文中可能遗漏了数字: {', '.join(significant_missing[:3])}",
                            auto_fixable=False,
                            fix_suggestion=None
                        ))

        return issues

    def _check_punctuation_consistency(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> List[ConsistencyIssue]:
        """
        检查标点符号一致性

        检查中英文标点混用等问题
        """
        issues = []

        # 中英文标点对照
        chinese_punct = '，。！？；：""''（）'
        english_punct = ',.!?;:"\''

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            for para_idx, trans in enumerate(translations[section_id]):
                # 检查是否混用中英文标点
                has_chinese = any(p in trans for p in chinese_punct)
                has_english = any(p in trans for p in english_punct)

                if has_chinese and has_english:
                    # 检测具体的英文标点
                    english_found = [p for p in english_punct if p in trans]
                    if english_found:
                        issues.append(ConsistencyIssue(
                            section_id=section_id,
                            paragraph_index=para_idx,
                            issue_type="punctuation",
                            description=f"中英文标点混用: 发现英文标点 {', '.join(english_found[:3])}",
                            auto_fixable=True,
                            fix_suggestion="建议统一使用中文标点"
                        ))

        return issues

    def _check_proper_nouns(
        self,
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> List[ConsistencyIssue]:
        """
        检查专有名词一致性

        检查公司名、产品名、人名等的翻译一致性
        """
        issues = []
        proper_noun_usage = defaultdict(lambda: {"translations": Counter(), "locations": []})

        # 常见专有名词模式（英文大写开头的词）
        proper_noun_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'

        for section in sections:
            section_id = section.section_id
            if section_id not in translations:
                continue

            for para_idx, (para, trans) in enumerate(zip(section.paragraphs, translations[section_id])):
                # 从原文中提取专有名词
                proper_nouns = re.findall(proper_noun_pattern, para.source)

                for noun in proper_nouns:
                    if len(noun) < 3:  # 忽略太短的
                        continue

                    proper_noun_usage[noun]["locations"].append({
                        "section_id": section_id,
                        "paragraph_index": para_idx
                    })

                    # 检查译文中是否保留了这个专有名词
                    if noun in trans:
                        proper_noun_usage[noun]["translations"]["保留原文"] += 1
                    else:
                        proper_noun_usage[noun]["translations"]["翻译"] += 1

        # 检查一致性
        for noun, usage in proper_noun_usage.items():
            trans_counts = usage["translations"]
            if len(trans_counts) > 1:
                # 同一专有名词有时保留有时翻译
                issues.append(ConsistencyIssue(
                    section_id=usage["locations"][0]["section_id"],
                    paragraph_index=usage["locations"][0]["paragraph_index"],
                    issue_type="proper_noun",
                    description=f"专有名词 '{noun}' 处理不一致: {dict(trans_counts)}",
                    auto_fixable=False,
                    fix_suggestion="建议统一保留原文或统一翻译"
                ))

        return issues

    def _generate_suggestions(
        self,
        issues: List[ConsistencyIssue],
        sections: List[Section],
        translations: Dict[str, List[str]]
    ) -> None:
        """
        生成建议修正列表
        """
        self.suggestions = []

        # 按优先级排序问题
        priority_order = {
            "terminology": 1,
            "proper_noun": 2,
            "data": 3,
            "punctuation": 4,
            "style": 5,
            "reference": 6
        }

        sorted_issues = sorted(
            issues,
            key=lambda x: priority_order.get(x.issue_type, 99)
        )

        for issue in sorted_issues[:10]:  # 最多10条建议
            suggestion = {
                "issue_type": issue.issue_type,
                "section_id": issue.section_id,
                "paragraph_index": issue.paragraph_index,
                "description": issue.description,
                "action": issue.fix_suggestion if issue.fix_suggestion else "需要人工审核",
                "auto_fixable": issue.auto_fixable,
                "priority": priority_order.get(issue.issue_type, 99)
            }
            self.suggestions.append(suggestion)

    def get_review_report(self, report: ConsistencyReport) -> str:
        """
        生成审查报告

        Args:
            report: 一致性审查报告

        Returns:
            str: 格式化的审查报告
        """
        lines = [
            "=" * 60,
            "全文一致性审查报告",
            "=" * 60,
            "",
            f"一致性状态: {'✅ 通过' if report.is_consistent else '❌ 存在问题'}",
            f"风格评分: {report.style_score:.1f}/100",
            f"问题总数: {len(report.issues)}",
            f"  - 可自动修复: {len(report.auto_fixable)}",
            f"  - 需人工审核: {len(report.manual_review)}",
            "",
        ]

        # 术语统计
        if report.term_stats:
            lines.append("## 术语使用统计")
            lines.append("-" * 40)
            for term, stats in list(report.term_stats.items())[:5]:
                consistent = "✅" if stats.get("is_consistent") else "⚠️"
                lines.append(f"  {consistent} {term}: {stats.get('total_count', 0)}次")
            if len(report.term_stats) > 5:
                lines.append(f"  ... 还有 {len(report.term_stats) - 5} 个术语")
            lines.append("")

        if report.issues:
            # 按类型分组
            by_type = {}
            for issue in report.issues:
                if issue.issue_type not in by_type:
                    by_type[issue.issue_type] = []
                by_type[issue.issue_type].append(issue)

            type_names = {
                "terminology": "术语一致性",
                "style": "风格一致性",
                "reference": "交叉引用",
                "data": "数据一致性",
                "coherence": "逻辑连贯性",
                "punctuation": "标点符号",
                "proper_noun": "专有名词"
            }

            for issue_type, issues in by_type.items():
                type_name = type_names.get(issue_type, issue_type)
                lines.append(f"## {type_name} ({len(issues)} 个问题)")
                lines.append("-" * 40)

                for issue in issues[:5]:  # 每类最多显示5个
                    auto_mark = "🔧" if issue.auto_fixable else "👁"
                    lines.append(f"  {auto_mark} [{issue.section_id}:{issue.paragraph_index}]")
                    lines.append(f"     {issue.description}")

                if len(issues) > 5:
                    lines.append(f"  ... 还有 {len(issues) - 5} 个问题")

                lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


def create_consistency_reviewer(llm_provider: LLMProvider) -> ConsistencyReviewer:
    """
    创建一致性审查器

    Args:
        llm_provider: LLM Provider

    Returns:
        ConsistencyReviewer: 一致性审查器实例
    """
    return ConsistencyReviewer(llm_provider=llm_provider)
