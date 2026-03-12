"""Translation prompt builder for long-form paragraph translation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.constants import (
    MAX_ARTICLE_CHALLENGES_IN_PROMPT,
    MAX_FORMAT_TOKENS_IN_PROMPT,
    MAX_HEADING_CHAIN_IN_PROMPT,
    MAX_SECTION_KEY_POINTS_IN_PROMPT,
    MAX_SECTION_NOTES_IN_PROMPT,
    MAX_STYLE_NOTES_IN_PROMPT,
)
from src.core.glossary_prompt import render_glossary_prompt_block
from src.core.longform_context import build_article_challenge_payload, limit_non_empty_strings
from . import get_prompt_manager


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")


def _truncate_by_sentence(text: str, max_chars: int = 120) -> str:
    """Truncate text by sentence while keeping the start and end when possible."""
    if len(text) <= max_chars:
        return text

    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    if len(sentences) <= 1:
        return text[:max_chars] + "……"

    last = sentences[-1]
    result_parts: List[str] = []
    used = len(last)

    for sentence in sentences[:-1]:
        if used + len(sentence) + 2 > max_chars:
            break
        result_parts.append(sentence)
        used += len(sentence) + 1

    if result_parts:
        return " ".join(result_parts) + " …… " + last
    return sentences[0][: max_chars - len(last) - 4] + " …… " + last


TRANSLATION_TEMPLATE_NAME = "longform/translation/paragraph_translate.v2"
RETRANSLATION_TEMPLATE_NAME = "longform/translation/paragraph_retranslate.v2"

STYLE_CONFIG: Dict[str, Dict[str, str]] = {
    "original": {"profile": "standard"},
    "simplified": {"profile": "lean"},
}


class TranslationPromptBuilder:
    """Build long-form translation prompts from source text and runtime context."""

    def __init__(self, prompt_style: str = "simplified"):
        style_key = (prompt_style or "simplified").strip().lower()
        if style_key not in STYLE_CONFIG:
            style_key = "simplified"

        config = STYLE_CONFIG[style_key]
        self.prompt_style = style_key
        self.translation_profile = config["profile"]
        self.prompt_manager = get_prompt_manager()

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
        learned_rules: Optional[List[str]] = None,
        instruction: Optional[str] = None,
        previous_translation: Optional[str] = None,
        format_tokens: Optional[List[Dict[str, Any]]] = None,
        term_usage: Optional[Dict[str, List[str]]] = None,
        **_kwargs,
    ) -> str:
        profile_text = self._build_profile_section()
        dynamic_sections = self._build_dynamic_sections(
            glossary=glossary or [],
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
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
            learned_rules=learned_rules or [],
            previous_translation=previous_translation,
            instruction=instruction,
            format_tokens=format_tokens or [],
            include_revision_task=True,
            term_usage=term_usage,
        )

        return self.prompt_manager.get(
            TRANSLATION_TEMPLATE_NAME,
            text=source_text,
            dynamic_sections="\n\n".join(dynamic_sections),
            translation_profile_instructions=profile_text,
        )

    def build_retranslation_prompt(
        self,
        source_text: str,
        current_translation: str,
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
        learned_rules: Optional[List[str]] = None,
        instruction: Optional[str] = None,
        format_tokens: Optional[List[Dict[str, Any]]] = None,
        term_usage: Optional[Dict[str, List[str]]] = None,
        **_kwargs,
    ) -> str:
        dynamic_sections = self._build_dynamic_sections(
            glossary=glossary or [],
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
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
            learned_rules=learned_rules or [],
            format_tokens=format_tokens or [],
            include_revision_task=False,
            term_usage=term_usage,
        )
        revision_profile = self._build_revision_profile_section()
        if revision_profile:
            dynamic_sections.insert(0, revision_profile)

        return self.prompt_manager.get(
            RETRANSLATION_TEMPLATE_NAME,
            source=source_text,
            current=current_translation,
            instruction=(
                instruction or
                "先纠正前次译文中的错误，再给出最佳中文译文。"
            ),
            dynamic_sections="\n\n".join(dynamic_sections),
        )

    def _build_profile_section(self) -> str:
        if self.translation_profile == "standard":
            return "\n".join(
                [
                    "- 配置：标准长文翻译。",
                    "- 保留原文的密集推理和细腻的分析师判断。",
                    "- 必要时使用更完整的表述，以保持逻辑或论证力度。",
                ]
            )
        if self.translation_profile == "lean":
            return "\n".join(
                [
                    "- 配置：精简长文翻译。",
                    "- 保留所有事实和逻辑，但优先使用更紧凑的中文表达。",
                    "- 在能清晰保留原意的前提下，使用更短的句子。",
                ]
            )
        return ""

    def _build_revision_profile_section(self) -> str:
        profile_text = self._build_profile_section()
        if not profile_text:
            return ""
        return "## 修订配置\n" + profile_text

    def _build_format_token_section(self, format_tokens: List[Dict[str, Any]]) -> str:
        if not format_tokens:
            return ""

        lines = [
            "## 隐藏格式 Token",
            "- `[[[TYPE_N|...]]]` 形式的 token 是后端控制标记，不是 Markdown。",
            "- 保持 token 的外层包裹、token id 和类型完全不变。",
            "- 只翻译 `|` 后面的文本。",
            "- 不要删除、复制、重编号或将 token 移动到其他段落。",
            "- `CODE_*` token 内部文本必须保持不变，除非指令明确要求修改。",
        ]

        preview: List[str] = []
        for token in format_tokens[:MAX_FORMAT_TOKENS_IN_PROMPT]:
            token_id = token.get("id", "")
            token_type = token.get("type", "")
            token_text = token.get("text", "")
            if token_id and token_text:
                preview.append(f"- {token_id} ({token_type}): {token_text}")
        if preview:
            lines.extend(["", "本段包含的 token：", *preview])

        return "\n".join(lines)

    def _build_glossary_section(
        self,
        glossary: List[Dict],
        term_usage: Dict[str, List[str]] = None,
    ) -> str:
        return render_glossary_prompt_block(
            glossary,
            include_title=True,
            term_usage=term_usage,
            empty_text="",
        )

    def _build_rules_section(self, rules: List[str]) -> str:
        if not rules:
            return ""

        lines = ["## 已学习的翻译规则"]
        for rule in rules:
            lines.append(f"- {rule}")

        return "\n".join(lines)

    def _build_instruction_section(
        self,
        previous_translation: Optional[str] = None,
        instruction: Optional[str] = None,
    ) -> str:
        normalized_instruction = (instruction or "").strip()
        normalized_previous = (previous_translation or "").strip()
        if not normalized_instruction and not normalized_previous:
            return ""

        if not normalized_previous:
            return "\n".join(
                [
                    "## 额外翻译指令",
                    normalized_instruction,
                    "",
                    "请在翻译当前原文时遵循以上指令。",
                    "翻译时不要丢失隐藏格式 token。",
                ]
            )

        lines = ["## 修订任务"]

        if normalized_previous:
            preview = (
                normalized_previous[:600] + "..."
                if len(normalized_previous) > 600
                else normalized_previous
            )
            lines.append("前次译文（供参考）：")
            lines.append(preview)

        if normalized_instruction:
            lines.extend(["", "修订要求：", normalized_instruction])

        lines.extend(
            [
                "",
                "以原文为准。先纠正旧译中的错误，再满足修订要求。",
                "修订时不要丢失隐藏格式 token。",
            ]
        )
        return "\n".join(lines)

    def _build_dynamic_sections(
        self,
        glossary: List[Dict],
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
        learned_rules: Optional[List[str]] = None,
        previous_translation: Optional[str] = None,
        instruction: Optional[str] = None,
        format_tokens: Optional[List[Dict[str, Any]]] = None,
        include_revision_task: bool = False,
        term_usage: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        dynamic_sections: List[str] = []

        format_token_text = self._build_format_token_section(format_tokens or [])
        if format_token_text:
            dynamic_sections.append(format_token_text)

        glossary_text = self._build_glossary_section(glossary, term_usage=term_usage)
        if glossary_text:
            dynamic_sections.append(glossary_text)

        rules_text = self._build_rules_section(learned_rules or [])
        if rules_text:
            dynamic_sections.append(rules_text)

        if include_revision_task:
            revision_task_text = self._build_instruction_section(
                previous_translation=previous_translation,
                instruction=instruction,
            )
            if revision_task_text:
                dynamic_sections.append(revision_task_text)

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

        return dynamic_sections

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

        overview_lines = ["## 上下文"]
        if article_title:
            overview_lines.append(f"文章标题：{article_title}")
        if article_theme:
            overview_lines.append(f"文章主题：{article_theme}")
        if current_section_title:
            overview_lines.append(f"当前章节：{current_section_title}")
        if heading_chain:
            overview_lines.append(
                f"标题链：{' -> '.join(heading_chain[-MAX_HEADING_CHAIN_IN_PROMPT:])}"
            )
        if target_audience:
            overview_lines.append(f"目标读者：{target_audience}")
        if len(overview_lines) > 1:
            sections.append("\n".join(overview_lines))

        if article_structure:
            sections.append("## 结构说明\n" + article_structure)

        if section_context:
            section_lines = ["## 章节角色"]
            role = section_context.get("role")
            if role:
                section_lines.append(f"在文章中的角色：{role}")
            relation_to_previous = section_context.get("relation_to_previous")
            if relation_to_previous:
                section_lines.append(f"与上一章节的关系：{relation_to_previous}")
            key_points = limit_non_empty_strings(
                section_context.get("key_points"),
                MAX_SECTION_KEY_POINTS_IN_PROMPT,
            )
            if key_points:
                section_lines.append("核心论点：")
                section_lines.extend(f"- {point}" for point in key_points)
            translation_notes = limit_non_empty_strings(
                section_context.get("translation_notes"),
                MAX_SECTION_NOTES_IN_PROMPT,
            )
            if translation_notes:
                section_lines.append("翻译注意事项：")
                section_lines.extend(f"- {note}" for note in translation_notes)
            if len(section_lines) > 1:
                sections.append("\n".join(section_lines))

        style_notes: List[str] = []
        if translation_voice:
            style_notes.append(f"期望的中文语体：{translation_voice}")
        if style_guide:
            tone = style_guide.get("tone")
            if tone:
                style_notes.append(f"语调：{tone}")
            notes = limit_non_empty_strings(
                style_guide.get("notes"),
                MAX_STYLE_NOTES_IN_PROMPT,
            )
            style_notes.extend(notes)
        if style_notes:
            sections.append("## 风格约束\n" + "\n".join(f"- {item}" for item in style_notes))

        if article_challenges:
            challenge_lines = ["## 翻译风险"]
            for challenge in build_article_challenge_payload(
                article_challenges,
                MAX_ARTICLE_CHALLENGES_IN_PROMPT,
            ):
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
            prev_lines = ["## 前文已确认译文"]
            src, trans = previous_paragraphs[-1]
            prev_lines.append(f"原文：{_truncate_by_sentence(src, 120)}")
            prev_lines.append(f"译文：{_truncate_by_sentence(trans, 120)}")
            sections.append("\n".join(prev_lines))

        if next_preview:
            preview_lines = ["## 下文预览"]
            preview_lines.append(f"- {_truncate_by_sentence(next_preview[0], 160)}")
            sections.append("\n".join(preview_lines))

        return "\n\n".join(sections) if sections else ""


_builders: Dict[str, TranslationPromptBuilder] = {}


def get_prompt_builder(style: str = "simplified") -> TranslationPromptBuilder:
    """Return a singleton builder per prompt style."""
    style_key = (style or "simplified").strip().lower()
    if style_key not in STYLE_CONFIG:
        style_key = "simplified"
    builder = _builders.get(style_key)
    if builder is None:
        builder = TranslationPromptBuilder(prompt_style=style_key)
        _builders[style_key] = builder
    return builder

