# Longform context contracts (v2)

Business prompt construction is centralized in `src/prompts/task_builders.py`. Providers retain transport and public compatibility methods; they do not define alternative business rules.

Paragraph context: glossary, previous_paragraphs, next_preview, article_title, article_theme, article_structure, current_section_title, heading_chain, target_audience, translation_voice, article_challenges, style_guide, section_context, learned_rules, instruction, previous_translation, format_tokens, term_usage.

Section context includes source-order annotation_plan (`term -> section_id, paragraph_id`), paragraph_structure only when source evidence exists, and explicit reference material separate from the output paragraphs.

Terminology strategy is one of preserve, preserve_annotate, first_annotate, translate. `alternatives`, `avoid`, and `source_quote` are evidence, not unconditional replacements. Prescan has no translations and must return an empty legacy term_usages object.

Run artifacts include the resolved prompt bundle manifest and digest. Incompatible or unversioned partial runs require an explicit new retranslation rather than silent mixed-version resume. Model-inferred memory remains pending until an explicit approval operation.
