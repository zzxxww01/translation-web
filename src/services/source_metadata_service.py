"""Batch translation for longform source/citation metadata."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from src.core.constants import MAX_GLOSSARY_TERMS_IN_PROMPT
from src.core.format_tokens import (
    TranslationPayload,
    apply_translation_payload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
    format_token_context,
)
from src.core.glossary_prompt import (
    render_glossary_prompt_block,
    select_glossary_terms_for_text,
)
from src.core.models import Glossary, Paragraph, ProjectMeta, Section
from src.core.structured_metadata import STRUCTURED_METADATA_TYPES
from src.llm.base import LLMProvider


logger = logging.getLogger(__name__)


@dataclass
class SourceMetadataEntry:
    source_text: str
    prompt_text: str
    paragraph: Paragraph
    metadata_type: str


class SourceMetadataTranslationService:
    """Translate `Source:` metadata once per unique entry and reuse results."""

    BATCH_SIZE = 20
    SUPPORTED_METADATA_TYPES = STRUCTURED_METADATA_TYPES
    SOURCE_PREFIX_RE = re.compile(
        r"^(?P<label>sources?|data)\s*:\s*(?P<body>.*)$",
        re.IGNORECASE | re.DOTALL,
    )
    BYLINE_PREFIX_RE = re.compile(
        r"^By\s+(?P<body>.*)$",
        re.IGNORECASE | re.DOTALL,
    )
    BYLINE_OTHERS_RE = re.compile(r"\band\s+(?P<count>\d+)\s+others\b", re.IGNORECASE)
    DATE_ACCESS_RE = re.compile(
        r"^(?P<date>[A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})(?:\s+·\s+(?P<access>Paid|Free))?$"
    )
    COMMON_BODY_TRANSLATIONS = {
        "estimate": "估算",
        "estimates": "估算",
        "model": "模型",
        "database": "数据库",
        "analysis": "分析",
        "research": "研究",
        "filing": "文件",
        "filings": "文件",
        "sec filing": "SEC 文件",
        "sec filings": "SEC 文件",
        "company filing": "公司文件",
        "company filings": "公司文件",
        "company reports": "公司报告",
    }
    PREFIX_TRANSLATIONS = {
        "source": "来源：",
        "sources": "来源：",
        "data": "数据：",
    }
    ACCESS_TRANSLATIONS = {
        "paid": "付费文章",
        "free": "免费文章",
    }

    def __init__(self, project_manager, llm_provider: LLMProvider):
        self.project_manager = project_manager
        self.llm = llm_provider

    def translate_project_sources(
        self,
        project_id: str,
        sections: Optional[List[Section]] = None,
        artifact_dir: Optional[Path] = None,
    ) -> Dict[str, int]:
        sections = sections or self.project_manager.get_sections(project_id)
        if not sections:
            return self._empty_result()

        project = self.project_manager.get(project_id)
        glossary = self.project_manager.glossary_manager.load_merged(project_id)
        existing_cache = self._build_existing_cache(sections)

        pending_targets: Dict[str, List[Tuple[Section, Paragraph]]] = {}
        unique_entries: Dict[str, SourceMetadataEntry] = {}
        changed_sections: Dict[str, Section] = {}

        reused_count = 0
        rule_count = 0

        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.metadata_type not in self.SUPPORTED_METADATA_TYPES:
                    continue

                cached_payload = existing_cache.get(paragraph.source)
                if cached_payload is not None and not self._is_legacy_source_translation(
                    paragraph
                ):
                    if not paragraph.has_confirmed_translation():
                        self._apply_payload(paragraph, cached_payload)
                        changed_sections[section.section_id] = section
                        reused_count += 1
                    continue

                pending_targets.setdefault(paragraph.source, []).append((section, paragraph))
                unique_entries.setdefault(
                    paragraph.source,
                    self._build_entry(paragraph),
                )

        if not unique_entries:
            self._persist_changed_sections(project_id, changed_sections)
            return {
                "total": len(existing_cache),
                "translated": 0,
                "reused": reused_count,
                "rule_applied": rule_count,
                "llm_batches": 0,
            }

        resolved_payloads: Dict[str, TranslationPayload] = {}
        unresolved_entries: List[SourceMetadataEntry] = []

        for source_text, entry in unique_entries.items():
            payload = self._translate_with_rules(entry, glossary, project)
            if payload is not None:
                resolved_payloads[source_text] = payload
                rule_count += 1
            else:
                unresolved_entries.append(entry)

        llm_batches = 0
        for batch_start in range(0, len(unresolved_entries), self.BATCH_SIZE):
            batch_entries = unresolved_entries[batch_start : batch_start + self.BATCH_SIZE]
            if not batch_entries:
                continue

            batch_payloads = self._translate_batch_with_llm(batch_entries, glossary)
            resolved_payloads.update(batch_payloads)
            llm_batches += 1

        translated_count = 0
        for source_text, targets in pending_targets.items():
            payload = resolved_payloads.get(source_text)
            if payload is None:
                logger.warning("Source metadata translation missing for: %s", source_text)
                continue
            for section, paragraph in targets:
                self._apply_payload(paragraph, payload)
                changed_sections[section.section_id] = section
                translated_count += 1

        self._persist_changed_sections(project_id, changed_sections)
        self._write_artifact(
            artifact_dir,
            resolved_payloads=resolved_payloads,
            pending_targets=pending_targets,
        )

        return {
            "total": len(pending_targets) + len(existing_cache),
            "translated": translated_count,
            "reused": reused_count,
            "rule_applied": rule_count,
            "llm_batches": llm_batches,
        }

    def _empty_result(self) -> Dict[str, int]:
        return {
            "total": 0,
            "translated": 0,
            "reused": 0,
            "rule_applied": 0,
            "llm_batches": 0,
        }

    def _build_existing_cache(
        self,
        sections: Iterable[Section],
    ) -> Dict[str, TranslationPayload]:
        cache: Dict[str, TranslationPayload] = {}
        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.metadata_type not in self.SUPPORTED_METADATA_TYPES:
                    continue
                if not paragraph.has_confirmed_translation():
                    continue
                if self._is_legacy_source_translation(paragraph):
                    continue
                cache.setdefault(
                    paragraph.source,
                    TranslationPayload(
                        text=paragraph.confirmed or "",
                        tokenized_text=paragraph.confirmed_tokenized,
                        format_issues=list(paragraph.confirmed_format_issues),
                    ),
                )
        return cache

    def _build_entry(self, paragraph: Paragraph) -> SourceMetadataEntry:
        dehydrated_payload = build_dehydrated_link_payload(paragraph)
        if dehydrated_payload is not None and dehydrated_payload.tokenized_text:
            prompt_text = dehydrated_payload.tokenized_text
        else:
            prepared = build_translation_input(paragraph)
            prompt_text = prepared.tokenized_text or prepared.text
        return SourceMetadataEntry(
            source_text=paragraph.source,
            prompt_text=prompt_text,
            paragraph=paragraph,
            metadata_type=paragraph.metadata_type or "",
        )

    def _translate_with_rules(
        self,
        entry: SourceMetadataEntry,
        glossary: Glossary,
        project: ProjectMeta,
    ) -> Optional[TranslationPayload]:
        if entry.metadata_type == "subtitle":
            return self._translate_subtitle(entry, project)
        if entry.metadata_type == "byline":
            return self._translate_byline(entry)
        if entry.metadata_type == "date_access":
            return self._translate_date_access(entry)

        match = self.SOURCE_PREFIX_RE.match(entry.source_text.strip())
        if not match:
            return None

        label = (match.group("label") or "").strip().lower()
        body = (match.group("body") or "").strip()
        translated_prefix = self.PREFIX_TRANSLATIONS.get(label, "来源：")
        if not body:
            return self._build_payload(entry.paragraph, translated_prefix)

        glossary_term = glossary.get_term(body) if glossary else None
        if glossary_term and glossary_term.translation:
            translated_body = (
                glossary_term.original
                if glossary_term.strategy.value.startswith("preserve")
                else glossary_term.translation
            )
            return self._build_payload(entry.paragraph, f"{translated_prefix}{translated_body}")

        exact_body = self.COMMON_BODY_TRANSLATIONS.get(body.lower())
        if exact_body:
            return self._build_payload(entry.paragraph, f"{translated_prefix}{exact_body}")

        body_parts = body.rsplit(" ", 1)
        if len(body_parts) == 2:
            suffix_translation = self.COMMON_BODY_TRANSLATIONS.get(body_parts[1].lower())
            if suffix_translation:
                return self._build_payload(
                    entry.paragraph,
                    f"{translated_prefix}{body_parts[0]} {suffix_translation}",
                )

        return None

    def _translate_subtitle(
        self,
        entry: SourceMetadataEntry,
        project: ProjectMeta,
    ) -> Optional[TranslationPayload]:
        subtitle = (
            project.metadata.subtitle.strip()
            if project.metadata and isinstance(project.metadata.subtitle, str)
            else ""
        )
        if not subtitle or subtitle == entry.source_text.strip():
            return None
        return self._build_payload(entry.paragraph, subtitle)

    def _translate_byline(
        self,
        entry: SourceMetadataEntry,
    ) -> Optional[TranslationPayload]:
        source_text = entry.source_text.strip()
        match = self.BYLINE_PREFIX_RE.match(source_text)
        if not match:
            return None

        body = (match.group("body") or "").strip()
        if not body:
            return self._build_payload(entry.paragraph, "作者：")

        others_match = self.BYLINE_OTHERS_RE.search(body)
        others_count = int(others_match.group("count")) if others_match else 0
        body_without_others = self.BYLINE_OTHERS_RE.sub("", body)
        body_without_others = re.sub(r"\s*,\s*$", "", body_without_others).strip()

        tokenized_names = self._extract_byline_names(entry.paragraph)
        total_count = len(tokenized_names) + others_count

        if tokenized_names:
            translated = f"作者：{'、'.join(tokenized_names)}"
            if others_count:
                translated += f" 等 {total_count} 人"
            return self._build_payload(entry.paragraph, translated)

        plain_names = self._split_plain_byline_names(body_without_others)
        if not plain_names and others_count:
            return self._build_payload(entry.paragraph, f"作者：等 {others_count} 人")
        if not plain_names:
            return None

        translated = f"作者：{'、'.join(plain_names)}"
        if others_count:
            translated += f" 等 {len(plain_names) + others_count} 人"
        return self._build_payload(entry.paragraph, translated)

    def _translate_date_access(
        self,
        entry: SourceMetadataEntry,
    ) -> Optional[TranslationPayload]:
        source_text = entry.source_text.strip()
        match = self.DATE_ACCESS_RE.match(source_text)
        if not match:
            return None

        translated_date = self._translate_english_date(match.group("date") or "")
        if not translated_date:
            return None

        access_text = (match.group("access") or "").strip().lower()
        translated_access = self.ACCESS_TRANSLATIONS.get(access_text)
        translated = translated_date
        if translated_access:
            translated = f"{translated} · {translated_access}"
        return self._build_payload(entry.paragraph, translated)

    def _extract_byline_names(
        self,
        paragraph: Paragraph,
    ) -> List[str]:
        if not paragraph.inline_elements:
            return []

        tokenized_source = build_translation_input(paragraph).tokenized_text or paragraph.source
        ordered_tokens = re.findall(r"\[\[\[(LINK_\d+)\|.*?\]\]\]", tokenized_source)
        if not ordered_tokens:
            return []

        token_lookup = {}
        for match in re.finditer(
            r"\[\[\[(LINK_\d+)\|(?P<text>.*?)\]\]\]",
            tokenized_source,
        ):
            token_lookup[match.group(1)] = match.group("text").strip()

        tokenized_names: List[str] = []
        for token_id in ordered_tokens:
            token_text = token_lookup.get(token_id, "")
            if not token_text:
                continue
            tokenized_names.append(f"[[[{token_id}|{token_text}]]]")
        return tokenized_names

    def _split_plain_byline_names(self, source_text: str) -> List[str]:
        normalized = re.sub(r"\band\b", ",", source_text, flags=re.IGNORECASE)
        return [
            item.strip()
            for item in normalized.split(",")
            if item and item.strip()
        ]

    def _translate_english_date(self, source_text: str) -> Optional[str]:
        normalized = source_text.strip()
        if not normalized:
            return None

        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                value = datetime.strptime(normalized, fmt)
                return f"{value.year} 年 {value.month} 月 {value.day} 日"
            except ValueError:
                continue
        return None

    def _translate_batch_with_llm(
        self,
        entries: List[SourceMetadataEntry],
        glossary: Glossary,
    ) -> Dict[str, TranslationPayload]:
        request_items = [
            {
                "id": f"s{index + 1:03d}",
                "text": entry.prompt_text,
            }
            for index, entry in enumerate(entries)
        ]
        glossary_block = self._build_glossary_block(glossary, entries)
        translated_items = self.llm.translate_source_metadata_batch(
            request_items,
            context={"glossary_block": glossary_block},
        )

        translated_map = {
            str(item.get("id", "")).strip(): str(item.get("translation", "")).strip()
            for item in translated_items
            if str(item.get("id", "")).strip()
        }

        payloads: Dict[str, TranslationPayload] = {}
        for index, entry in enumerate(entries):
            item_id = f"s{index + 1:03d}"
            translated = translated_map.get(item_id)
            if not translated:
                logger.warning("Missing source metadata batch item: %s", item_id)
                continue
            payloads[entry.source_text] = self._build_payload(entry.paragraph, translated)
        return payloads

    def _build_glossary_block(
        self,
        glossary: Glossary,
        entries: List[SourceMetadataEntry],
    ) -> str:
        joined_text = "\n".join(entry.source_text for entry in entries)
        selected_terms = select_glossary_terms_for_text(
            glossary,
            joined_text,
            max_terms=MAX_GLOSSARY_TERMS_IN_PROMPT,
        )
        return render_glossary_prompt_block(
            selected_terms,
            include_title=False,
            empty_text="(无命中术语)",
        )

    def _build_payload(
        self,
        paragraph: Paragraph,
        translated_text: str,
    ) -> TranslationPayload:
        normalized_text = self._normalize_final_translation(translated_text)
        return build_translation_payload(
            paragraph,
            normalized_text,
            token_repairer=self._repair_format_tokens,
        )

    def _repair_format_tokens(
        self,
        paragraph: Paragraph,
        translated_tokenized_text: str,
        issues: List[str],
    ) -> Optional[str]:
        if not paragraph.inline_elements:
            return None

        prepared = build_translation_input(paragraph)
        return self.llm.repair_format_tokens(
            source_text=prepared.tokenized_text or prepared.text,
            translated_text=translated_tokenized_text,
            format_tokens=format_token_context(paragraph),
            issues=issues,
        )

    def _apply_payload(self, paragraph: Paragraph, payload: TranslationPayload) -> None:
        apply_translation_payload(paragraph, payload, "source_metadata")
        paragraph.confirm(
            payload.text,
            "source_metadata",
            tokenized_text=payload.tokenized_text,
            format_issues=payload.format_issues,
        )

    def _persist_changed_sections(
        self,
        project_id: str,
        changed_sections: Dict[str, Section],
    ) -> None:
        for section in changed_sections.values():
            self.project_manager.save_section(project_id, section)

    def _write_artifact(
        self,
        artifact_dir: Optional[Path],
        *,
        resolved_payloads: Dict[str, TranslationPayload],
        pending_targets: Dict[str, List[Tuple[Section, Paragraph]]],
    ) -> None:
        if artifact_dir is None:
            return

        artifact_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "items": [
                {
                    "source": source_text,
                    "translation": payload.text,
                    "tokenized_translation": payload.tokenized_text,
                    "format_issues": payload.format_issues,
                    "occurrences": len(pending_targets.get(source_text, [])),
                }
                for source_text, payload in sorted(resolved_payloads.items())
            ]
        }
        with open(artifact_dir / "source-metadata.json", "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _normalize_final_translation(self, translated_text: str) -> str:
        normalized = str(translated_text or "").strip()
        normalized = re.sub(r"^来源：\s+", "来源：", normalized)
        normalized = re.sub(r"^数据：\s+", "数据：", normalized)
        return normalized

    def _is_legacy_source_translation(self, paragraph: Paragraph) -> bool:
        if paragraph.metadata_type != "source" or not paragraph.confirmed:
            return False
        if "source_metadata" in paragraph.translations:
            return False
        match = self.SOURCE_PREFIX_RE.match(paragraph.source.strip())
        if not match:
            return False

        label = (match.group("label") or "").strip().lower()
        translated_prefix = self.PREFIX_TRANSLATIONS.get(label, "来源：")
        legacy_translation = f"{translated_prefix}{(match.group('body') or '').strip()}"
        return paragraph.confirmed.strip() == legacy_translation.strip()
