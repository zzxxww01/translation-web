"""Prompt loading for exact template names."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


class PromptManager:
    """Load prompt templates by their exact logical names."""

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(__file__).parent
        self._templates: Dict[str, str] = {}
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        for prompt_file in self.prompts_dir.rglob("*.txt"):
            name = self._normalize_name(
                prompt_file.relative_to(self.prompts_dir).as_posix()
            )
            try:
                with open(prompt_file, "r", encoding="utf-8") as handle:
                    self._templates[name] = handle.read()
            except Exception as exc:
                print(f"Warning: Failed to load prompt template '{name}': {exc}")

    def _normalize_name(self, name: str) -> str:
        normalized = str(name).replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized.endswith(".txt"):
            normalized = normalized[:-4]
        return normalized

    def resolve_name(self, name: str) -> str:
        return self._normalize_name(name)

    def get(self, name: str, **kwargs) -> str:
        resolved = self.resolve_name(name)
        if resolved not in self._templates:
            available = ", ".join(sorted(self.list_templates()))
            raise KeyError(
                f"Prompt template '{name}' not found. Available templates: {available}"
            )

        template = self._templates[resolved]
        if not kwargs:
            return template

        try:
            return template.format(**kwargs)
        except KeyError as exc:
            missing_var = str(exc).strip("'")
            raise ValueError(
                f"Missing required variable '{missing_var}' for template '{name}'"
            ) from exc

    def reload(self) -> None:
        self._templates.clear()
        self._load_all_templates()

    def list_templates(self) -> List[str]:
        return sorted(self._templates.keys())

    def has_template(self, name: str) -> bool:
        return self.resolve_name(name) in self._templates


_global_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Return the shared prompt manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = PromptManager()
    return _global_manager


def get_prompt(name: str, **kwargs) -> str:
    """Convenience wrapper around the global prompt manager."""
    return get_prompt_manager().get(name, **kwargs)
