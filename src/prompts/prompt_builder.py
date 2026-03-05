"""Translation prompt builder."""

from typing import Dict, List, Optional, Tuple

from ..core.models import TranslationRule


class TranslationPromptBuilder:
    """Build full translation prompts from source text and optional context blocks."""

    def __init__(self, prompt_style: str = "simplified"):
        self.prompt_style = prompt_style

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
        instruction: Optional[str] = None,
        previous_translation: Optional[str] = None,
        **_kwargs,
    ) -> str:
        dynamic_sections: List[str] = []

        if glossary:
            glossary_text = self._build_glossary_section(glossary)
            if glossary_text:
                dynamic_sections.append(glossary_text)

        if learned_rules:
            rules_text = self._build_rules_section(learned_rules)
            if rules_text:
                dynamic_sections.append(rules_text)

        retranslate_text = self._build_retranslation_section(
            previous_translation=previous_translation,
            instruction=instruction,
        )
        if retranslate_text:
            dynamic_sections.append(retranslate_text)

        context_text = self._build_context_section(
            article_title=article_title,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
        )
        if context_text:
            dynamic_sections.append(context_text)

        return self.template.format(
            text=source_text,
            dynamic_sections="\n\n".join(dynamic_sections),
        )

    def _build_glossary_section(self, glossary: List[Dict]) -> str:
        if not glossary:
            return ""

        lines = ["## 术语表（请严格遵循）"]
        for term in glossary[:20]:
            original = term.get("original", "")
            translation = term.get("translation", "")
            strategy = term.get("strategy", "translate")
            note = term.get("note", "")

            if strategy == "preserve":
                lines.append(f"- {original} -> 保留英文")
            elif strategy == "first_annotate":
                lines.append(f"- {original} -> {translation}（首次标注，后续用中文）")
            elif note:
                lines.append(f"- {original} -> {translation}（{note}）")
            else:
                lines.append(f"- {original} -> {translation}")

        return "\n".join(lines)

    def _build_rules_section(self, rules: List[TranslationRule]) -> str:
        if not rules:
            return ""

        lines = ["## 历史纠错（严格遵循）"]
        total_chars = 0
        max_chars = 150

        for rule in rules[:5]:
            line = f'- ❌ "{rule.wrong}" -> ✅ "{rule.right}"（{rule.instruction}）'
            total_chars += len(line)
            if total_chars > max_chars:
                break
            lines.append(line)

        return "\n".join(lines) if len(lines) > 1 else ""

    def _build_retranslation_section(
        self,
        previous_translation: Optional[str] = None,
        instruction: Optional[str] = None,
    ) -> str:
        normalized_instruction = (instruction or "").strip()
        normalized_previous = (previous_translation or "").strip()
        if not normalized_instruction and not normalized_previous:
            return ""

        lines = ["## 重译任务（仅本次生效）"]

        if normalized_previous:
            preview = (
                normalized_previous[:600] + "..."
                if len(normalized_previous) > 600
                else normalized_previous
            )
            lines.append("上一版译文（用于对照改写）：")
            lines.append(preview)

        if normalized_instruction:
            lines.append("")
            lines.append("本次重译要求：")
            lines.append(normalized_instruction)

        lines.append("")
        lines.append("说明：基于原文与上下文重写完整译文，不要偏离原意。")
        return "\n".join(lines)

    def _build_context_section(
        self,
        article_title: Optional[str] = None,
        current_section_title: Optional[str] = None,
        heading_chain: Optional[List[str]] = None,
        previous_paragraphs: Optional[List[Tuple[str, str]]] = None,
        next_preview: Optional[List[str]] = None,
    ) -> str:
        sections: List[str] = []

        if article_title or current_section_title:
            context_lines = ["## 上下文信息"]
            if article_title:
                context_lines.append(f"文章标题：{article_title}")
            if current_section_title:
                context_lines.append(f"当前章节：{current_section_title}")
            if heading_chain:
                context_lines.append(f"章节层级：{' -> '.join(heading_chain)}")
            sections.append("\n".join(context_lines))

        if previous_paragraphs:
            prev_lines = ["## 上文参考（保持风格一致）"]
            for src, trans in previous_paragraphs[-2:]:
                src_short = src[:100] + "..." if len(src) > 100 else src
                trans_short = trans[:100] + "..." if len(trans) > 100 else trans
                prev_lines.append(f"原文：{src_short}")
                prev_lines.append(f"译文：{trans_short}")
                prev_lines.append("")
            sections.append("\n".join(prev_lines))

        if next_preview:
            _ = next_preview  # reserved for future use

        return "\n\n".join(sections) if sections else ""


_default_builder = None


def get_prompt_builder(style: str = "simplified") -> TranslationPromptBuilder:
    """Get a singleton prompt builder by style."""
    global _default_builder
    if _default_builder is None or _default_builder.prompt_style != style:
        _default_builder = TranslationPromptBuilder(prompt_style=style)
    return _default_builder
