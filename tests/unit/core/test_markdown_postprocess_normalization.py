# -*- coding: utf-8 -*-
"""确定性收尾层回归测试：全/半角标点归一、引号配对、转义残留、嵌套占位符还原。

对应 15 篇实证审计的头号落选原因（分块拼接后的标点漂移、GTC 引号同向 bug、
URL 内 ``\\&``、``\\@`` 残留、千分位混入中文量级数字、叠写标点）。
"""

from src.core.markdown_postprocess import postprocess_markdown


def test_halfwidth_punct_in_chinese_context_converted():
    src = "这是一段中文,后面还有中文;以及:结尾!对吗?好"
    out = postprocess_markdown(src)
    assert "中文，后面" in out
    assert "中文；以及" in out
    assert "以及：结尾" in out
    assert "结尾！对吗" in out
    assert "对吗？好" in out


def test_halfwidth_punct_with_trailing_space_consumed():
    out = postprocess_markdown("资本支出, 而且还在增长")
    assert "资本支出，而且" in out


def test_halfwidth_punct_before_latin_converted():
    out = postprocess_markdown("参数如下:GB300 与 MI355X")
    assert "如下：GB300" in out


def test_latin_context_punct_untouched():
    out = postprocess_markdown("Q1 revenue grew 31%, beating estimates.")
    assert "31%, beating" in out


def test_paren_after_cjk_converted():
    out = postprocess_markdown("英伟达(NVIDIA)今日发布")
    assert "英伟达（NVIDIA）" in out


def test_paren_with_cjk_inner_converted():
    out = postprocess_markdown("the plan (详见附录) is final")
    assert "（详见附录）" in out


def test_pure_english_paren_untouched():
    out = postprocess_markdown("See the appendix (Figure 3) for details.")
    assert "(Figure 3)" in out


def test_thousands_separator_before_cjk_magnitude_removed():
    out = postprocess_markdown("估值 2,600 万美元，产能 1,000 亿")
    assert "2600 万" in out
    assert "1000 亿" in out
    assert "2,600" not in out


def test_plain_thousands_separator_kept():
    out = postprocess_markdown("total of 12,600 units shipped")
    assert "12,600" in out


def test_doubled_fullwidth_punct_collapsed():
    out = postprocess_markdown("宇树科技表示：：机器人已量产。。没错，，真的")
    assert "：：" not in out
    assert "。。" not in out
    assert "，，" not in out


def test_straight_quotes_paired():
    out = postprocess_markdown('黄仁勋说"我们赢了"然后离场')
    assert "“我们赢了”" in out


def test_single_direction_quotes_repaired():
    # GTC 2026 指纹 bug：全文开引号 0 命中、引号两侧同向
    out = postprocess_markdown("他说”很好”，后来又说”不行”")
    assert "“很好”" in out
    assert "“不行”" in out
    assert out.count("“") == out.count("”")


def test_odd_quote_count_left_alone():
    src = '他说"话没说完'
    out = postprocess_markdown(src)
    assert '"' in out


def test_url_escaped_amp_fixed_inside_link():
    src = r"见[榜单](https://example.com/?query-0-page=3\&cst=x)细节"
    out = postprocess_markdown(src)
    assert "(https://example.com/?query-0-page=3&cst=x)" in out
    assert r"\&" not in out


def test_escape_residue_stripped_in_prose():
    out = postprocess_markdown(r"联系 \@dylan522p 以及 A \& B 团队")
    assert "@dylan522p" in out
    assert "A & B" in out
    assert "\\@" not in out
    assert "\\&" not in out


def test_code_block_punct_untouched():
    src = "说明\n\n```\nprintf(a,b);\nx: int = 1\n```\n\n结束"
    out = postprocess_markdown(src)
    assert "printf(a,b);" in out
    assert "x: int = 1" in out


def test_inline_code_untouched():
    out = postprocess_markdown("设置环境变量`FHC_HIDDEN=4096,DEBUG=1`即可")
    assert "`FHC_HIDDEN=4096,DEBUG=1`" in out


def test_nested_image_in_link_placeholder_restored():
    # 图片先被 stash，外层链接的 stash 值内嵌图片占位符；
    # 单遍还原会把 \x00PROTECTED_n\x00 泄漏进成品（Claude Code 篇 ￰4￰ 同款）。
    src = "[![推文](https://cdn.example.com/a.png)](https://twitter.com/x/status/1) 相关报道"
    out = postprocess_markdown(src)
    assert "[![推文](https://cdn.example.com/a.png)](https://twitter.com/x/status/1)" in out
    assert "\x00" not in out
    assert "PROTECTED_" not in out


def test_normalization_idempotent():
    src = (
        '中文,测试(英伟达)说"好"；估值 2,600 万。。\n\n'
        r"[链](https://a.com/?x=1\&y=2) 与 \@abc"
    )
    once = postprocess_markdown(src)
    twice = postprocess_markdown(once)
    assert once == twice
