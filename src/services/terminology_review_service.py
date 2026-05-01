"""Terminology pre-review and glossary promotion service."""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from src.llm.config_loader import get_config_loader


logger = logging.getLogger(__name__)


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
    existing_terms: List[GlossaryTerm] = field(default_factory=list)
    section_ids: List[str] = field(default_factory=list)
    section_titles: Dict[str, str] = field(default_factory=dict)
    contexts: List[str] = field(default_factory=list)
    hit_title: bool = False
    total_occurrences: int = 0
    force_reasons: List[str] = field(default_factory=list)


class TerminologyReviewService:
    """Prepare terminology review data and manage project/global promotion."""

    REVIEW_SCHEMA_VERSION = 4
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

    def prepare_review(self, project_id: str, *, force: bool = False) -> Dict[str, Any]:
        started_at = time.monotonic()
        logger.info(
            "[%s] term-review prepare start: force=%s model=%s",
            project_id,
            force,
            self._llm_model_name(),
        )
        if not force:
            cached = self._load_cached_payload(project_id)
            if cached is not None:
                logger.info(
                    "[%s] term-review prepare cache hit: candidates=%s elapsed=%.3fs",
                    project_id,
                    cached.get("total_candidates"),
                    time.monotonic() - started_at,
                )
                return cached

        try:
            project = self.project_manager.get(project_id)
            sections = self.project_manager.get_sections(project_id)
            full_text = "\n\n".join(
                paragraph.source
                for section in sections
                for paragraph in section.paragraphs
            )
            project_glossary = self.glossary_manager.load_project(project_id)
            global_glossary = self.glossary_manager.load_global()
            merged_glossary = self.glossary_manager.load_merged(project_id)
            existing_terms = self.glossary_manager.to_dict(
                merged_glossary,
                include_strategy_notes=False,
            )
            aggregated: Dict[str, AggregatedCandidate] = {}
            logger.info(
                "[%s] term-review inputs loaded: sections=%d existing_terms=%d elapsed=%.3fs",
                project_id,
                len(sections),
                len(existing_terms),
                time.monotonic() - started_at,
            )

            self._aggregate_project_global_conflicts(
                sections=sections,
                full_text=full_text,
                project_glossary=project_glossary,
                global_glossary=global_glossary,
                aggregated=aggregated,
            )
            prescan_results = self._prescan_sections(project_id, sections, existing_terms)

            for section in sections:
                prescan_result = prescan_results.get(section.section_id)
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
                    existing_term = merged_glossary.get_term(term)
                    if existing_term and not self._term_suggestion_conflicts(
                        existing_term,
                        suggested_translation,
                    ):
                        continue

                    candidate = aggregated.setdefault(
                        normalized,
                        AggregatedCandidate(term=term),
                    )
                    candidate.term = candidate.term or term
                    if suggested_translation:
                        candidate.suggested_translations[suggested_translation] += 1
                    if existing_term:
                        self._add_existing_term(candidate, existing_term)
                        self._add_force_reason(candidate, "existing_conflict")
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
            logger.info(
                "[%s] term-review prepare complete: candidates=%d sections_with_candidates=%d elapsed=%.3fs",
                project_id,
                payload.get("total_candidates", 0),
                len(payload.get("sections", [])),
                time.monotonic() - started_at,
            )
            return payload
        except Exception as exc:
            logger.exception(
                "[%s] term-review prepare failed: force=%s model=%s elapsed=%.3fs error=%s",
                project_id,
                force,
                self._llm_model_name(),
                time.monotonic() - started_at,
                exc,
            )
            raise

    def _load_cached_payload(self, project_id: str) -> Optional[Dict[str, Any]]:
        latest_path = (
            self.project_manager.projects_path
            / project_id
            / "artifacts"
            / "term-review"
            / "latest.json"
        )
        if not latest_path.exists():
            return None

        try:
            latest_mtime = latest_path.stat().st_mtime
            dependency_mtime = self._term_review_dependency_mtime(project_id)
            if latest_mtime < dependency_mtime:
                return None
            with open(latest_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if payload.get("project_id") != project_id:
                return None
            if payload.get("schema_version") != self.REVIEW_SCHEMA_VERSION:
                return None
            if payload.get("model") != self._llm_model_name():
                return None
            payload["cached"] = True
            return payload
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def _term_review_dependency_mtime(self, project_id: str) -> float:
        project_dir = self.project_manager.projects_path / project_id
        paths = [
            project_dir / "meta.json",
            project_dir / "source.md",
            project_dir / "source.html",
            project_dir / "glossary.json",
            Path("config/llm_providers.yaml"),
            self.glossary_manager.global_path / "global_glossary_semi.json",
        ]
        sections_dir = project_dir / "sections"
        if sections_dir.exists():
            paths.extend(sections_dir.glob("*/source.md"))
            paths.extend(sections_dir.glob("*/meta.json"))

        mtimes = []
        for path in paths:
            try:
                mtimes.append(path.stat().st_mtime)
            except OSError:
                continue
        return max(mtimes, default=0.0)

    def _llm_model_name(self) -> str:
        return (
            getattr(self.llm, "model_name", None)
            or getattr(self.llm, "default_model", None)
            or ""
        )

    def _prescan_sections(
        self,
        project_id: str,
        sections: List[Section],
        existing_terms: Dict[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        worker_count = self._prescan_max_workers(len(sections))
        started_at = time.monotonic()
        logger.info(
            "[%s] term-review prescan sections start: sections=%d max_workers=%d model=%s",
            project_id,
            len(sections),
            worker_count,
            self._llm_model_name(),
        )
        if len(sections) <= 1:
            results = {
                section.section_id: self._prescan_section_logged(project_id, section, existing_terms)
                for section in sections
            }
            logger.info(
                "[%s] term-review prescan sections complete: sections=%d elapsed=%.3fs",
                project_id,
                len(results),
                time.monotonic() - started_at,
            )
            return results

        results: Dict[str, Dict[str, Any]] = {}
        failures: List[str] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(
                    self._prescan_section_logged,
                    project_id,
                    section,
                    existing_terms,
                ): section
                for section in sections
            }
            for future in as_completed(future_map):
                section = future_map[future]
                try:
                    results[section.section_id] = future.result()
                except Exception as exc:
                    failures.append(f"{section.section_id}: {exc}")
                    logger.exception(
                        "[%s] term-review section prescan future failed: section_id=%s error=%s",
                        project_id,
                        section.section_id,
                        exc,
                    )
                    results[section.section_id] = {}
        if failures:
            raise RuntimeError(
                "Terminology precheck failed for "
                f"{len(failures)}/{len(sections)} sections: "
                + "; ".join(failures[:5])
            )
        logger.info(
            "[%s] term-review prescan sections complete: sections=%d elapsed=%.3fs",
            project_id,
            len(results),
            time.monotonic() - started_at,
        )
        return results

    def _prescan_section_logged(
        self,
        project_id: str,
        section: Section,
        existing_terms: Dict[str, str],
    ) -> Dict[str, Any]:
        started_at = time.monotonic()
        paragraph_count = len(section.paragraphs)
        char_count = sum(len(paragraph.source or "") for paragraph in section.paragraphs)
        logger.info(
            "[%s] term-review section prescan start: section_id=%s title=%s paragraphs=%d chars=%d",
            project_id,
            section.section_id,
            section.title,
            paragraph_count,
            char_count,
        )
        try:
            result = self._prescan_section(section, existing_terms)
            logger.info(
                "[%s] term-review section prescan complete: section_id=%s new_terms=%d elapsed=%.3fs",
                project_id,
                section.section_id,
                len(result.get("new_terms", []) if isinstance(result, dict) else []),
                time.monotonic() - started_at,
            )
            return result
        except Exception as exc:
            logger.exception(
                "[%s] term-review section prescan failed: section_id=%s elapsed=%.3fs error=%s",
                project_id,
                section.section_id,
                time.monotonic() - started_at,
                exc,
            )
            raise

    def _prescan_max_workers(self, section_count: int) -> int:
        if section_count <= 1:
            return 1

        model_name = self._llm_model_name()
        if not model_name:
            return section_count

        try:
            llm_config = get_config_loader().load()
        except Exception:
            return section_count

        for provider in llm_config.providers.values():
            for model in provider.models:
                if model.alias == model_name or model.real_model == model_name:
                    try:
                        configured = int(
                            provider.rate_limit.get("max_concurrent") or section_count
                        )
                    except (TypeError, ValueError):
                        configured = section_count
                    return max(1, min(configured, section_count))

        return section_count

    def apply_review(self, project_id: str, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        glossary = self.glossary_manager.load_project(project_id)
        review_payload = self._load_cached_payload(project_id) or {}
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
            strategy = self._strategy_from_review_payload(
                review_payload,
                term,
                translation,
            )
            term_entry = GlossaryTerm(
                original=term,
                translation=translation,
                strategy=strategy or (existing.strategy if existing else self._infer_strategy(term, translation)),
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

    def _strategy_from_review_payload(
        self,
        review_payload: Dict[str, Any],
        term: str,
        translation: str,
    ) -> Optional[TranslationStrategy]:
        normalized_term = _normalize_term(term)
        normalized_translation = _normalize_term(translation)
        for section in review_payload.get("sections", []) or []:
            for candidate in section.get("candidates", []) or []:
                if _normalize_term(candidate.get("term", "")) != normalized_term:
                    continue
                for source_key in ("existing_terms", "similar_terms"):
                    for option in candidate.get(source_key, []) or []:
                        option_translation = option.get("translation") or option.get("original") or ""
                        if _normalize_term(option_translation) != normalized_translation:
                            continue
                        try:
                            return TranslationStrategy(option.get("strategy") or "translate")
                        except ValueError:
                            return None
        return None

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

    def _aggregate_project_global_conflicts(
        self,
        *,
        sections: List[Section],
        full_text: str,
        project_glossary: Glossary,
        global_glossary: Glossary,
        aggregated: Dict[str, AggregatedCandidate],
    ) -> None:
        for project_term in project_glossary.terms:
            if project_term.status != "active":
                continue
            global_term = global_glossary.get_term(project_term.original)
            if not global_term or global_term.status != "active":
                continue
            if not self._glossary_terms_conflict(project_term, global_term):
                continue
            if _safe_count_occurrences(full_text, project_term.original) <= 0:
                continue

            candidate = self._candidate_for_existing_term(
                term=project_term,
                sections=sections,
                aggregated=aggregated,
                reason="project_global_conflict",
            )
            self._add_existing_term(candidate, project_term)
            self._add_existing_term(candidate, global_term)

    def _candidate_for_existing_term(
        self,
        *,
        term: GlossaryTerm,
        sections: List[Section],
        aggregated: Dict[str, AggregatedCandidate],
        reason: str,
    ) -> AggregatedCandidate:
        normalized = _normalize_term(term.original)
        candidate = aggregated.setdefault(
            normalized,
            AggregatedCandidate(term=term.original),
        )
        candidate.term = candidate.term or term.original
        if term.translation:
            candidate.suggested_translations[term.translation] += 1
        self._add_force_reason(candidate, reason)

        for section in sections:
            section_text = "\n".join(paragraph.source for paragraph in section.paragraphs)
            matches = _safe_count_occurrences(section_text, term.original)
            if matches <= 0:
                continue
            if section.section_id not in candidate.section_ids:
                candidate.section_ids.append(section.section_id)
            candidate.section_titles[section.section_id] = section.title
            candidate.total_occurrences += matches
            context = self._context_for_term(section_text, term.original)
            if context and context not in candidate.contexts:
                candidate.contexts.append(context)

        return candidate

    def _context_for_term(self, text: str, term: str) -> str:
        normalized = text.lower()
        needle = term.lower().strip()
        if not needle:
            return ""
        index = normalized.find(needle)
        if index < 0:
            return ""
        start = max(0, index - 90)
        end = min(len(text), index + len(term) + 90)
        return re.sub(r"\s+", " ", text[start:end]).strip()

    def _term_suggestion_conflicts(
        self,
        existing_term: GlossaryTerm,
        suggested_translation: str,
    ) -> bool:
        suggested = (suggested_translation or "").strip()
        if not suggested:
            return False
        existing = (existing_term.translation or existing_term.original).strip()
        return _normalize_term(suggested) != _normalize_term(existing)

    def _glossary_terms_conflict(
        self,
        project_term: GlossaryTerm,
        global_term: GlossaryTerm,
    ) -> bool:
        return (
            _normalize_term(project_term.translation or project_term.original)
            != _normalize_term(global_term.translation or global_term.original)
            or project_term.strategy != global_term.strategy
        )

    def _add_existing_term(
        self,
        candidate: AggregatedCandidate,
        term: GlossaryTerm,
    ) -> None:
        if not any(
            _normalize_term(existing.original) == _normalize_term(term.original)
            and existing.scope == term.scope
            for existing in candidate.existing_terms
        ):
            candidate.existing_terms.append(term)

    def _add_force_reason(self, candidate: AggregatedCandidate, reason: str) -> None:
        if reason not in candidate.force_reasons:
            candidate.force_reasons.append(reason)

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
            suggested_translation_items = [
                {"translation": translation, "count": count}
                for translation, count in candidate.suggested_translations.most_common()
            ]
            suggested_translation = suggested_translation_items[0]["translation"] if suggested_translation_items else ""
            similar_terms = self._find_similar_terms(candidate.term, merged_glossary)
            for existing in candidate.existing_terms:
                existing_payload = {
                    "original": existing.original,
                    "translation": existing.translation,
                    "strategy": existing.strategy.value,
                    "scope": existing.scope,
                    "note": existing.note,
                    "similarity": 1.0,
                }
                if not any(
                    item.get("original", "").lower() == existing.original.lower()
                    and item.get("scope") == existing.scope
                    for item in similar_terms
                ):
                    similar_terms.insert(0, existing_payload)
            if not suggested_translation and candidate.existing_terms:
                suggested_translation = (
                    candidate.existing_terms[0].translation
                    or candidate.existing_terms[0].original
                )

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
                    "suggested_translations": suggested_translation_items,
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
                    "existing_terms": [
                        existing.model_dump(mode="json")
                        for existing in candidate.existing_terms
                    ],
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
            "schema_version": self.REVIEW_SCHEMA_VERSION,
            "project_id": project.id,
            "project_title": project.title,
            "model": self._llm_model_name(),
            "review_required": total_candidates > 0,
            "generated_at": datetime.now().isoformat(),
            "total_candidates": total_candidates,
            "sections": sections,
        }

    def _build_candidate_reasons(self, candidate: AggregatedCandidate) -> List[str]:
        reasons: List[str] = list(candidate.force_reasons)
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
