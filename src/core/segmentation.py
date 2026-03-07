"""
Translation Agent - 分段策略模块

实现三层分离架构：
1. 翻译单元（TranslationBlock）- 给AI看的，按H2章节，每2000字切块
2. 确认单元（ConfirmationUnit）- 给用户看的，合并短段落
3. 输出段落（Paragraph）- 最终输出，严格遵循原文
"""

from typing import List, Optional
from dataclasses import dataclass
import re
from ..core.models import Paragraph, Section, ElementType


@dataclass
class TranslationBlock:
    """翻译单元 - 给AI处理的大块文本"""

    id: str  # "block_001"
    section_id: str  # 所属章节ID
    section_title: str  # 章节标题
    paragraphs: List[Paragraph]  # 包含的原始段落

    # 上下文信息
    previous_translation: Optional[str] = None  # 上一个块的译文（最后一段）
    next_preview: Optional[str] = None  # 下一个块的原文预览

    @property
    def source_text(self) -> str:
        """获取完整原文"""
        return "\n\n".join([p.source for p in self.paragraphs])

    @property
    def estimated_chars(self) -> int:
        """估算字符数"""
        return sum(len(p.source) for p in self.paragraphs)

    @property
    def paragraph_ids(self) -> List[str]:
        """获取所有段落ID"""
        return [p.id for p in self.paragraphs]


@dataclass
class ConfirmationUnit:
    """确认单元 - 给用户确认的合并段落"""

    id: str  # "confirm_001"
    merged_paragraph_ids: List[str]  # 合并的段落ID列表
    source: str  # 合并后的原文
    translation: str  # 合并后的译文

    is_merged: bool = False  # 是否是合并段落

    def split_back_to_paragraphs(
        self, original_paragraphs: List[Paragraph]
    ) -> List[Paragraph]:
        """拆分回原始段落（用于最终输出）"""
        para_map = {p.id: p for p in original_paragraphs}
        ordered = [para_map[p_id] for p_id in self.merged_paragraph_ids if p_id in para_map]

        if not self.is_merged or len(ordered) <= 1:
            return ordered

        split_texts = estimate_paragraph_boundaries(
            self.translation,
            original_paragraph_count=len(ordered),
            original_lengths=[len(p.source) for p in ordered],
        )
        for idx, para in enumerate(ordered):
            para.confirmed = split_texts[idx] if idx < len(split_texts) else self.translation
        return ordered


