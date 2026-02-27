"""
Translation Agent - Prompt Manager

集中管理所有prompt模板，支持动态加载和变量替换。
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class PromptManager:
    """Prompt管理器，负责加载和管理所有prompt模板"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初始化Prompt管理器

        Args:
            prompts_dir: prompts文件夹路径，默认为 src/prompts
        """
        if prompts_dir is None:
            # 默认路径：当前目录（prompts文件夹）
            self.prompts_dir = Path(__file__).parent
        else:
            self.prompts_dir = Path(prompts_dir)
        self._templates: Dict[str, str] = {}

        # 预加载所有模板
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        """加载所有prompt模板"""
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        for prompt_file in self.prompts_dir.glob("*.txt"):
            name = prompt_file.stem
            try:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    self._templates[name] = f.read()
            except Exception as e:
                print(f"Warning: Failed to load prompt template '{name}': {e}")

    def get(self, name: str, **kwargs) -> str:
        """
        获取并格式化prompt模板

        Args:
            name: 模板名称（不含.txt扩展名）
            **kwargs: 模板变量

        Returns:
            str: 格式化后的prompt

        Raises:
            KeyError: 如果模板不存在
        """
        if name not in self._templates:
            available = ", ".join(self._templates.keys())
            raise KeyError(
                f"Prompt template '{name}' not found. "
                f"Available templates: {available}"
            )

        template = self._templates[name]

        # 如果提供了变量，进行格式化
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                missing_var = str(e).strip("'")
                raise ValueError(
                    f"Missing required variable '{missing_var}' for template '{name}'"
                )

        return template

    def reload(self) -> None:
        """重新加载所有模板"""
        self._templates.clear()
        self._load_all_templates()

    def list_templates(self) -> List[str]:
        """列出所有可用的模板名称"""
        return list(self._templates.keys())

    def has_template(self, name: str) -> bool:
        """检查指定的模板是否存在"""
        return name in self._templates


# 全局单例实例
_global_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局Prompt管理器单例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = PromptManager()
    return _global_manager


def get_prompt(name: str, **kwargs) -> str:
    """
    便捷函数：获取并格式化prompt模板

    Args:
        name: 模板名称
        **kwargs: 模板变量

    Returns:
        str: 格式化后的prompt
    """
    return get_prompt_manager().get(name, **kwargs)
