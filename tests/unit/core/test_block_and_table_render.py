# -*- coding: utf-8 -*-
"""导出层块结构还原：表格译文采用、列表缩进、引用块、有序编号。"""

from src.core.block_format import (
    render_blockquote,
    render_list_item,
    restore_ordered_number,
)
from src.core.inline_recovery_service import InlineRecoveryService
from src.core.models import ElementType, Paragraph
from src.core.table_render import render_table_markdown, tables_structurally_equal


_EN_TABLE = "| Metric | 2025 |\n|---|---|\n| Revenue | $12B |"
_ZH_TABLE = "| 指标 | 2025 |\n|---|---|\n| 营收 | 120 亿美元 |"


def _table_paragraph(translation: str | None) -> Paragraph:
    return Paragraph(
        id="p1",
        index=0,
        source=_EN_TABLE,
        element_type=ElementType.TABLE,
        parent_block_type=ElementType.TABLE,
        parent_block_markdown=_EN_TABLE,
        confirmed=translation,
    )


# --- 表格 -------------------------------------------------------------


def test_structurally_equal_tables_are_accepted():
    assert tables_structurally_equal(_EN_TABLE, _ZH_TABLE)
    assert render_table_markdown(_ZH_TABLE, _EN_TABLE) == _ZH_TABLE


def test_row_count_mismatch_falls_back_to_source():
    broken = "| 指标 | 2025 |\n|---|---|"  # 少一行
    assert not tables_structurally_equal(_EN_TABLE, broken)
    assert render_table_markdown(broken, _EN_TABLE) == _EN_TABLE


def test_column_count_mismatch_falls_back_to_source():
    broken = "| 指标 | 2025 | 备注 |\n|---|---|---|\n| 营收 | 120 亿 | - |"
    assert render_table_markdown(broken, _EN_TABLE) == _EN_TABLE


def test_separator_row_moved_falls_back_to_source():
    broken = "| 指标 | 2025 |\n| 营收 | 120 亿美元 |\n|---|---|"
    assert render_table_markdown(broken, _EN_TABLE) == _EN_TABLE


def test_empty_translation_falls_back_to_source():
    assert render_table_markdown("", _EN_TABLE) == _EN_TABLE
    assert render_table_markdown(None, _EN_TABLE) == _EN_TABLE


def test_export_renders_translated_table():
    service = InlineRecoveryService()
    rendered = service.render_block_markdown([_table_paragraph(_ZH_TABLE)])
    assert rendered == _ZH_TABLE


def test_export_falls_back_and_records_when_table_structure_broken():
    service = InlineRecoveryService()
    service.reset_fallback_stats()
    rendered = service.render_block_markdown([_table_paragraph("译文乱了")])
    assert rendered == _EN_TABLE
    assert service.fallback_block_ids  # 回退必须留痕


# --- 列表 / 引用 / 有序编号 -------------------------------------------


def test_list_item_keeps_indent_level():
    assert render_list_item("一级项", 0) == "- 一级项"
    assert render_list_item("二级项", 1) == "  - 二级项"
    assert render_list_item("三级项", 2) == "    - 三级项"


def test_list_item_strips_model_added_prefix():
    # 模型自作主张带上的列表符号必须剥掉，否则导出成 `- - 文本`。
    assert render_list_item("- 文本", 0) == "- 文本"
    assert render_list_item("* 文本", 1) == "  - 文本"


def test_blockquote_prefixes_every_line():
    assert render_blockquote("第一行\n第二行") == "> 第一行\n> 第二行"
    assert render_blockquote("> 已带前缀") == "> 已带前缀"


def test_ordered_number_restored_when_model_drops_it():
    assert restore_ordered_number("1. First item", "第一个条目") == "1. 第一个条目"
    assert restore_ordered_number("2) Second", "第二个") == "2) 第二个"


def test_ordered_number_not_duplicated():
    assert restore_ordered_number("1. First", "1. 第一个") == "1. 第一个"


def test_ordered_number_untouched_for_plain_paragraph():
    assert restore_ordered_number("A plain sentence.", "一句普通的话。") == "一句普通的话。"
