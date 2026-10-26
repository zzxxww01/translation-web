"""Model choices from the installed runtimes; discovery never submits a prompt."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from .config import Config
from .runtime_paths import claude_cli_path

logger = logging.getLogger(__name__)
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/\[\]-]{0,127}")
CLAUDE_ALIASES = [
    {"id": "opus", "label": "Claude Opus", "description": "Claude Code 的 Opus 别名"},
    {"id": "sonnet", "label": "Claude Sonnet", "description": "Claude Code 的 Sonnet 别名"},
    {"id": "haiku", "label": "Claude Haiku", "description": "Claude Code 的 Haiku 别名"},
]


def validate_model(model: str | None) -> str | None:
    if model is None or not model.strip():
        return None
    model = model.strip()
    if not MODEL_ID.fullmatch(model):
        raise ValueError("模型 ID 格式不正确，请填写模型名称，不要填写命令或空格")
    return model


def codex_models(codex_home: Path) -> list[dict[str, str]]:
    try:
        data = json.loads((codex_home / "models_cache.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    raw = data.get("models") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    listed = [m for m in raw if isinstance(m, dict) and m.get("visibility") == "list"
              and isinstance(m.get("slug"), str) and MODEL_ID.fullmatch(m["slug"])]
    listed.sort(key=lambda m: m["priority"] if isinstance(m.get("priority"), (int, float)) else 1_000_000)
    choices = {}
    for model in listed:
        choices.setdefault(model["slug"], {
            "id": model["slug"], "label": str(model.get("display_name") or model["slug"]),
            "description": str(model.get("description") or ""),
        })
    return list(choices.values())


async def discover_claude_models(config: Config) -> list[dict[str, str]]:
    # Lazy import: Codex-only discovery and unit tests do not need the SDK.
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    options = ClaudeAgentOptions(cwd=str(config.home), setting_sources=["user"], cli_path=claude_cli_path(config))
    # connect/get_server_info only initialize the CLI; no query/inference is sent.
    async with ClaudeSDKClient(options=options) as client:
        info = await client.get_server_info() or {}
        raw = info.get("models") or []
        choices = []
        for model in raw:
            if not isinstance(model, dict):
                continue
            value = model.get("value")
            if isinstance(value, str) and MODEL_ID.fullmatch(value):
                choices.append({"id": value, "label": str(model.get("displayName") or value),
                                "description": str(model.get("description") or "")})
        return choices


class ModelCatalog:
    def __init__(self, config: Config):
        self.config = config
        self._claude: dict[str, Any] | None = None
        self._expires = 0.0
        self._lock = asyncio.Lock()
        self._cli_identity: tuple[str | None, int | None] | None = None

    async def get(self, harness: str) -> dict[str, Any]:
        if harness == "codex":
            models = await asyncio.to_thread(codex_models, self.config.codex_home)
            default = self.config.codex_model or (models[0]["id"] if models else None)
            return {"models": models, "default_model": default, "source": "cache",
                    "warning": None if models else "还没有读到 Codex 模型清单；可使用默认模型或填写模型 ID。"}
        if harness != "claude":
            raise ValueError("不支持的运行工具")
        async with self._lock:
            path = claude_cli_path(self.config)
            try:
                modified = Path(path).stat().st_mtime_ns if path else None
            except OSError:
                modified = None
            identity = (path, modified)
            if identity != self._cli_identity:
                self._expires = 0.0
                self._cli_identity = identity
            if self._claude is not None and time.monotonic() < self._expires:
                return self._claude
            try:
                models = await asyncio.wait_for(discover_claude_models(self.config), timeout=15)
            except Exception:
                logger.warning("Claude model discovery failed", exc_info=True)
                models = []
            self._claude = {
                "models": models or CLAUDE_ALIASES, "default_model": self.config.model,
                "source": "runtime" if models else "aliases",
                "warning": None if models else "暂时读不到 Claude 的模型清单，以下为通用别名；能否使用取决于账号权限。",
            }
            self._expires = time.monotonic() + (300 if models else 30)
            return self._claude
