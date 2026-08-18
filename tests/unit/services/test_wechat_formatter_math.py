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


# --- 公式节点标记：供前端 MathJax 渲染成内嵌 SVG -------------------------------


def test_block_formula_carries_data_latex_without_delimiters(
    formatter: WechatFormatter,
) -> None:
    result = _render(formatter, BLOCK_FORMULA)
    html = result["html"]

    assert 'data-formula="block"' in html
    assert "data-latex=" in html
    # data-latex 里必须是纯 LaTeX，带上 $$ 会让 MathJax 解析失败
    unescaped = html_lib.unescape(html)
    assert 'data-latex="$$' not in unescaped
    assert r"\mathbf{o}_t" in unescaped


def test_inline_formula_carries_data_latex(formatter: WechatFormatter) -> None:
    result = _render(formatter, r"其中 $\alpha_{i}$ 是权重。")
    html = result["html"]

    assert 'data-formula="inline"' in html
    unescaped = html_lib.unescape(html)
    assert r"\alpha_{i}" in unescaped
    assert 'data-latex="$' not in unescaped


def test_fallback_content_kept_for_degraded_rendering(
    formatter: WechatFormatter,
) -> None:
    # 前端渲染器加载失败时，节点内容仍是等宽 LaTeX 原文，而不是空白
    result = _render(formatter, BLOCK_FORMULA)
    html = html_lib.unescape(result["html"])
    assert "<code" in result["html"]
    assert r"\sum_{i=1}^{t}" in html


@pytest.mark.parametrize(
    "raw,expected",
    [
        (r"$$ a_1 $$", "a_1"),
        (r"$a_1$", "a_1"),
        (r"\[ a_1 \]", "a_1"),
        (r"\( a_1 \)", "a_1"),
        ("a_1", "a_1"),
    ],
)
def test_strip_math_delimiters(raw: str, expected: str) -> None:
    assert WechatFormatter._strip_math_delimiters(raw) == expected


def test_backslash_artifact_repaired_before_rendering():
    """排版链路必须自己修 `\backslash ` 污染。

    导出走 postprocess_markdown 时会修，但公众号排版是另一条链路：用户往往直接
    把**早就生成好的**译文粘进来。不在这里修，`\mathbf{q}_l=\mathbf{w}_l` 就会
    带着 `\backslash ` 送进 MathJax，渲染成字面的 `\mathbfq\_l`（真实产物如此）。
    """
    polluted = r"每层学习一个查询向量：$\backslash mathbf{q}\backslash _l=\backslash mathbf{w}\backslash _l$"
    result = WechatFormatter().format(polluted, theme="default")
    html = result["html"]

    assert result["formula_count"] == 1
    assert 'data-latex="\\mathbf{q}_l=\\mathbf{w}_l"' in html
    assert "backslash" not in html


def test_legitimate_backslash_command_survives_formatting():
    """`\backslash` 是合法命令（集合差），单独一处不能被当成污染改掉。"""
    src = r"集合差记作 $A \backslash B$。"
    html = WechatFormatter().format(src, theme="default")["html"]
    assert r"A \backslash B" in html
