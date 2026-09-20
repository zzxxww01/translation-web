"""Provider-independent business prompts; providers handle transport only."""
from __future__ import annotations
import json
from typing import Any
from . import get_prompt_manager
from .prompt_builder import TranslationPromptBuilder
from src.core.glossary_prompt import render_glossary_prompt_block
from src.core.longform_context import build_section_guideline_lines, build_article_challenge_payload

_PARAGRAPH_FIELDS = (
    "glossary", "previous_paragraphs", "next_preview", "article_title", "article_theme",
    "article_structure", "current_section_title", "heading_chain", "target_audience",
    "translation_voice", "article_challenges", "style_guide", "section_context", "learned_rules",
    "instruction", "previous_translation", "format_tokens", "term_usage",
)

def paragraph_prompt(source: str, context: dict, *, current: str | None = None) -> str:
    from src.settings import settings
    builder = TranslationPromptBuilder(prompt_style=settings.translation_prompt_style)
    kwargs = {key: context[key] for key in _PARAGRAPH_FIELDS if key in context}
    if current is None:
        return builder.build_prompt(source_text=source, **kwargs)
    kwargs.pop("previous_translation", None)
    return builder.build_retranslation_prompt(source_text=source, current_translation=current, **kwargs)

def section_prompt(text: str, title: str, context: dict, ids: list[str]) -> str:
    pm = get_prompt_manager()
    guidelines = build_section_guideline_lines(
        context.get("guidelines", []), section_role=context.get("section_role", ""),
        translation_voice=context.get("translation_voice", ""),
        target_audience=context.get("target_audience", ""), translation_notes=context.get("translation_notes"),
    )
    for key in ("relation_to_previous", "relation_to_next", "annotation_plan", "paragraph_structure"):
        if context.get(key):
            guidelines.append(f"{key}: " + json.dumps(context[key], ensure_ascii=False))
    # Source and approved translation stay together; explicit truncation, never a claimed full history.
    previous = []
    for pair in context.get("previous_translations", [])[-3:]:
        previous.append({key: str(pair.get(key, ""))[:1000] for key in ("source", "translation")})
    return pm.render(
        "longform/translation/section_batch_translate",
        section_title=title, section_text=text, paragraph_ids=json.dumps(ids, ensure_ascii=False),
        article_theme=context.get("article_theme", ""),
        article_challenges=json.dumps(build_article_challenge_payload(context.get("article_challenges")), ensure_ascii=False),
        target_audience=context.get("target_audience", ""), translation_voice=context.get("translation_voice", ""),
        section_position=context.get("section_position", ""),
        previous_section=context.get("previous_section_title", ""), next_section=context.get("next_section_title", ""),
        glossary=render_glossary_prompt_block(context.get("glossary", []), term_usage=context.get("term_usage")),
        previous_translations=json.dumps(previous, ensure_ascii=False),
        feedback_from_previous_sections=context.get("feedback_from_previous_sections", ""),
        guidelines="\n".join(str(g) for g in guidelines),
    )

def analysis_prompt(text: str) -> str:
    return get_prompt_manager().render("analysis", text=text[:18000])

def consistency_prompt(paragraphs: list[dict], glossary: Any) -> str:
    pairs = [{"paragraph_index": i, "source": p["source"], "translation": p["translation"]}
             for i, p in enumerate(paragraphs)]
    return get_prompt_manager().render("consistency", para_text=json.dumps(pairs, ensure_ascii=False),
                                       glossary_text=render_glossary_prompt_block(glossary))

def title_prompt(title: str, subtitle: str | None, context: dict) -> str:
    return get_prompt_manager().render("longform/auxiliary/title_translate", title=title, subtitle=subtitle or "",
        glossary_block=context.get("glossary_block", "（无）"),
        preservation_block=context.get("preservation_block", "（无额外保留项）"),
        context_block=json.dumps({key: context[key] for key in ("article_theme", "structure_summary", "target_audience") if context.get(key)}, ensure_ascii=False))

def section_title_prompt(title: str, context: dict, glossary_block: str = "", whitelist_rules: str = "") -> str:
    glossary = glossary_block or context.get("glossary_block") or context.get("glossary") or "（无）"
    if not isinstance(glossary, str):
        glossary = render_glossary_prompt_block(glossary)
    return get_prompt_manager().render("longform/auxiliary/section_title_translate", title=title,
        glossary=glossary, whitelist_rules=whitelist_rules or context.get("whitelist_rules", ""),
        context_block=json.dumps({key: value for key, value in context.items() if key not in {"glossary", "glossary_block", "whitelist_rules"}}, ensure_ascii=False, default=str))

def section_titles_prompt(sections: list[dict], theme: str, glossary: str, rules: str) -> str:
    return get_prompt_manager().render("longform/auxiliary/section_titles_batch", sections_json=json.dumps(sections, ensure_ascii=False),
                                      article_theme=theme, glossary_block=glossary, whitelist_rules=rules)

def source_metadata_prompt(entries: list[dict], context: dict) -> str:
    return get_prompt_manager().render("longform/metadata/source_batch_translate", entry_count=len(entries),
        glossary_block=context.get("glossary_block", "（无）"), entries_json=json.dumps(entries, ensure_ascii=False))

def format_repair_prompt(source: str, translation: str, tokens: list[dict], issues: list[str]) -> str:
    return get_prompt_manager().render("longform/auxiliary/format_repair", source=source, translation=translation,
                                      tokens=json.dumps(tokens, ensure_ascii=False), issues=json.dumps(issues, ensure_ascii=False))
