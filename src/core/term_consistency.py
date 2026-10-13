"""Conservative source-aware terminology signals shared by both review entrypoints.

These checks report suspected mismatches, not machine-editable replacements.
Polysemous terms need semantic review and cannot be checked by global substitution.
"""
from __future__ import annotations
from collections import Counter
import re
from typing import Any, Iterable
from .glossary_prompt import _count_term_occurrences, _normalize_prompt_term, _is_polysemous_translation, _prose_only
from .models import ConsistencyIssue


def check_terminology(sections, translations: dict[str, list[str]], terms: Iterable[Any]):
    issues: list[ConsistencyIssue] = []
    stats: dict[str, dict] = {}
    for term in terms:
        if getattr(term, 'status', 'active') != 'active':
            continue
        item = _normalize_prompt_term(term)
        if not item:
            continue
        original, expected = item['original'], item['translation']
        ambiguous = _is_polysemous_translation(expected, item['note'])
        strategy = item['strategy']
        if strategy in {'preserve', 'preserve_annotate'}:
            expected = original
        elif strategy == 'first_annotate':
            # The standard spelling may itself include the first-mention note.
            expected = re.sub(r'\s*[（(][A-Za-z0-9 ._-]+[)）]$', '', expected).strip()
        counts: Counter = Counter()
        missing_locations = []
        total = 0
        for section in sections:
            for index, (para, translated) in enumerate(zip(section.paragraphs, translations.get(section.section_id, []))):
                if not translated.strip() or not _count_term_occurrences(_prose_only(para.source), original):
                    continue
                total += 1
                if ambiguous:
                    continue
                found = _count_term_occurrences(translated, expected) > 0
                if found:
                    counts[expected] += 1
                else:
                    missing_locations.append((section.section_id, index))
        if not total:
            continue
        stats[original] = {
            'total_count': total, 'total_hits': total,
            'expected_hits': counts[expected], 'other_hits': len(missing_locations),
            'translations': dict(counts), 'preferred': expected,
            'is_consistent': not missing_locations,
            'requires_context_review': ambiguous,
        }
        for section_id, index in missing_locations:
            issues.append(ConsistencyIssue(
                section_id=section_id, paragraph_index=index, issue_type='terminology',
                description=f'术语 "{original}" 未检测到当前义项的标准写法 "{expected}"，需对照原文核验',
                auto_fixable=False, fix_suggestion='请确认本处义项与术语表一致后再修改，不要整段替换',
            ))
    return issues, stats
