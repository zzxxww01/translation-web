"""
Translation Agent - Smart Sampler

智能采样器（方案 C）

用于长文档的智能采样，确保所有章节都被覆盖，
同时识别术语密集段落进行重点采样。

采样策略：
1. 每章首段 (完整)
2. 每章中段 (完整)
3. 每章末段 (完整)
4. 术语密集段 (启发式检测: 大写词、专有名词比例)
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from ..core.models import Section, Paragraph


@dataclass
class SampledParagraph:
    """采样的段落"""
    section_id: str
    section_title: str
    paragraph_index: int
    text: str
    sample_reason: str  # "first", "middle", "last", "term_dense"


@dataclass
class SamplingResult:
    """采样结果"""
    sampled_paragraphs: List[SampledParagraph]
    total_characters: int
    coverage_stats: Dict[str, int]  # section_id -> sampled_count


class SmartSampler:
    """智能采样器"""

    def __init__(
        self,
        max_total_chars: int = 30000,
        term_density_threshold: float = 0.15,
        min_paragraph_length: int = 100
    ):
        """
        初始化智能采样器

        Args:
            max_total_chars: 最大采样总字符数
            term_density_threshold: 术语密度阈值（专有名词比例）
            min_paragraph_length: 最小段落长度（过短的段落不单独采样）
        """
        self.max_total_chars = max_total_chars
        self.term_density_threshold = term_density_threshold
        self.min_paragraph_length = min_paragraph_length

    def sample_for_deep_analysis(
        self,
        sections: List[Section],
        include_term_dense: bool = True
    ) -> SamplingResult:
        """
        为深度分析采样文本

        确保每个章节都被采样，同时控制总字符数

        Args:
            sections: 章节列表
            include_term_dense: 是否包含术语密集段落

        Returns:
            SamplingResult: 采样结果
        """
        sampled_paragraphs: List[SampledParagraph] = []
        total_chars = 0
        coverage_stats: Dict[str, int] = {}

        # 计算每章节的基础采样配额
        num_sections = len(sections)
        if num_sections == 0:
            return SamplingResult([], 0, {})

        base_quota_per_section = self.max_total_chars // num_sections

        for section in sections:
            section_samples = []
            section_chars = 0
            paragraphs = section.paragraphs

            if not paragraphs:
                coverage_stats[section.section_id] = 0
                continue

            # 首段/中段/末段按**槽位**均分本章配额，装不下就截断而不是整段丢弃。
            #
            # 此前首段无条件全文纳入且不受配额约束，中段/末段再做「放得下才要」的
            # 全有或全无判断。长文里每章配额只有几十到几百字符，而首段动辄数百字符，
            # 于是首段一进来余量就是负数，四路采样永远退化成只取首段——实测 16 篇
            # 语料中 9 篇如此，最长的一篇 25 章全是 first。本章的展开与收束因此
            # 从不进入分析视野，而那正是论证与数据最密集的位置。
            slots = [(0, "first")]
            if len(paragraphs) >= 3:
                slots.append((len(paragraphs) // 2, "middle"))
            if len(paragraphs) >= 2:
                slots.append((len(paragraphs) - 1, "last"))

            slot_quota = max(
                self.MIN_USEFUL_SNIPPET_CHARS,
                base_quota_per_section // len(slots),
            )
            for index, reason in slots:
                sample = self._sample_paragraph(section, index, reason)
                # 允许结转前面槽位没用完的额度，短首段不会白白浪费配额
                allowance = max(
                    slot_quota,
                    base_quota_per_section - section_chars,
                )
                taken = self._fit_into_quota(sample, allowance)
                if taken:
                    section_samples.append(taken)
                    section_chars += len(taken.text)

            # 4. 检测并采样术语密集段落
            if include_term_dense:
                term_dense_samples = self._find_term_dense_paragraphs(
                    section,
                    already_sampled=[s.paragraph_index for s in section_samples],
                    remaining_quota=base_quota_per_section - section_chars
                )
                section_samples.extend(term_dense_samples)
                section_chars += sum(len(s.text) for s in term_dense_samples)

            # 添加到总采样中
            sampled_paragraphs.extend(section_samples)
            total_chars += section_chars
            coverage_stats[section.section_id] = len(section_samples)

        return SamplingResult(
            sampled_paragraphs=sampled_paragraphs,
            total_characters=total_chars,
            coverage_stats=coverage_stats
        )

    def sample_for_section_roles(
        self,
        sections: List[Section]
    ) -> Dict[str, str]:
        """
        为章节角色分析采样（增强版）

        每章节采样: 首段 + 中段 + 末段 摘要

        Args:
            sections: 章节列表

        Returns:
            Dict[str, str]: section_id -> 章节摘要文本
        """
        section_summaries: Dict[str, str] = {}

        for section in sections:
            paragraphs = section.paragraphs
            if not paragraphs:
                section_summaries[section.section_id] = ""
                continue

            summary_parts = []

            # 首段 (完整或前 500 字符)
            if paragraphs:
                first_text = paragraphs[0].source[:500]
                summary_parts.append(f"[首段] {first_text}")

            # 中段
            if len(paragraphs) >= 3:
                mid_index = len(paragraphs) // 2
                mid_text = paragraphs[mid_index].source[:500]
                summary_parts.append(f"[中段] {mid_text}")

            # 末段
            if len(paragraphs) >= 2:
                last_text = paragraphs[-1].source[:500]
                summary_parts.append(f"[末段] {last_text}")

            section_summaries[section.section_id] = "\n".join(summary_parts)

        return section_summaries

    def _sample_paragraph(
        self,
        section: Section,
        index: int,
        reason: str
    ) -> Optional[SampledParagraph]:
        """采样单个段落"""
        if index >= len(section.paragraphs):
            return None

        paragraph = section.paragraphs[index]
        text = paragraph.source

        # 跳过过短的段落
        if len(text) < self.min_paragraph_length and reason not in ("first", "last"):
            return None

        return SampledParagraph(
            section_id=section.section_id,
            section_title=section.title,
            paragraph_index=index,
            text=text,
            sample_reason=reason
        )

    # 截断后的片段短于这个长度就没有分析价值，宁可不取。
    MIN_USEFUL_SNIPPET_CHARS = 80

    def _fit_into_quota(
        self,
        sample: Optional[SampledParagraph],
        remaining_quota: int
    ) -> Optional[SampledParagraph]:
        """把采样片段裁到剩余配额内；装不下有意义的片段时返回 None。"""
        if sample is None or remaining_quota <= 0:
            return None
        if len(sample.text) <= remaining_quota:
            return sample
        if remaining_quota < self.MIN_USEFUL_SNIPPET_CHARS:
            return None

        truncated = sample.text[:remaining_quota].rstrip()
        if not truncated:
            return None
        return SampledParagraph(
            section_id=sample.section_id,
            section_title=sample.section_title,
            paragraph_index=sample.paragraph_index,
            text=truncated + "…",
            sample_reason=sample.sample_reason,
        )

    def _find_term_dense_paragraphs(
        self,
        section: Section,
        already_sampled: List[int],
        remaining_quota: int
    ) -> List[SampledParagraph]:
        """
        找出术语密集的段落

        使用启发式检测：
        - 大写单词比例
        - 专有名词模式（CamelCase, 缩写词）
        - 技术术语模式

        Args:
            section: 章节
            already_sampled: 已采样的段落索引
            remaining_quota: 剩余字符配额

        Returns:
            List[SampledParagraph]: 术语密集段落列表
        """
        results = []
        used_chars = 0

        # 计算每个段落的术语密度
        density_scores: List[Tuple[int, float]] = []

        for i, para in enumerate(section.paragraphs):
            if i in already_sampled:
                continue

            density = self._calculate_term_density(para.source)
            if density >= self.term_density_threshold:
                density_scores.append((i, density))

        # 按密度排序，优先采样高密度段落
        density_scores.sort(key=lambda x: x[1], reverse=True)

        for idx, density in density_scores:
            para = section.paragraphs[idx]
            if used_chars + len(para.source) > remaining_quota:
                break

            results.append(SampledParagraph(
                section_id=section.section_id,
                section_title=section.title,
                paragraph_index=idx,
                text=para.source,
                sample_reason="term_dense"
            ))
            used_chars += len(para.source)

        return results

    def _calculate_term_density(self, text: str) -> float:
        """
        计算文本的术语密度

        Args:
            text: 文本内容

        Returns:
            float: 术语密度 (0-1)
        """
        if not text:
            return 0.0

        words = text.split()
        if len(words) < 5:
            return 0.0

        term_indicators = 0

        for word in words:
            # 检测大写缩写词 (2-6 个大写字母)
            if re.match(r'^[A-Z]{2,6}$', word):
                term_indicators += 2

            # 检测 CamelCase
            elif re.match(r'^[A-Z][a-z]+[A-Z]', word):
                term_indicators += 1.5

            # 检测技术术语模式（带数字的词，如 "3nm", "EUV"）
            elif re.match(r'^\d+[a-zA-Z]+$|^[a-zA-Z]+\d+', word):
                term_indicators += 1.5

            # 检测首字母大写的专有名词
            elif re.match(r'^[A-Z][a-z]+$', word):
                term_indicators += 0.5

        return term_indicators / len(words)

    def build_sampled_text(
        self,
        sampling_result: SamplingResult,
        include_section_headers: bool = True
    ) -> str:
        """
        将采样结果构建为文本

        Args:
            sampling_result: 采样结果
            include_section_headers: 是否包含章节标题

        Returns:
            str: 构建的采样文本
        """
        lines = []
        current_section = None

        for sample in sampling_result.sampled_paragraphs:
            # 添加章节标题
            if include_section_headers and sample.section_id != current_section:
                if current_section is not None:
                    lines.append("")  # 空行分隔
                lines.append(f"## {sample.section_title}")
                current_section = sample.section_id

            # 添加段落文本（带采样原因标记）
            lines.append(sample.text)

        return "\n".join(lines)


def create_smart_sampler(
    max_total_chars: int = 30000,
    term_density_threshold: float = 0.15
) -> SmartSampler:
    """
    创建智能采样器

    Args:
        max_total_chars: 最大采样总字符数
        term_density_threshold: 术语密度阈值

    Returns:
        SmartSampler: 智能采样器实例
    """
    return SmartSampler(
        max_total_chars=max_total_chars,
        term_density_threshold=term_density_threshold
    )
