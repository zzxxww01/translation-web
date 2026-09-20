# Output contracts (v2)

All JSON tasks use a top-level object and local validation. Invalid JSON is an error, not an empty success. Unknown/duplicate paragraph IDs, duplicate object keys and non-finite scores are rejected.

- Analysis: terms (original, translation, strategy, note), style, summary.
- Deep analysis: theme, key_arguments, structure_summary, style, sampled_terms (or terminology for article_analysis), challenges, guidelines.
- Candidate verification: verified_terms includes positive and negative decisions; source evidence is required for interpretation.
- Prescan: new_terms (term, suggested_translation, context, source_quote, confidence, requires_review), term_usages={}.
- Batch translation / metadata: translations=[{id, translation}]. Missing IDs explicitly retry; no position-based guessing.
- Section titles: translations={id: non-empty string}.
- Review: issues=[{paragraph_index, original_text, translation_text, issue_type, severity, priority, description, why_it_matters, suggestion}]. Scores are optional diagnostics. Program computes counts and binds evidence to reviewed_version.
- Refine: polished_translations=[{index, translation}]. Indices are batch-local and unique. Missing items preserve the original but do not imply the issue was solved.
- Rule extraction: bounded bullet list or NONE, stored as pending candidates, never automatically active global rules.
- Titles: public legacy two-line format is retained; parser removes only the initial label, never internal colons.

A changed translation requires fresh review before acceptance. Parse or model failures remain visible as degraded/unresolved states. Grammar/format correctness does not establish semantic fidelity.
