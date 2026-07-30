"""Markdown 表格译文的结构校验与渲染。

表格块在解析时是**整表一个 Paragraph**（``_segments_from_block`` 对
TABLE 恒返回单段），所以译文也是一整张表的 markdown。历史实现无条件回吐
英文源表——表格被送去翻译并计费，成品却仍是英文。

这里的原则是「校验通过才采用译文」：模型改坏表格结构（少一行、少一列、
丢掉分隔行）的代价远大于表格没被翻译，因此任何结构不一致都回退英文源表
并记 warning，绝不把损坏的表格写进成品。
"""

from __future__ import annotations

import re
from typing import List, Optional


# 表格分隔行：`|---|:--:|` 这类只由 `-`、`:`、`|`、空白组成的行。
_SEPARATOR_ROW = re.compile(r"^[\s|:\-]+$")


def _table_rows(markdown: str) -> List[str]:
    return [line.strip() for line in (markdown or "").strip().split("\n") if line.strip()]


def _row_shape(row: str) -> tuple[int, bool]:
    """一行的结构指纹：竖线数量 + 是否分隔行。"""
    return row.count("|"), bool(_SEPARATOR_ROW.match(row))


def tables_structurally_equal(source_markdown: str, translated_markdown: str) -> bool:
    """译文表格与源表结构是否完全一致。

    比较行数、每行竖线数、分隔行所在位置。单元格文本内容不比较——那正是
    翻译要改的东西。
    """
    source_rows = _table_rows(source_markdown)
    translated_rows = _table_rows(translated_markdown)
    if not source_rows or len(source_rows) != len(translated_rows):
        return False
    return all(
        _row_shape(src) == _row_shape(dst)
        for src, dst in zip(source_rows, translated_rows)
    )


def render_table_markdown(
    translated: Optional[str],
    source_markdown: Optional[str],
    *,
    on_reject=None,
) -> Optional[str]:
    """采用结构校验通过的表格译文，否则回退源表。

    ``on_reject`` 在译文存在但被判定结构不一致时调用（用于记 warning），
    签名为 ``(reason: str) -> None``。返回 ``None`` 表示两侧都没有内容，
    由调用方决定更下层的兜底。
    """
    translated = (translated or "").strip()
    source_markdown = (source_markdown or "").strip()

    if not translated:
        return source_markdown or None
    if not source_markdown:
        # 没有源表可比对时不敢采用译文（无法判断结构是否被改坏）。
        return None
    if tables_structurally_equal(source_markdown, translated):
        return translated

    if on_reject is not None:
        on_reject(
            f"表格译文结构与原表不一致（源 {len(_table_rows(source_markdown))} 行 / "
            f"译文 {len(_table_rows(translated))} 行），回退英文原表"
        )
    return source_markdown
