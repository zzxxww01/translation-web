# -*- coding: utf-8 -*-
"""分档重译：resume / section / all 三种范围的过滤语义。

在此之前 _build_translatable_section 无条件跳过已有译文的段落，导致系统**根本无法
重译**——点「全文一键翻译」永远只处理未译段落，用户要重来只能逐段重译或删项目。
"""

import pytest

from src.core.models import Paragraph, Section
from src.services.batch_translation_service import BatchTranslationService
from src.services.section_translation_executor import SectionTranslationExecutor


def _section(section_id: str = "s1") -> Section:
    return Section(
        section_id=section_id,
        title="Demo",
        paragraphs=[
            Paragraph(id="p1", index=0, source="hello", confirmed="你好"),
            Paragraph(id="p2", index=1, source="world"),
        ],
    )


def test_default_keeps_only_untranslated_paragraphs() -> None:
    result = SectionTranslationExecutor._build_translatable_section(_section())
    assert [p.id for p in result.paragraphs] == ["p2"]


def test_force_keeps_translated_paragraphs_too() -> None:
    result = SectionTranslationExecutor._build_translatable_section(
        _section(), force=True
    )
    assert [p.id for p in result.paragraphs] == ["p1", "p2"]


def test_scope_resume_forces_nothing() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    service._retranslate_scope = "resume"
    service._retranslate_section_ids = set()
    assert service._should_force_retranslate(_section("s1")) is False


def test_scope_all_forces_every_section() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    BatchTranslationService.set_retranslate_scope(service, "all")
    assert service._should_force_retranslate(_section("s1")) is True
    assert service._should_force_retranslate(_section("s9")) is True


def test_scope_section_forces_only_listed_sections() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    BatchTranslationService.set_retranslate_scope(service, "section", ["s2"])
    assert service._should_force_retranslate(_section("s2")) is True
    assert service._should_force_retranslate(_section("s1")) is False


def test_scope_section_requires_ids() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    with pytest.raises(ValueError):
        BatchTranslationService.set_retranslate_scope(service, "section")


def test_unknown_scope_rejected() -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    with pytest.raises(ValueError):
        BatchTranslationService.set_retranslate_scope(service, "everything")


def test_structured_metadata_never_retranslated_even_when_forced() -> None:
    # 署名/副标题/来源/日期这类结构化元数据段走专门的元数据翻译链路，
    # 正文重译不得把它们卷进来重复计费。
    section = Section(
        section_id="s1",
        title="Demo",
        paragraphs=[
            Paragraph(
                id="meta1",
                index=0,
                source="By Doug O'Laughlin",
                is_metadata=True,
                metadata_type="byline",
                confirmed="作者：Doug O'Laughlin",
            ),
            Paragraph(id="p1", index=1, source="hello", confirmed="你好"),
        ],
    )
    result = SectionTranslationExecutor._build_translatable_section(section, force=True)
    assert [p.id for p in result.paragraphs] == ["p1"]
