"""Terminology pre-review and glossary promotion service."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.glossary import GlossaryManager, infer_glossary_tags
from src.core.models import (
    ElementType,
    Glossary,
    GlossaryTerm,
    ProjectMeta,
    Section,
    TranslationStrategy,
)
from src.core.project import ProjectManager
from src.llm.base import LLMProvider


def _normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip()).lower()


def _safe_count_occurrences(text: str, term: str) -> int:
    normalized_text = text.lower()
    normalized_term = term.lower().strip()
    if not normalized_term:
        return 0

    if re.fullmatch(r"[a-z0-9 .,+\-/]+", normalized_term):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])"
        return len(re.findall(pattern, normalized_text))

    return normalized_text.count(normalized_term)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_term(a), _normalize_term(b)).ratio()


@dataclass
class AggregatedCandidate:
    term: str
    suggested_translations: Counter[str] = field(default_factory=Counter)
    section_ids: List[str] = field(default_factory=list)
    section_titles: Dict[str, str] = field(default_factory=dict)
    contexts: List[str] = field(default_factory=list)
    hit_title: bool = False
    total_occurrences: int = 0


class TerminologyReviewService:
    """Prepare terminology review data and manage project/global promotion."""

    HIGH_FREQUENCY_THRESHOLD = 2
    SIMILARITY_THRESHOLD = 0.45
    MAX_SIMILAR_TERMS = 3

    def __init__(
        self,
        project_manager: ProjectManager,
        glossary_manager: GlossaryManager,
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        self.llm = llm_provider
        self.project_manager = project_manager
        self.glossary_manager = glossary_manager

    def prepare_review(self, project_id: str) -> Dict[str, Any]:
        project = self.project_manager.get(project_id)
        sections = self.project_manager.get_sections(project_id)
        merged_glossary = self.glossary_manager.load_merged(project_id)
        existing_terms = self.glossary_manager.to_dict(
            merged_glossary,
            include_strategy_notes=False,
        )
        aggregated: Dict[str, AggregatedCandidate] = {}

        for section in sections:
            prescan_result = self._prescan_section(section, existing_terms)
            if not prescan_result:
                continue

            section_text = "\n".join(paragraph.source for paragraph in section.paragraphs)
            heading_text = "\n".join(
                paragraph.source
                for paragraph in section.paragraphs
                if paragraph.element_type in (ElementType.H3, ElementType.H4)
            )
            title_space = f"{section.title}\n{heading_text}".lower()

            for term_data in prescan_result.get("new_terms", []):
                term = (term_data.get("term") or "").strip()
                suggested_translation = (
                    term_data.get("suggested_translation") or ""
                ).strip()
                context = (term_data.get("context") or "").strip()
                normalized = _normalize_term(term)
                if not term or not normalized:
                    continue
                if merged_glossary.get_term(term):
                    continue

                candidate = aggregated.setdefault(
                    normalized,
                    AggregatedCandidate(term=term),
                )
                candidate.term = candidate.term or term
                if suggested_translation:
                    candidate.suggested_translations[suggested_translation] += 1
                if section.section_id not in candidate.section_ids:
                    candidate.section_ids.append(section.section_id)
                candidate.section_titles[section.section_id] = section.title
                if context and context not in candidate.contexts:
                    candidate.contexts.append(context)
                candidate.hit_title = candidate.hit_title or (
                    normalized in title_space
                )
                candidate.total_occurrences += max(
                    _safe_count_occurrences(section_text, term),
                    1,
                )

        payload = self._build_review_payload(
            project=project,
            merged_glossary=merged_glossary,
            aggregated=aggregated,
        )
        self._write_payload(project_id, payload)
        return payload

    def apply_review(self, project_id: str, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        glossary = self.glossary_manager.load_project(project_id)
        applied: List[Dict[str, Any]] = []
        skipped: List[str] = []

        for decision in decisions:
            term = (decision.get("term") or "").strip()
            action = (decision.get("action") or "").strip().lower()
            translation = (decision.get("translation") or "").strip()
            note = (decision.get("note") or "").strip() or None
            first_occurrence = (decision.get("first_occurrence") or "").strip() or None
            if not term:
                continue

            if action == "skip":
                skipped.append(term)
                continue

            if not translation:
                continue

            existing = glossary.get_term(term)
            term_entry = GlossaryTerm(
                original=term,
                translation=translation,
                strategy=existing.strategy if existing else self._infer_strategy(term, translation),
                note=note if note is not None else (existing.note if existing else None),
                tags=list(existing.tags) if existing and existing.tags else infer_glossary_tags(term),
                first_occurrence=first_occurrence or (existing.first_occurrence if existing else None),
                scope="project",
                source="term_review",
                status="active",
            )
            glossary.add_term(term_entry)
            applied.append(term_entry.model_dump(mode="json"))

        self.glossary_manager.save_project(project_id, glossary)
        return {
            "project_id": project_id,
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "applied_terms": applied,
            "skipped_terms": skipped,
        }

    def get_project_recommendations(self, project_id: str) -> Dict[str, Any]:
        project_glossary = self.glossary_manager.load_project(project_id)
        global_glossary = self.glossary_manager.load_global()
        project = self.project_manager.get(project_id)
        sections = self.project_manager.get_sections(project_id)
        recommendations: List[Dict[str, Any]] = []

        for term in project_glossary.terms:
            if term.status != "active" or not term.translation:
                continue

            global_term = global_glossary.get_term(term.original)
            if global_term and global_term.translation == term.translation:
                continue

            usage = self._calculate_usage(sections, term.original)
            if usage["usage_count"] < self.HIGH_FREQUENCY_THRESHOLD:
                continue

            recommendations.append(
                {
                    "original": term.original,
                    "translation": term.translation,
                    "strategy": term.strategy.value,
                    "note": term.note,
                    "scope": "project",
                    "source": term.source,
                    "status": term.status,
                    "usage_count": usage["usage_count"],
                    "section_ids": usage["section_ids"],
                    "section_titles": [
                        {
                            "section_id": section.section_id,
                            "title": section.title,
                        }
                        for section in sections
                        if section.section_id in usage["section_ids"]
                    ],
                    "recommended_reason": (
                        f"在当前项目《{project.title}》中高频出现"
                    ),
                }
            )

        recommendations.sort(key=lambda item: (-item["usage_count"], item["original"].lower()))
        return {
            "project_id": project_id,
            "recommendations": recommendations,
        }

    def promote_project_term(self, project_id: str, original: str) -> Dict[str, Any]:
        project_glossary = self.glossary_manager.load_project(project_id)
        global_glossary = self.glossary_manager.load_global()
        project_term = project_glossary.get_term(original)
        if not project_term:
            raise FileNotFoundError(f"Project term not found: {original}")

        promoted = GlossaryTerm(
            original=project_term.original,
            translation=project_term.translation,
            strategy=project_term.strategy,
            note=project_term.note,
            tags=list(project_term.tags),
            first_occurrence=project_term.first_occurrence,
            scope="global",
            source="promoted_from_project",
            status=project_term.status,
        )
        global_glossary.add_term(promoted)
        self.glossary_manager.save_global(global_glossary)
        return {
            "message": "Term promoted to global glossary",
            "term": promoted.model_dump(mode="json"),
        }

    def _prescan_section(
        self,
        section: Section,
        existing_terms: Dict[str, str],
    ) -> Dict[str, Any]:
        if self.llm is None:
            raise RuntimeError("LLM provider is required for term-review prepare flow.")
        section_content = "\n\n".join(paragraph.source for paragraph in section.paragraphs)
        return self.llm.prescan_section_with_flash(
            section_id=section.section_id,
            section_title=section.title,
            section_content=section_content,
            existing_terms=existing_terms,
        )

    def _build_review_payload(
        self,
        project: ProjectMeta,
        merged_glossary: Glossary,
        aggregated: Dict[str, AggregatedCandidate],
    ) -> Dict[str, Any]:
        section_groups: Dict[str, Dict[str, Any]] = {}

        for candidate in aggregated.values():
            reasons = self._build_candidate_reasons(candidate)
            if not reasons:
                continue

            first_section_id = candidate.section_ids[0]
            first_section_title = candidate.section_titles.get(first_section_id, "")
            suggested_translation = candidate.suggested_translations.most_common(1)[0][0] if candidate.suggested_translations else ""
            similar_terms = self._find_similar_terms(candidate.term, merged_glossary)

            group = section_groups.setdefault(
                first_section_id,
                {
                    "section_id": first_section_id,
                    "section_title": first_section_title,
                    "candidates": [],
                },
            )
            group["candidates"].append(
                {
                    "term": candidate.term,
                    "suggested_translation": suggested_translation,
                    "reasons": reasons,
                    "occurrence_count": candidate.total_occurrences,
                    "first_occurrence": first_section_id,
                    "related_sections": [
                        {
                            "section_id": section_id,
                            "section_title": candidate.section_titles.get(section_id, ""),
                        }
                        for section_id in candidate.section_ids
                    ],
                    "contexts": candidate.contexts[:3],
                    "similar_terms": similar_terms,
                }
            )

        sections = list(section_groups.values())
        sections.sort(key=lambda item: item["section_id"])
        for section in sections:
            section["candidates"].sort(
                key=lambda item: (-item["occurrence_count"], item["term"].lower())
            )

        total_candidates = sum(len(section["candidates"]) for section in sections)
        return {
            "project_id": project.id,
            "project_title": project.title,
            "review_required": total_candidates > 0,
            "generated_at": datetime.now().isoformat(),
            "total_candidates": total_candidates,
            "sections": sections,
        }

    def _build_candidate_reasons(self, candidate: AggregatedCandidate) -> List[str]:
        reasons: List[str] = []
        if candidate.hit_title:
            reasons.append("title")
        if candidate.total_occurrences >= self.HIGH_FREQUENCY_THRESHOLD:
            reasons.append("high_frequency")
        if len(candidate.suggested_translations) > 1:
            reasons.append("ambiguous")
        return reasons

    def _find_similar_terms(self, term: str, glossary: Glossary) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        for item in glossary.terms:
            if _normalize_term(item.original) == _normalize_term(term):
                continue
            score = _similarity(term, item.original)
            if score < self.SIMILARITY_THRESHOLD and _normalize_term(term) not in _normalize_term(item.original) and _normalize_term(item.original) not in _normalize_term(term):
                continue
            suggestions.append(
                {
                    "original": item.original,
                    "translation": item.translation,
                    "strategy": item.strategy.value,
                    "scope": item.scope,
                    "note": item.note,
                    "similarity": round(score, 3),
                }
            )
        suggestions.sort(key=lambda item: (-item["similarity"], item["original"].lower()))
        return suggestions[: self.MAX_SIMILAR_TERMS]

    def _calculate_usage(self, sections: List[Section], term: str) -> Dict[str, Any]:
        section_ids: List[str] = []
        usage_count = 0
        for section in sections:
            section_text = "\n".join(paragraph.source for paragraph in section.paragraphs)
            matches = _safe_count_occurrences(section_text, term)
            if matches:
                section_ids.append(section.section_id)
                usage_count += matches
        return {
            "usage_count": usage_count,
            "section_ids": section_ids,
        }

    def _infer_strategy(self, term: str, translation: str) -> TranslationStrategy:
        stripped = term.strip()
        upper_term = stripped.upper()
        if upper_term == stripped and len(stripped) <= 8:
            return TranslationStrategy.PRESERVE
        if translation and translation == stripped:
            return TranslationStrategy.PRESERVE
        # 含英文字母 + 有不同的中文翻译 → 首次括注
        if re.search(r'[a-zA-Z]', stripped) and translation and translation != stripped:
            return TranslationStrategy.FIRST_ANNOTATE
        return TranslationStrategy.TRANSLATE

    def _write_payload(self, project_id: str, payload: Dict[str, Any]) -> None:
        output_dir = self.project_manager.projects_path / project_id / "artifacts" / "term-review"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "latest.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
