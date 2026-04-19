"""
微信公众号主题样式管理
"""

from pathlib import Path
from typing import Dict

THEMES_DIR = Path(__file__).parent.parent / "prompts" / "wechat_themes"


class WechatThemeManager:
    """微信主题管理器"""

    def __init__(self):
        self.themes: Dict[str, str] = {}
        self._load_themes()

    def _load_themes(self):
        """加载所有主题 CSS"""
        if not THEMES_DIR.exists():
            return

        for css_file in THEMES_DIR.glob("*.css"):
            theme_name = css_file.stem
            self.themes[theme_name] = css_file.read_text(encoding="utf-8")

    def get_theme(self, theme_name: str = "default") -> str:
        """获取主题 CSS"""
        return self.themes.get(theme_name, self.themes.get("default", ""))

    def list_themes(self) -> list[str]:
        """列出所有可用主题"""
        return list(self.themes.keys())


# 全局单例
_theme_manager = WechatThemeManager()


def get_theme(theme_name: str = "default") -> str:
    """获取主题 CSS"""
    return _theme_manager.get_theme(theme_name)


def list_themes() -> list[str]:
    """列出所有可用主题"""
    return _theme_manager.list_themes()
