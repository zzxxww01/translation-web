"""
Translation Service - 分段优化服务

提供翻译流程中的分段管理和优化功能
"""

from typing import List, Optional, Dict, Any
from ..core.models import Section, Paragraph, ProjectMeta
from ..core.segmentation import SegmentationStrategy, TranslationBlock, ConfirmationUnit
from ..agents.translation import TranslationAgent, TranslationContext


class SegmentationService:
    """分段优化服务"""

    def __init__(
        self,
        translation_agent: TranslationAgent,
        strategy: Optional[SegmentationStrategy] = None,
    ):
        self.translation_agent = translation_agent
        self.strategy = strategy or SegmentationStrategy()

    async def translate_by_blocks(
        self,
        sections: List[Section],
        context: TranslationContext,
        model_name: str = "pro",
    ) -> List[Section]:
        """
        按翻译单元批量翻译

        流程：
        1. 创建翻译单元（TranslationBlock）
        2. 逐块翻译
        3. 将译文分配回原始段落
        4. 创建确认单元供用户确认

        Args:
            sections: 章节列表
            context: 翻译上下文
            model_name: 模型名称

        Returns:
            翻译后的章节列表
        """
        # Step 1: 创建翻译单元
        translation_blocks = self.strategy.create_translation_blocks(sections)

        # Step 2: 逐块翻译
        for block in translation_blocks:
            # 更新上下文
            block_context = self._build_block_context(block, context)

            # 逐段翻译（使用现有逻辑）
            for para in block.paragraphs:
                block_context.source_text = para.source
                translation = self.translation_agent.translate_paragraph(
                    para, block_context, model_name
                )
                # 翻译结果已自动记录到段落中

        return sections

    def _build_block_context(
        self, block: TranslationBlock, base_context: TranslationContext
    ) -> TranslationContext:
        """构建翻译块的上下文"""
        # 复制基础上下文
        block_context = TranslationContext(
            glossary=base_context.glossary,
            style_guide=base_context.style_guide,
            article_title=base_context.article_title,
            current_section_title=block.section_title,
            heading_chain=base_context.heading_chain,
        )

        # 添加上文参考
        if block.previous_translation:
            # 模拟上一段的源文和译文
            block_context.previous_paragraphs = [("...", block.previous_translation)]

        # 添加下文预览
        if block.next_preview:
            block_context.next_preview = [block.next_preview]

        return block_context

    def create_confirmation_units(
        self, sections: List[Section]
    ) -> List[ConfirmationUnit]:
        """
        为已翻译的章节创建确认单元

        Args:
            sections: 已翻译的章节列表

        Returns:
            确认单元列表
        """
        all_paragraphs = []
        for section in sections:
            all_paragraphs.extend(section.paragraphs)

        return self.strategy.create_confirmation_units(all_paragraphs)

    def apply_user_confirmations(
        self, confirmation_units: List[ConfirmationUnit], sections: List[Section]
    ) -> List[Section]:
        """
        应用用户确认，生成最终输出

        Args:
            confirmation_units: 用户确认后的单元
            sections: 原始章节

        Returns:
            更新后的章节（段落包含confirmed字段）
        """
        # 收集所有段落
        all_paragraphs = []
        for section in sections:
            all_paragraphs.extend(section.paragraphs)

        # 重建输出段落
        output_paragraphs = self.strategy.rebuild_output_paragraphs(
            confirmation_units, all_paragraphs
        )

        # 更新章节
        for section in sections:
            for i, para in enumerate(section.paragraphs):
                matching_output = next(
                    (p for p in output_paragraphs if p.id == para.id), None
                )
                if matching_output:
                    section.paragraphs[i] = matching_output

        return sections


class TranslationOrchestrator:
    """翻译编排器 - 协调整个翻译流程"""

    def __init__(
        self,
        translation_agent: TranslationAgent,
        segmentation_service: SegmentationService,
    ):
        self.translation_agent = translation_agent
        self.segmentation_service = segmentation_service

    async def translate_project(
        self,
        project_meta: ProjectMeta,
        sections: List[Section],
        use_block_translation: bool = True,
    ) -> Dict[str, Any]:
        """
        翻译整个项目

        Args:
            project_meta: 项目元数据
            sections: 章节列表
            use_block_translation: 是否使用块级翻译（推荐）

        Returns:
            {
                "sections": 翻译后的章节,
                "confirmation_units": 确认单元列表,
                "stats": 统计信息
            }
        """
        # 构建基础上下文
        glossary = getattr(project_meta, "glossary", None)
        style_guide = getattr(project_meta, "style_guide", None)
        context = TranslationContext(
            glossary=glossary,
            style_guide=style_guide,
            article_title=project_meta.title,
        )

        # 翻译
        if use_block_translation:
            # 使用块级翻译（推荐）
            translated_sections = await self.segmentation_service.translate_by_blocks(
                sections, context
            )
        else:
            # 使用逐段翻译（旧方式）
            translated_sections = await self._translate_paragraph_by_paragraph(
                sections, context
            )

        # 创建确认单元
        confirmation_units = self.segmentation_service.create_confirmation_units(
            translated_sections
        )

        # 统计信息
        stats = {
            "total_sections": len(sections),
            "total_paragraphs": sum(len(s.paragraphs) for s in sections),
            "total_confirmation_units": len(confirmation_units),
            "merged_units": sum(1 for u in confirmation_units if u.is_merged),
        }

        return {
            "sections": translated_sections,
            "confirmation_units": confirmation_units,
            "stats": stats,
        }

    async def _translate_paragraph_by_paragraph(
        self, sections: List[Section], context: TranslationContext
    ) -> List[Section]:
        """逐段翻译（旧方式，保留向后兼容）"""
        for section in sections:
            for para in section.paragraphs:
                context.source_text = para.source
                context.current_section_title = section.title

                self.translation_agent.translate_paragraph(para, context)

        return sections
