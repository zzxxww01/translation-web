"""
微信公众号主题样式管理
"""

import re
import threading
from pathlib import Path
from typing import Dict, List

THEMES_DIR = Path(__file__).parent.parent / "prompts" / "wechat_themes"

# 主题元数据
THEME_METADATA = {
    "default": {
        "name": "经典",
        "description": "专业稳重，适合技术文章",
    },
    "grace": {
        "name": "优雅",
        "description": "精致美观，适合品牌内容",
    },
    "simple": {
        "name": "简洁",
        "description": "清爽简约，适合快速阅读",
    },
}


_ROOT_BLOCK_RE = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
_VAR_DECL_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
_VAR_USE_RE = re.compile(
    r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)"
)
# 只折叠最简单的一元乘除（calc(16px * 1.3)），复杂表达式原样留着。
_CALC_MUL_RE = re.compile(
    r"calc\(\s*(-?[\d.]+)([a-z%]*)\s*([*/])\s*(-?[\d.]+)\s*\)"
)


def resolve_css_variables(css: str) -> str:
    """把 ``var()`` 与简单 ``calc()`` 解析成字面值。

    公众号只认元素上的内联 style，``<style>`` 连同 ``:root`` 一起会被剥掉——
    ``var(--md-primary-color)`` 到了那边没有任何定义可查，整条声明作废：字号回退
    成浏览器默认、颜色回退成继承值，排版与预览对不上。所以必须在发给前端之前
    就算成字面值，juice 内联后进公众号才有效。

    此前只有前端 hack 式地 replace 了三个变量名，其余（字号、文字色、代码底色等）
    一路失效。
    """
    variables: Dict[str, str] = {}
    for block in _ROOT_BLOCK_RE.findall(css):
        for name, value in _VAR_DECL_RE.findall(block):
            variables[name] = value.strip()

    if not variables:
        return css

    def substitute(text: str) -> str:
        def replace(match: "re.Match[str]") -> str:
            name, fallback = match.group(1), match.group(2)
            if name in variables:
                return variables[name]
            return (fallback or "").strip()

        return _VAR_USE_RE.sub(replace, text)

    # 变量值本身可能引用别的变量，迭代到收敛（次数设上限，防循环引用）
    for _ in range(5):
        resolved = {key: substitute(value) for key, value in variables.items()}
        if resolved == variables:
            break
        variables = resolved

    css = substitute(css)

    def fold_calc(match: "re.Match[str]") -> str:
        left, unit, operator, right = match.groups()
        try:
            value = (
                float(left) * float(right)
                if operator == "*"
                else float(left) / float(right)
            )
        except (ValueError, ZeroDivisionError):
            return match.group(0)
        rendered = f"{value:.4f}".rstrip("0").rstrip(".")
        return f"{rendered}{unit}"

    for _ in range(3):
        folded = _CALC_MUL_RE.sub(fold_calc, css)
        if folded == css:
            break
        css = folded

    return css


class WechatThemeManager:
    """微信主题管理器"""

    def __init__(self):
        self.themes: Dict[str, str] = {}
        self.base_css: str = ""
        self._lock = threading.RLock()  # 添加锁
        self._load_themes()

    def _load_themes(self):
        """加载所有主题 CSS"""
        with self._lock:  # 加锁保护
            # 清空现有主题
            self.themes.clear()
            self.base_css = ""

            if not THEMES_DIR.exists():
                return

            # 加载基础样式
            base_file = THEMES_DIR / "base.css"
            if base_file.exists():
                self.base_css = base_file.read_text(encoding="utf-8")

            # 加载主题样式
            for css_file in THEMES_DIR.glob("*.css"):
                if css_file.stem == "base":
                    continue
                theme_name = css_file.stem
                self.themes[theme_name] = css_file.read_text(encoding="utf-8")

    def reload_themes(self):
        """重新加载主题"""
        self._load_themes()

    def get_theme(self, theme_name: str = "default") -> str:
        """获取主题 CSS（包含基础样式）"""
        with self._lock:  # 加锁保护
            theme_css = self.themes.get(theme_name, self.themes.get("default", ""))
            # 合并基础样式和主题样式；变量在这里就地解析成字面值，理由见
            # resolve_css_variables 的说明。
            return resolve_css_variables(f"{self.base_css}\n\n{theme_css}")

    def list_themes(self) -> List[dict]:
        """列出所有可用主题及其元数据"""
        with self._lock:  # 加锁保护
            themes = []
            for theme_id in self.themes.keys():
                metadata = THEME_METADATA.get(theme_id, {})
                themes.append({
                    "id": theme_id,
                    "name": metadata.get("name", theme_id),
                    "description": metadata.get("description", ""),
                })
            return themes


# 全局单例
_theme_manager = WechatThemeManager()


def get_theme(theme_name: str = "default") -> str:
    """获取主题 CSS"""
    return _theme_manager.get_theme(theme_name)


def list_themes() -> List[dict]:
    """列出所有可用主题"""
    return _theme_manager.list_themes()
