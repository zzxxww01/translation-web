# -*- coding: utf-8 -*-
"""内联强调解析必须尊重反斜杠转义。

html2md（markdownify）会把原文里的字面 `*` `_` 转义成 `\\*` `\\_`。解析器若不认
转义，就会把它们当成强调定界符：字面符号丢失，还会凭空造出一个假的 em/strong
token 送进 prompt 与译文。LaTeX 下标（`P\\_{max}`）是受害最严重的场景——`_` 的
后置守卫只挡字母数字，`_{` 会被放行，于是假 em 可以跨越多个变量。
"""

from src.core.markdown_project_parser import MarkdownProjectParser


def _extract(text: str):
    parser = MarkdownProjectParser.__new__(MarkdownProjectParser)
    return MarkdownProjectParser._extract_inline_elements(parser, text)


def test_escaped_asterisks_are_literal():
    plain, elements = _extract(r"转义星号 \*not italic\* 结束")
    assert plain == r"转义星号 \*not italic\* 结束"
    assert elements == []


def test_escaped_underscores_are_literal():
    plain, elements = _extract(r"Ryan Dahl@rough\_\_sea")
    assert plain == r"Ryan Dahl@rough\_\_sea"
    assert elements == []


def test_latex_subscript_with_braces_survives():
    # 旧行为：'数学 P\\{max} 与 V\\{dd}' + 一个跨越两个变量的假 em。
    plain, elements = _extract(r"数学 P\_{max} 与 V\_{dd}")
    assert plain == r"数学 P\_{max} 与 V\_{dd}"
    assert elements == []


def test_escaped_backtick_not_treated_as_code():
    plain, elements = _extract(r"字面反引号 \`not code\` 结束")
    assert plain == r"字面反引号 \`not code\` 结束"
    assert elements == []


def test_real_emphasis_still_parsed():
    plain, elements = _extract("真斜体 *italic* 与真粗体 **bold**")
    assert plain == "真斜体 italic 与真粗体 bold"
    assert [(item.type, item.text) for item in elements] == [
        ("em", "italic"),
        ("strong", "bold"),
    ]


def test_real_underscore_emphasis_still_parsed():
    plain, elements = _extract("下划线斜体 _italic_ 正常")
    assert plain == "下划线斜体 italic 正常"
    assert [(item.type, item.text) for item in elements] == [("em", "italic")]


def test_snake_case_identifier_still_protected():
    plain, elements = _extract("snake_case_identifier 不该被吃")
    assert plain == "snake_case_identifier 不该被吃"
    assert elements == []


def test_escaped_and_real_emphasis_coexist():
    plain, elements = _extract(r"混合 \_escaped_ 与 _real_")
    assert plain == r"混合 \_escaped_ 与 real"
    assert [(item.type, item.text) for item in elements] == [("em", "real")]


def test_inline_code_still_parsed():
    plain, elements = _extract("执行 `pip install` 即可")
    assert plain == "执行 pip install 即可"
    assert [(item.type, item.text) for item in elements] == [("code", "pip install")]


def test_display_math_subscripts_survive():
    # 用户实测案例：LaTeX 下标的 `_` 被当成斜体定界符成对吞掉，
    # `\mathbf{v}_i, \qquad \alpha_` 整段变成一个假 em。
    formula = (
        r"$$ \mathbf{o}_t = \sum_{i=1}^{t} \alpha_{i\rightarrow t}\,\mathbf{v}_i, "
        r"\qquad \alpha_{i\rightarrow t} = "
        r"\frac{\phi(\mathbf{q}_t,\mathbf{k}_i)}{\sum_{j=1}^{t}\phi(\mathbf{q}_t,\mathbf{k}_j)} $$"
    )
    plain, elements = _extract(formula)
    assert plain == formula
    assert elements == []


def test_inline_math_subscripts_survive():
    plain, elements = _extract(r"其中 $\alpha_{i} + \beta_{j}$ 与 $x_1 + y_2$ 成立")
    assert plain == r"其中 $\alpha_{i} + \beta_{j}$ 与 $x_1 + y_2$ 成立"
    assert elements == []


def test_paren_math_subscripts_survive():
    plain, elements = _extract(r"满足 \(P_{max} = V_{dd} \times I\) 的条件")
    assert plain == r"满足 \(P_{max} = V_{dd} \times I\) 的条件"
    assert elements == []


def test_emphasis_outside_math_still_parsed():
    plain, elements = _extract(r"公式 $a_i$ 之外的 _真斜体_ 仍要解析")
    assert plain == r"公式 $a_i$ 之外的 真斜体 仍要解析"
    assert [(item.type, item.text) for item in elements] == [("em", "真斜体")]


def test_currency_pair_is_not_math_and_does_not_swallow_emphasis():
    # 闭定界符后跟数字 → 不是公式；这一段里的 _斜体_ 仍应正常解析
    plain, elements = _extract(r"价格 $100 到 $200，其中 _重点_ 在这里")
    assert plain == r"价格 $100 到 $200，其中 重点 在这里"
    assert [(item.type, item.text) for item in elements] == [("em", "重点")]


def test_dollar_inside_inline_code_does_not_open_math():
    plain, elements = _extract(r"执行 `echo $HOME` 然后看 _斜体_")
    assert plain == r"执行 echo $HOME 然后看 斜体"
    assert [(item.type, item.text) for item in elements] == [
        ("code", "echo $HOME"),
        ("em", "斜体"),
    ]


def test_link_still_parsed():
    plain, elements = _extract("参见 [文档](https://example.com/a_b_c) 了解详情")
    assert plain == "参见 文档 了解详情"
    assert elements[0].type == "link"
    assert elements[0].href == "https://example.com/a_b_c"
