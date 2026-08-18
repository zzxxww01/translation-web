# -*- coding: utf-8 -*-
r"""公式在翻译链路里必须被 `[[[MATH_n|...]]]` 挡住，且还原时无条件用原文覆盖。

此前公式是当普通文本送进 prompt 的，模型改写过它：`\mathbf{q}_l=\mathbf{w}_l`
变成 `\backslash mathbf{q}\backslash _l=\backslash mathbf{w}\backslash _l`，
渲染出来是字面的 `\mathbfq\_l`（真实产物里出现过）。

排版层与后处理层的还原是事后补救；这里是根治：模型再怎么改，还原时都用
element.text 覆盖——和 `code` 类型同一策略。
"""

from src.core.format_tokens import (
    restore_markdown_from_tokenized,
    tokenize_text,
    validate_tokenized_text,
)
from src.core.markdown_project_parser import MarkdownProjectParser

FORMULA = r"$\mathbf{q}_l=\mathbf{w}_l$"
MANGLED = r"$\backslash mathbf{q}\backslash _l=\backslash mathbf{w}\backslash _l$"


def _extract(text: str):
    parser = MarkdownProjectParser.__new__(MarkdownProjectParser)
    return MarkdownProjectParser._extract_inline_elements(parser, text)


def test_formula_becomes_a_math_element():
    _, elements = _extract(f"每层学习一个查询向量 {FORMULA}。")
    assert [(item.type, item.text) for item in elements] == [("math", FORMULA)]


def test_formula_is_wrapped_as_token_for_the_model():
    plain, elements = _extract(f"每层学习一个查询向量 {FORMULA}。")
    tokenized = tokenize_text(plain, elements)
    assert f"[[[MATH_1|{FORMULA}]]]" in tokenized


def test_model_rewriting_the_formula_is_overridden():
    """核心保证：模型改写公式也没用，还原时用原文覆盖。"""
    plain, elements = _extract(f"每层学习一个查询向量 {FORMULA}。")
    tokenized = tokenize_text(plain, elements)
    model_output = tokenized.replace(FORMULA, MANGLED)

    restored = restore_markdown_from_tokenized(model_output, elements)
    assert FORMULA in restored
    assert "backslash" not in restored


def test_model_rewriting_the_formula_is_reported():
    plain, elements = _extract(f"每层学习一个查询向量 {FORMULA}。")
    tokenized = tokenize_text(plain, elements)
    model_output = tokenized.replace(FORMULA, MANGLED)

    issues = validate_tokenized_text(model_output, elements)
    assert any("MATH_1" in issue for issue in issues)


def test_surrounding_text_is_still_translated():
    """公式被保护，周围的正文与其他 token 该翻的照翻。"""
    source = f"每层学习 {FORMULA}，其中 **权重** 见 `config`。"
    plain, elements = _extract(source)
    tokenized = tokenize_text(plain, elements)
    model_output = tokenized.replace(FORMULA, MANGLED).replace("权重", "weights")

    restored = restore_markdown_from_tokenized(model_output, elements)
    assert FORMULA in restored          # 公式原样
    assert "**weights**" in restored    # 正文翻译生效
    assert "`config`" in restored       # 代码同样保持原文


def test_block_math_protected_too():
    block = r"$$\frac{a}{b}$$"
    plain, elements = _extract(f"如下：{block}")
    tokenized = tokenize_text(plain, elements)
    model_output = tokenized.replace(block, r"$$\backslash frac{a}{b}$$")

    restored = restore_markdown_from_tokenized(model_output, elements)
    assert block in restored


def test_currency_is_not_treated_as_math():
    """`$100 到 $200` 不是公式，不该被登记成 math token。"""
    _, elements = _extract(r"价格 $100 到 $200 之间")
    assert [item.type for item in elements] == []


def test_dollar_inside_inline_code_is_not_math():
    """行内代码里的 `$` 不参与公式配对。"""
    _, elements = _extract(r"执行 `echo $HOME` 即可")
    assert [item.type for item in elements] == ["code"]
