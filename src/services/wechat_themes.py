"""
微信公众号主题样式管理
"""

from pathlib import Path
from typing import Dict, List
import threading

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
            # 合并基础样式和主题样式
            return f"{self.base_css}\n\n{theme_css}"

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
