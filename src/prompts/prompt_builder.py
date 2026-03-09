"""Translation prompt builder."""

from typing import Any, Dict, List, Optional, Tuple

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
        article_theme: Optional[str] = None,
        article_structure: Optional[str] = None,
        current_section_title: Optional[str] = None,
        heading_chain: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        translation_voice: Optional[str] = None,
        article_challenges: Optional[List[Any]] = None,
        style_guide: Optional[Dict] = None,
        section_context: Optional[Dict] = None,
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
            article_theme=article_theme,
            article_structure=article_structure,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            target_audience=target_audience,
            translation_voice=translation_voice,
            article_challenges=article_challenges,
            style_guide=style_guide,
            section_context=section_context,
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
            first_occurrence_note = term.get("first_occurrence_note", False)

            if strategy == "preserve":
                lines.append(f"- {original} -> 保留英文")
            elif strategy == "first_annotate" or first_occurrence_note:
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
        article_theme: Optional[str] = None,
        article_structure: Optional[str] = None,
        current_section_title: Optional[str] = None,
        heading_chain: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        translation_voice: Optional[str] = None,
        article_challenges: Optional[List[Any]] = None,
        style_guide: Optional[Dict] = None,
        section_context: Optional[Dict] = None,
        previous_paragraphs: Optional[List[Tuple[str, str]]] = None,
        next_preview: Optional[List[str]] = None,
    ) -> str:
        sections: List[str] = []

        if article_title or current_section_title or article_theme or target_audience:
            context_lines = ["## 上下文信息"]
            if article_title:
                context_lines.append(f"文章标题：{article_title}")
            if article_theme:
                context_lines.append(f"文章主线：{article_theme}")
            if current_section_title:
                context_lines.append(f"当前章节：{current_section_title}")
            if heading_chain:
                context_lines.append(f"章节层级：{' -> '.join(heading_chain)}")
            if target_audience:
                context_lines.append(f"目标读者：{target_audience}")
            sections.append("\n".join(context_lines))

        if article_structure:
            sections.append("## 结构提示\n" + article_structure)

        if section_context:
            section_lines = ["## 本章角色"]
            role = section_context.get("role")
            if role:
                section_lines.append(f"章节职责：{role}")
            relation_to_previous = section_context.get("relation_to_previous")
            if relation_to_previous:
                section_lines.append(f"与前文关系：{relation_to_previous}")
            key_points = section_context.get("key_points") or []
            if key_points:
                section_lines.append("关键点：")
                section_lines.extend(f"- {point}" for point in key_points[:5])
            translation_notes = section_context.get("translation_notes") or []
            if translation_notes:
                section_lines.append("翻译注意：")
                section_lines.extend(f"- {note}" for note in translation_notes[:5])
            if len(section_lines) > 1:
                sections.append("\n".join(section_lines))

        style_notes = []
        if translation_voice:
            style_notes.append(f"建议中文声线：{translation_voice}")
        if style_guide:
            tone = style_guide.get("tone")
            if tone:
                style_notes.append(f"语气：{tone}")
            notes = style_guide.get("notes") or []
            style_notes.extend(str(note) for note in notes[:5])
        if style_notes:
            sections.append("## 风格约束\n" + "\n".join(f"- {item}" for item in style_notes))

        if article_challenges:
            challenge_lines = ["## 翻译风险提示"]
            for challenge in article_challenges[:5]:
                if isinstance(challenge, dict):
                    location = str(challenge.get("location", "")).strip()
                    issue = str(challenge.get("issue", "")).strip()
                    suggestion = str(challenge.get("suggestion", "")).strip()
                    line = issue
                    if location:
                        line = f"[{location}] {line}"
                    if suggestion:
                        line = f"{line}；建议：{suggestion}"
                    if line:
                        challenge_lines.append(f"- {line}")
                else:
                    text = str(challenge).strip()
                    if text:
                        challenge_lines.append(f"- {text}")
            if len(challenge_lines) > 1:
                sections.append("\n".join(challenge_lines))

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
            preview_lines = ["## 下文预览（避免本段与后文断裂）"]
            for preview in next_preview[:2]:
                preview_lines.append(f"- {preview[:160]}")
            sections.append("\n".join(preview_lines))

        return "\n\n".join(sections) if sections else ""


_default_builder = None


def get_prompt_builder(style: str = "simplified") -> TranslationPromptBuilder:
    """Get a singleton prompt builder by style."""
    global _default_builder
    if _default_builder is None or _default_builder.prompt_style != style:
        _default_builder = TranslationPromptBuilder(prompt_style=style)
    return _default_builder
