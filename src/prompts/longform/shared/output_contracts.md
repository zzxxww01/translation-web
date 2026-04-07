# Longform Prompt Output Contracts

## Article Analysis

```json
{
  "theme": "string",
  "key_arguments": ["string"],
  "structure_summary": "string",
  "terminology": [
    {
      "term": "string",
      "context_meaning": "string",
      "translation": "string|null",
      "strategy": "preserve|first_annotate|translate",
      "first_occurrence_note": true,
      "rationale": "string"
    }
  ],
  "style": {
    "tone": "string",
    "target_audience": "string",
    "translation_voice": "string"
  },
  "challenges": [
    {
      "type": "terminology|metaphor|cultural_reference|cross_domain_term|rhetorical_tone|structure|accuracy",
      "location": "string",
      "issue": "string",
      "suggestion": "string"
    }
  ],
  "guidelines": ["string"]
}
```

## Section Role Map

```json
{
  "section_roles": {
    "section_id": {
      "role_in_article": "string",
      "relation_to_previous": "string",
      "relation_to_next": "string",
      "key_points": ["string"],
      "translation_notes": ["string"]
    }
  }
}
```

## Section Prescan

```json
{
  "new_terms": [
    {
      "term": "string",
      "suggested_translation": "string",
      "context": "string",
      "confidence": 0.9
    }
  ],
  "term_usages": {
    "existing_term": "translation used in this section"
  }
}
```

## Paragraph Translation

Plain Chinese text only.

## Paragraph Retranslation

Plain Chinese text only.

## Section Batch Translation

```json
{
  "translations": [
    {
      "id": "p001",
      "translation": "string"
    }
  ]
}
```

## Section Critique

```json
{
  "overall_score": 8.6,
  "readability_score": 8.2,
  "accuracy_score": 9.1,
  "conciseness_score": 8.0,
  "is_excellent": false,
  "issues": [
    {
      "paragraph_index": 2,
      "issue_type": "accuracy|terminology|tone|readability|annotation|data|structure",
      "severity": "critical|high|medium|low",
      "original_text": "string",
      "description": "string",
      "why_it_matters": "string",
      "suggestion": "string"
    }
  ]
}
```

## Rule Extraction

```json
{
  "has_meaningful_change": true,
  "rules": [
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
