# Longform Prompt Context Contracts

This folder documents the canonical logical context shapes used by the longform prompt system.

## ArticleContext

```json
{
  "article": {
    "title": "string",
    "theme": "string",
    "structure_summary": "string",
    "key_arguments": ["string"],
    "target_audience": "string",
    "translation_voice": "string",
    "tone": "string",
    "guidelines": ["string"],
    "challenges": [
      {
        "location": "string",
        "issue": "string",
        "suggestion": "string"
      }
    ]
  }
}
```

## TerminologyContext

```json
{
  "terminology": {
    "terms": [
      {
        "term": "string",
        "translation": "string|null",
        "strategy": "preserve|first_annotate|translate",
        "context_meaning": "string",
        "first_occurrence_note": true,
        "rationale": "string"
      }
    ]
  }
}
```

## SectionContext

```json
{
  "section": {
    "id": "string",
    "title": "string",
    "title_translation": "string",
    "position": "3/8",
    "previous_title": "string",
    "next_title": "string",
    "role": "string",
    "relation_to_previous": "string",
    "relation_to_next": "string",
    "key_points": ["string"],
    "translation_notes": ["string"]
  }
}
```

## ParagraphContext

```json
{
  "paragraph": {
    "id": "string",
    "heading_chain": ["string"],
    "previous_confirmed": [
      {
        "source": "string",
        "translation": "string"
      }
    ],
    "next_preview": ["string"]
  }
}
```

## FormattingContext

```json
{
  "formatting": {
    "has_hidden_tokens": true,
    "tokens": [
      {
        "id": "LINK_1",
        "type": "link",
        "text": "source text"
      }
    ]
  }
}
```

## RevisionContext

```json
{
  "revision": {
    "instruction": "string",
    "current_translation": "string"
  }
}
```

## LearnedRulesContext

```json
{
  "learned_rules": [
    {
      "wrong": "string",
      "right": "string",
      "instruction": "string",
      "rule_type": "hard_rule|soft_preference|strict_prohibition",
      "category": "terminology|accuracy|fluency|style|locale"
    }
  ]
}
```
