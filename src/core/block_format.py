"""块级 markdown 前缀的剥离与还原（导出层职责）。

约定：**结构标记由导出层负责补齐，模型只输出纯文本**。因此渲染前必须先
剥掉译文里模型自作主张带上的列表符号/引用前缀，否则会得到 `- - 文本`、
`> > 文本` 这类双前缀；反过来，原文本身携带的有序编号是正文内容，模型
吃掉了要补回来。
"""

from __future__ import annotations

import re


# 行首的列表符号（可重复，模型偶尔会写 `- - `）。
_LIST_PREFIX = re.compile(r"^\s*(?:[-*+]\s+)+")
# 行首的引用前缀（可重复）。
_QUOTE_PREFIX = re.compile(r"^\s*(?:>\s?)+")
# 有序列表编号：`1. ` / `2) `。
_ORDERED_NUMBER = re.compile(r"^\s*(\d+[.)])\s+")


def strip_list_prefix(text: str) -> str:
    return _LIST_PREFIX.sub("", text or "", count=1)


def strip_quote_prefix(text: str) -> str:
    return _QUOTE_PREFIX.sub("", text or "", count=1)


def render_list_item(text: str, indent: int = 0) -> str:
    """渲染列表项：剥掉译文自带的符号，按缩进层级补 `- `。"""
    return f"{'  ' * max(0, indent)}- {strip_list_prefix(text).lstrip()}"


def render_blockquote(text: str) -> str:
    """渲染引用块：**逐行**补 `> `，多行引用不能只有首行带前缀。"""
    lines = (text or "").split("\n")
    return "\n".join(f"> {strip_quote_prefix(line).rstrip()}".rstrip() for line in lines)


def restore_ordered_number(source_text: str, translated_text: str) -> str:
    """原文有有序编号而译文丢了，就把编号补回。

    有序列表项在解析时是普通段落（编号留在待译文本里），模型经常把
    「1. 」当成格式标记吃掉，导致导出后条目失去序号。
    """
    source_match = _ORDERED_NUMBER.match(source_text or "")
    if not source_match:
        return translated_text
    if not translated_text or _ORDERED_NUMBER.match(translated_text):
        return translated_text
    return f"{source_match.group(1)} {translated_text.lstrip()}"
