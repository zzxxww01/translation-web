"""回归测试：markdown 安全后处理不得误伤代码/表格/含括号链接。

此前 postprocess 只保护围栏代码与单行内联代码，缩进代码块、表格单元格里的
`$ < >` 会被转义破坏；链接正则 `[^)]+` 遇到 href 含 `)` 会提前截断。
"""

from src.core.markdown_postprocess import postprocess_markdown


def test_indented_code_block_not_escaped():
    src = "正文\n\n    total = $price + tax\n    if a < b > c:\n\n结束"
    out = postprocess_markdown(src)
    assert "total = $price + tax" in out
    assert "if a < b > c:" in out
    assert "\\$price" not in out
    assert "&lt;" not in out


def test_table_cells_not_escaped():
    src = "| 名称 | 表达式 |\n| --- | --- |\n| A | a < b |\n| B | $5 |"
    out = postprocess_markdown(src)
    assert "a < b" in out
    assert "$5" in out
    assert "&lt;" not in out
    assert "\\$5" not in out


def test_link_with_parentheses_preserved():
    src = "见 [维基](https://en.wikipedia.org/wiki/Foo_(bar)) 链接"
    out = postprocess_markdown(src)
    assert "[维基](https://en.wikipedia.org/wiki/Foo_(bar))" in out


def test_image_with_parentheses_preserved():
    src = "![图](https://x.com/a_(1).png)"
    out = postprocess_markdown(src)
    assert "![图](https://x.com/a_(1).png)" in out


def test_normal_text_still_escaped():
    # 注意：mid-line `>` 仅在紧邻非空格字符时才转义（既有行为），故用 a>b
    src = "价格是 $5 且 a < b 还有 a>b"
    out = postprocess_markdown(src)
    assert "\\$5" in out
    assert "a &lt; b" in out
    assert "a&gt;b" in out


def test_idempotent():
    src = "正文 $5 a < b\n\n    code = $x\n\n| c | $1 |"
    once = postprocess_markdown(src)
    twice = postprocess_markdown(once)
    assert once == twice
