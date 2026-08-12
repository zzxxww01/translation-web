# -*- coding: utf-8 -*-
"""微信排版的数学公式保真。

CommonMark 不认 `$$`，而公式里的下标 `_` 会被 markdown-it 当成强调定界符成对吞掉：
    `\\mathbf{v}_i, \\qquad \\alpha_{i\\to t}`
    → `\\mathbf{v}<em>i, \\qquad \\alpha</em>{i\\to t}`
公式既丢字符又多出 <em>。公式必须在 render 之前摘出来。
"""

import html as html_lib

import pytest

from src.services.wechat_formatter import WechatFormatter


BLOCK_FORMULA = (
    r"$$ \mathbf{o}_t = \sum_{i=1}^{t} \alpha_{i\rightarrow t}\,\mathbf{v}_i, "
    r"\qquad \alpha_{i\rightarrow t} = "
    r"\frac{\phi(\mathbf{q}_t,\mathbf{k}_i)}{\sum_{j=1}^{t}\phi(\mathbf{q}_t,\mathbf{k}_j)} $$"
)


@pytest.fixture
def formatter() -> WechatFormatter:
    return WechatFormatter()


def _render(formatter: WechatFormatter, markdown: str) -> dict:
    return formatter.format(markdown, upload_images=False, image_to_base64=False)


def test_block_formula_keeps_every_subscript(formatter: WechatFormatter) -> None:
    result = _render(formatter, f"正文\n\n{BLOCK_FORMULA}\n\n后文")
    html = html_lib.unescape(result["html"])

    for fragment in (
        r"\mathbf{o}_t",
        r"\sum_{i=1}^{t}",
        r"\alpha_{i\rightarrow t}",
        r"\mathbf{v}_i",
        r"\mathbf{k}_i",
        r"\sum_{j=1}^{t}",
    ):
        assert fragment in html, fragment


def test_block_formula_is_not_polluted_by_emphasis(formatter: WechatFormatter) -> None:
    result = _render(formatter, BLOCK_FORMULA)
    assert "<em>" not in result["html"]
    assert result["formula_count"] == 1


def test_inline_formula_preserved_and_emphasis_still_works(
    formatter: WechatFormatter,
) -> None:
    result = _render(
        formatter,
        r"其中 $\alpha_{i\rightarrow t}$ 是权重，这是 *真斜体* 与 _另一个斜体_。",
    )
    html = html_lib.unescape(result["html"])

    assert r"\alpha_{i\rightarrow t}" in html
    assert "<em>真斜体</em>" in html
    assert "<em>另一个斜体</em>" in html


def test_currency_pair_is_not_treated_as_formula(formatter: WechatFormatter) -> None:
    # 闭定界符后紧跟数字 → 按 Pandoc 规则不是公式，否则整段中文会被吞进公式框
    result = _render(formatter, "价格区间是 $100 到 $200，很贵。")
    assert result["formula_count"] == 0
    assert "到" in result["html"]


def test_block_formula_not_nested_inside_paragraph(formatter: WechatFormatter) -> None:
    # <section> 嵌进 <p> 是非法 HTML，微信编辑器会把它拆坏
    result = _render(formatter, f"引子\n\n{BLOCK_FORMULA}\n\n结尾")
    assert "<p><section" not in result["html"]


def test_markdown_without_math_is_unaffected(formatter: WechatFormatter) -> None:
    result = _render(formatter, "# 标题\n\n普通段落，含 *强调*。")
    assert result["formula_count"] == 0
    assert "<em>强调</em>" in result["html"]
