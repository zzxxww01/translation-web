# -*- coding: utf-8 -*-
"""公众号只认元素上的内联 style，`<style>` 整个会被剥掉。

由此产生两类必须在**发出去之前**处理掉的东西：

1. CSS 变量。`:root` 跟着 `<style>` 一起没了，`var(--x)` 在公众号里无从查起，
   整条声明作废——字号回退成浏览器默认、颜色回退成继承值。
2. `display: table`。公众号不支持这个显示类型，靠它 + `margin:auto` 收缩成
   居中标签的标题会退回块级，铺满整行变成一条大色块（用户实拍到）。
"""

import re

import pytest

from src.services.wechat_formatter import WechatFormatter
from src.services.wechat_themes import get_theme, resolve_css_variables


# --- CSS 变量解析 ---------------------------------------------------------


def test_var_reference_resolved_to_literal():
    css = ":root { --c: #3b82f6; }\nh2 { color: var(--c); }"
    out = resolve_css_variables(css)
    assert "color: #3b82f6" in out
    assert "var(" not in out


def test_var_fallback_used_when_undefined():
    css = ":root { --a: 1px; }\np { margin: var(--nope, 8px); }"
    out = resolve_css_variables(css)
    assert "margin: 8px" in out


def test_nested_var_resolved():
    css = ":root { --base: #111; --text: var(--base); }\np { color: var(--text); }"
    out = resolve_css_variables(css)
    assert "color: #111" in out


def test_simple_calc_folded():
    css = ":root { --s: 16px; }\nh2 { font-size: calc(var(--s) * 1.3); }"
    out = resolve_css_variables(css)
    assert "font-size: 20.8px" in out
    assert "calc(" not in out


def test_complex_calc_left_alone():
    """只折叠一元乘除，含加减的表达式原样留着，别算错。"""
    css = "p { width: calc(100% - 16px); }"
    assert "calc(100% - 16px)" in resolve_css_variables(css)


def test_shipped_themes_carry_no_variables():
    for theme in ("default", "grace", "simple"):
        css = get_theme(theme)
        assert "var(" not in css, theme
        assert "calc(" not in css, theme


# --- 标题外壳 -------------------------------------------------------------


def test_headings_wrapped_in_label_span():
    html = WechatFormatter().format("# 一级\n\n## 二级\n", theme="default")["html"]
    assert '<h1><span class="wx-heading-label">一级</span></h1>' in html
    assert '<h2><span class="wx-heading-label">二级</span></h2>' in html


def test_h3_not_wrapped():
    """h3 靠左边框强调，本来就不需要收缩，不该多一层。"""
    html = WechatFormatter().format("### 三级\n", theme="default")["html"]
    assert "wx-heading-label" not in html


def test_heading_wrapping_is_idempotent():
    formatter = WechatFormatter()
    once = formatter.format("## 二级\n", theme="default")["html"]
    twice = formatter._apply_wechat_fixes(once)
    assert twice.count("wx-heading-label") == 1


def test_heading_inner_markup_preserved():
    html = WechatFormatter().format("## 带 `代码` 与 **粗体**\n", theme="default")["html"]
    assert "wx-heading-label" in html
    assert "<code" in html
    assert "<strong>" in html


# --- 公众号 CSS 能力边界 -------------------------------------------------
# 每一条都对应一种"预览好看、成品垮掉"的真实故障。主题里出现即视为缺陷：
# 公众号只保留内联 style，且属性走白名单，下面这些要么被剥、要么不受支持。
FORBIDDEN_CSS = [
    (
        r"position:\s*(absolute|fixed|sticky)",
        "绝对定位失效后，装饰会掉进文档流——大引号跑到文章顶部、菱形符号贴到页面左边缘",
    ),
    (r"::(before|after)", "伪元素装饰无一例外依赖绝对定位，且公众号会剥掉"),
    (r"display:\s*(table|flex|grid)", "这些显示类型不受支持，失效后收缩布局会摊成满宽色块"),
    (r"\bvar\(", "`:root` 跟着 <style> 一起被剥掉，var() 无从查起，整条声明作废"),
    (r"\bcalc\(", "同上，且 calc 里通常套着 var"),
    (r"color-mix\(", "2023 年才铺开的语法，公众号不认，含它的整条声明作废"),
    (r"background-clip|text-fill-color", "渐变文字：clip 被剥而 text-fill-color 留下时，文字会全透明"),
    (r"transition:|animation:", "公众号正文没有动效"),
    (r":hover|:focus|:active", "公众号正文没有交互态"),
    (r"transform:", "变换不受支持，靠它做的细线/位移会跳变"),
]


@pytest.mark.parametrize("theme", ["default", "grace", "simple"])
@pytest.mark.parametrize("pattern,reason", FORBIDDEN_CSS)
def test_theme_avoids_unsupported_css(theme: str, pattern: str, reason: str) -> None:
    hits = re.findall(pattern, get_theme(theme))
    assert not hits, f"{theme} 主题用了公众号不支持的写法（{len(hits)} 处）：{reason}"


def test_headings_survive_losing_layout_properties():
    """把公众号会剥的属性全部拿掉后，标题仍然是收缩的，不该摊成满宽。

    这是 display:table 那次故障的本质：它一失效就退回块级。inline-block 退化成
    inline 仍然收缩，所以现在的写法扛得住。
    """
    css = get_theme("default")
    # 标题的视觉样式必须挂在内层 span 上，而不是标题元素本身
    assert ".wx-heading-label" in css
    assert "display: inline-block" in css
