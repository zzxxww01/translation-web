"""翻译Prompt模板构建器

提供简化版和增强版两种Prompt策略
"""

from typing import Dict, Any, List, Tuple, Optional
from ..core.models import Glossary, TranslationRule


class TranslationPromptBuilder:
    """翻译Prompt构建器"""

    def __init__(self, prompt_style: str = "simplified"):
        """
        初始化

        Args:
            prompt_style: Prompt风格 - "simplified" 或 "original"
        """
        self.prompt_style = prompt_style

        # 加载Prompt模板
        import os

        prompts_dir = os.path.dirname(__file__)

        if prompt_style == "simplified":
            template_file = os.path.join(prompts_dir, "translation_simplified.txt")
        elif prompt_style == "post":
            template_file = os.path.join(prompts_dir, "post_translation.txt")
        else:
            template_file = os.path.join(prompts_dir, "translation.txt")

        with open(template_file, "r", encoding="utf-8") as f:
            self.template = f.read()

    def build_prompt(
        self,
        source_text: str,
        glossary: Optional[List[Dict]] = None,
        previous_paragraphs: Optional[List[Tuple[str, str]]] = None,
        next_preview: Optional[List[str]] = None,
        article_title: Optional[str] = None,
        current_section_title: Optional[str] = None,
        heading_chain: Optional[List[str]] = None,
        learned_rules: Optional[List[TranslationRule]] = None,
        **kwargs,
    ) -> str:
        """
        构建翻译Prompt

        Args:
            source_text: 待翻译文本
            glossary: 术语表（已筛选的相关术语）
            previous_paragraphs: 上文参考 [(源文, 译文), ...]
            next_preview: 下文预览 [源文, ...]
            article_title: 文章标题
            current_section_title: 当前章节标题
            heading_chain: 标题链 ["# 主标题", "## 二级标题", ...]
            learned_rules: 自学习翻译规则列表
            **kwargs: 其他上下文参数

        Returns:
            完整的Prompt字符串
        """
        dynamic_sections = []

        # 1. 术语表部分
        if glossary:
            glossary_text = self._build_glossary_section(glossary)
            dynamic_sections.append(glossary_text)

        # 2. 历史纠错规则（术语表之后、上下文之前）
        if learned_rules:
            rules_text = self._build_rules_section(learned_rules)
            if rules_text:
                dynamic_sections.append(rules_text)

        # 3. 上下文部分
        context_text = self._build_context_section(
            article_title=article_title,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
        )
        if context_text:
            dynamic_sections.append(context_text)

        # 组装完整Prompt
        dynamic_sections_text = "\n\n".join(dynamic_sections)

        prompt = self.template.format(
            text=source_text, dynamic_sections=dynamic_sections_text
        )

        return prompt

    def _build_glossary_section(self, glossary: List[Dict]) -> str:
        """构建术语表部分"""
        if not glossary:
            return ""

        lines = ["## 术语表（请严格遵循）"]

        for term in glossary[:20]:  # 最多20个术语
            original = term.get("original", "")
            translation = term.get("translation", "")
            strategy = term.get("strategy", "translate")
            note = term.get("note", "")

            if strategy == "preserve":
                lines.append(f"- {original} → 保留英文")
            elif strategy == "first_annotate":
                lines.append(f"- {original} → {translation}（首次标注，后续用中文）")
            else:
                if note:
                    lines.append(f"- {original} → {translation}（{note}）")
                else:
                    lines.append(f"- {original} → {translation}")

        return "\n".join(lines)

    def _build_rules_section(self, rules: List[TranslationRule]) -> str:
        """
        构建历史纠错规则部分

        Token 预算控制：最多 5 条规则，总计 ≤150 字符
        """
        if not rules:
            return ""

        lines = ["## 历史纠错（严格遵循）"]
        total_chars = 0
        max_chars = 150

        for rule in rules[:5]:
            line = f'- ❌ "{rule.wrong}" → ✅ "{rule.right}"（{rule.instruction}）'
            total_chars += len(line)
            if total_chars > max_chars:
                break
            lines.append(line)

        return "\n".join(lines) if len(lines) > 1 else ""

    def _build_context_section(
        self,
        article_title: Optional[str] = None,
        current_section_title: Optional[str] = None,
        heading_chain: Optional[List[str]] = None,
        previous_paragraphs: Optional[List[Tuple[str, str]]] = None,
        next_preview: Optional[List[str]] = None,
    ) -> str:
        """构建上下文部分"""
        sections = []

        # 文章级上下文
        if article_title or current_section_title:
            context_lines = ["## 上下文信息"]
            if article_title:
                context_lines.append(f"文章标题：《{article_title}》")
            if current_section_title:
                context_lines.append(f"当前章节：{current_section_title}")
            if heading_chain and len(heading_chain) > 0:
                context_lines.append(f"章节层级：{' → '.join(heading_chain)}")
            sections.append("\n".join(context_lines))

        # 上文参考
        if previous_paragraphs and len(previous_paragraphs) > 0:
            prev_lines = ["## 上文参考（保持风格一致）"]

            # 只显示最近2段
            for src, trans in previous_paragraphs[-2:]:
                # 截断过长的文本
                src_short = src[:100] + "..." if len(src) > 100 else src
                trans_short = trans[:100] + "..." if len(trans) > 100 else trans
                prev_lines.append(f"原文：{src_short}")
                prev_lines.append(f"译文：{trans_short}")
                prev_lines.append("")

            sections.append("\n".join(prev_lines))

        # 下文预览（可选，根据需要）
        # if next_preview and len(next_preview) > 0:
        #     next_lines = ["## 下文预览"]
        #     for src in next_preview[:2]:
        #         src_short = src[:100] + "..." if len(src) > 100 else src
        #         next_lines.append(f"- {src_short}")
        #     sections.append("\n".join(next_lines))

        return "\n\n".join(sections) if sections else ""


# 全局实例（可配置）
_default_builder = None


def get_prompt_builder(style: str = "simplified") -> TranslationPromptBuilder:
    """获取Prompt构建器"""
    global _default_builder
    if _default_builder is None or _default_builder.prompt_style != style:
        _default_builder = TranslationPromptBuilder(prompt_style=style)
    return _default_builder
