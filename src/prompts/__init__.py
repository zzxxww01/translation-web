"""Named prompt templates, explicit includes, strict rendering and run snapshots."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import logging
from pathlib import Path
import re
from string import Formatter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
BUNDLE_VERSION = "chinese-quality-v2"
_INCLUDE = re.compile(r"\[\[include:([A-Za-z0-9_/-]+)\]\]")
_active_manager = ContextVar("translation_prompt_manager", default=None)


class PromptManager:
    """Load exact template names. Source data is formatted only once."""
    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(__file__).parent
        self._templates: Dict[str, str] = {}
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        templates = {}
        for path in self.prompts_dir.rglob("*.txt"):
            name = self._normalize_name(path.relative_to(self.prompts_dir).as_posix())
            templates[name] = path.read_text(encoding="utf-8-sig")
        # Atomic replacement; no window with an empty template registry.
        self._templates = templates
        for name in templates:
            self._expanded(name)

    def _normalize_name(self, name: str) -> str:
        normalized = str(name).replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized[:-4] if normalized.endswith(".txt") else normalized

    def resolve_name(self, name: str) -> str:
        return self._normalize_name(name)

    def _expanded(self, name: str, stack: tuple = ()) -> str:
        name = self.resolve_name(name)
        if name in stack:
            raise ValueError("Prompt include cycle: " + " -> ".join((*stack, name)))
        if name not in self._templates:
            raise KeyError(f"Prompt template '{name}' not found")
        return _INCLUDE.sub(lambda m: self._expanded(m[1], (*stack, name)), self._templates[name])

    def variables(self, name: str) -> set[str]:
        return {key for _, key, _, _ in Formatter().parse(self._expanded(name)) if key is not None}

    def get(self, name: str, **kwargs) -> str:
        active = _active_manager.get()
        if active is not None and active is not self:
            return active.get(name, **kwargs)
        template = self._expanded(name)
        if not kwargs:
            return template  # compatibility: callers may inspect unrendered templates
        try:
            rendered = template.format(**kwargs)
        except KeyError as exc:
            raise ValueError(f"Missing required variable {exc} for template '{name}'") from exc
        logger.debug("prompt task=%s bundle=%s rendered_sha256=%s chars=%d",
                     name, BUNDLE_VERSION, hashlib.sha256(rendered.encode()).hexdigest(), len(rendered))
        return rendered

    def render(self, name: str, **kwargs) -> str:
        active = _active_manager.get()
        if active is not None and active is not self:
            return active.render(name, **kwargs)
        fields = self.variables(name)
        missing, unused = fields - kwargs.keys(), kwargs.keys() - fields
        if missing or unused:
            raise ValueError(f"Prompt '{name}': missing={sorted(missing)}, unused={sorted(unused)}")
        return self.get(name, **kwargs)

    def reload(self) -> None:
        self._load_all_templates()

    def list_templates(self) -> List[str]:
        return sorted(self._templates)

    def has_template(self, name: str) -> bool:
        return self.resolve_name(name) in self._templates

    def snapshot(self) -> dict:
        templates = dict(self._templates)
        raw = json.dumps(templates, sort_keys=True, ensure_ascii=False).encode()
        # Changes in composition code are significant, not just text changes.
        code_hash = hashlib.sha256()
        for relative in ("__init__.py", "prompt_builder.py", "task_builders.py", "contracts.py", "editing_options.py"):
            path = Path(__file__).parent / relative
            if path.exists():
                code_hash.update(relative.encode() + b"\0" + path.read_bytes())
        option_path = Path(__file__).resolve().parents[2] / "config" / "editing_options.json"
        if option_path.exists():
            code_hash.update(option_path.read_bytes())
        digest = hashlib.sha256(raw + code_hash.digest()).hexdigest()
        return {"schema_version": 1, "bundle_version": BUNDLE_VERSION,
                "digest": digest, "composer_hash": code_hash.hexdigest(), "templates": templates}

    def frozen_copy(self):
        clone = object.__new__(PromptManager)
        clone.prompts_dir = self.prompts_dir
        clone._templates = dict(self._templates)
        return clone


_global_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    active = _active_manager.get()
    if active is not None:
        return active
    global _global_manager
    if _global_manager is None:
        _global_manager = PromptManager()
    return _global_manager

def get_prompt(name: str, **kwargs) -> str:
    return get_prompt_manager().get(name, **kwargs)

@contextmanager
def prompt_bundle_scope(snapshot: Optional[dict] = None):
    """Freeze a bundle for a run. Incompatible old runs require explicit retranslation."""
    manager = get_prompt_manager().frozen_copy()
    current = manager.snapshot()
    if snapshot is not None and snapshot.get("digest") != current["digest"]:
        raise ValueError("Prompt bundle changed or is unversioned; start an explicit new retranslation instead of mixing versions.")
    token = _active_manager.set(manager)
    try:
        yield manager
    finally:
        _active_manager.reset(token)