class SegmentationStrategy:
    """分段策略管理器"""

    def __init__(
        self,
        translation_block_size: int = 2000,  # 翻译单元大小（字符）
        confirmation_min_size: int = 150,  # 确认单元最小大小
        confirmation_max_size: int = 400,  # 合并后最大大小
    ):
        self.translation_block_size = translation_block_size
        self.confirmation_min_size = confirmation_min_size
        self.confirmation_max_size = confirmation_max_size

    def create_translation_blocks(
        self, sections: List[Section]
    ) -> List[TranslationBlock]:
        """
        创建翻译单元

        策略：
        1. 按H2章节分组
        2. 每2000字切块（在段落边界切分）
        3. 保留上下文信息
        """
        blocks = []
        block_counter = 1

        for section in sections:
            if not section.paragraphs:
                continue

            # 按章节分组段落
            current_block_paras = []
            current_size = 0

            for i, para in enumerate(section.paragraphs):
                para_size = len(para.source)

                # 检查是否需要切块
                if (
                    current_size + para_size > self.translation_block_size
                    and current_block_paras
                ):
                    # 创建一个块
                    block = TranslationBlock(
                        id=f"block_{block_counter:03d}",
                        section_id=section.section_id,
                        section_title=section.title,
                        paragraphs=current_block_paras.copy(),
                    )
                    blocks.append(block)
                    block_counter += 1

                    # 重置
                    current_block_paras = [para]
                    current_size = para_size
                else:
                    current_block_paras.append(para)
                    current_size += para_size

            # 处理最后一块
            if current_block_paras:
                block = TranslationBlock(
                    id=f"block_{block_counter:03d}",
                    section_id=section.section_id,
                    section_title=section.title,
                    paragraphs=current_block_paras,
                )
                blocks.append(block)
                block_counter += 1

        # 添加上下文信息
        for i, block in enumerate(blocks):
            if i > 0:
                # 获取上一块的最后一段译文
                prev_block = blocks[i - 1]
                if prev_block.paragraphs:
                    last_para = prev_block.paragraphs[-1]
                    if last_para.confirmed:
                        block.previous_translation = last_para.confirmed

            if i < len(blocks) - 1:
                # 获取下一块的第一段原文
                next_block = blocks[i + 1]
                if next_block.paragraphs:
                    first_para = next_block.paragraphs[0]
                    preview = (
                        first_para.source[:200] + "..."
                        if len(first_para.source) > 200
                        else first_para.source
                    )
                    block.next_preview = preview

        return blocks

    def create_confirmation_units(
        self, paragraphs: List[Paragraph]
    ) -> List[ConfirmationUnit]:
        """
        创建确认单元

        策略：
        1. 遵循原文段落标记
        2. 合并短于150字的段落
        3. 合并后不超过400字
        4. 列表项不合并
        """
        units = []
        unit_counter = 1

        i = 0
        while i < len(paragraphs):
            current_para = paragraphs[i]

            # 检查是否应该合并
            should_merge = False
            merge_paras = [current_para]

            if len(current_para.source) < self.confirmation_min_size:
                # 尝试合并
                if current_para.element_type != ElementType.LI:  # 列表项不合并
                    # 向后查找可合并段落
                    j = i + 1
                    merged_size = len(current_para.source)

                    while j < len(paragraphs):
                        next_para = paragraphs[j]
                        next_size = len(next_para.source)

                        # 检查合并条件
                        if (
                            merged_size + next_size <= self.confirmation_max_size
                            and next_para.element_type != ElementType.LI
                        ):
                            merge_paras.append(next_para)
                            merged_size += next_size
                            j += 1
                            should_merge = True

                            # 如果达到足够大小，停止合并
                            if merged_size >= self.confirmation_min_size:
                                break
                        else:
                            break

            # 创建确认单元
            unit = ConfirmationUnit(
                id=f"confirm_{unit_counter:03d}",
                merged_paragraph_ids=[p.id for p in merge_paras],
                source="\n\n".join([p.source for p in merge_paras]),
                translation="\n\n".join(
                    [p.best_translation_text() for p in merge_paras]
                ),
                is_merged=should_merge and len(merge_paras) > 1,
            )
            units.append(unit)
            unit_counter += 1

            # 移动索引
            i += len(merge_paras)

        return units

    def rebuild_output_paragraphs(
        self,
        confirmation_units: List[ConfirmationUnit],
        original_paragraphs: List[Paragraph],
    ) -> List[Paragraph]:
        """
        从确认单元重建输出段落

        策略：
        1. 严格遵循原文分段
        2. 智能拆分合并的译文
        3. 保留所有格式信息
        """
        output_paragraphs = []

        for unit in confirmation_units:
            if not unit.is_merged:
                # 未合并，直接使用
                for p_id in unit.merged_paragraph_ids:
                    para = next((p for p in original_paragraphs if p.id == p_id), None)
                    if para:
                        para.confirmed = unit.translation
                        output_paragraphs.append(para)
            else:
                # 已合并，需要拆分
                split_paras = unit.split_back_to_paragraphs(original_paragraphs)
                output_paragraphs.extend(split_paras)

        return output_paragraphs


# 辅助函数
def estimate_paragraph_boundaries(
    merged_translation: str,
    original_paragraph_count: int,
    original_lengths: Optional[List[int]] = None,
) -> List[str]:
    """
    估算段落边界，将合并的译文拆分回多个段落
    """
    text = (merged_translation or "").strip()
    if original_paragraph_count <= 0:
        return []
    if original_paragraph_count == 1:
        return [text]
    if not text:
        return [""] * original_paragraph_count

    text_len = len(text)
    punct_matches = [m.start() for m in re.finditer(r"[。！？!?；;,.，]", text)]

    def nearest_boundary(target: int, prev: int) -> int:
        if not punct_matches:
            return max(prev + 1, target)
        closest = None
        best_distance = None
        for pos in punct_matches:
            boundary = pos + 1
            if boundary <= prev:
                continue
            distance = abs(boundary - target)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                closest = boundary
        return closest if closest is not None else max(prev + 1, target)

    if original_lengths and len(original_lengths) == original_paragraph_count and sum(original_lengths) > 0:
        total = float(sum(original_lengths))
        ratios = [length / total for length in original_lengths]
    else:
        ratios = [1.0 / original_paragraph_count] * original_paragraph_count

    targets = []
    accumulated = 0.0
    for ratio in ratios[:-1]:
        accumulated += ratio
        targets.append(int(round(text_len * accumulated)))

    boundaries: List[int] = []
    prev = 0
    for target in targets:
        boundary = nearest_boundary(target, prev)
        boundary = max(prev + 1, min(boundary, text_len - (original_paragraph_count - len(boundaries) - 1)))
        boundaries.append(boundary)
        prev = boundary

    segments: List[str] = []
    start = 0
    for boundary in boundaries:
        segments.append(text[start:boundary].strip())
        start = boundary
    segments.append(text[start:].strip())

    # 保底处理：确保长度对齐且不出现空槽位
    while len(segments) < original_paragraph_count:
        segments.append("")
    if len(segments) > original_paragraph_count:
        head = segments[: original_paragraph_count - 1]
        tail = "".join(segments[original_paragraph_count - 1 :]).strip()
        segments = head + [tail]

    for i in range(len(segments)):
        if segments[i]:
            continue
        # 空段回退为一个空格，避免下游把空字符串误判为未翻译
        segments[i] = " "
    return segments
