"""Model choices from the installed runtimes; discovery never submits a prompt."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import time
from pathlib import Path
from typing import Any

from .config import Config
from .runtime_paths import claude_cli_path

logger = logging.getLogger(__name__)
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/\[\]-]{0,127}")
DISCOVERY_TIMEOUT_S = 15
MODEL_OUTPUT_LIMIT = 256 * 1024
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


def parse_antigravity_models(output: str) -> list[dict[str, str]]:
    """`agy models` emits model slug and display name, separated by a tab."""
    choices = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2:
            continue
        value, label = (field.strip() for field in fields)
        if value.lower() in {"slug", "id", "model", "model_id"}:
            continue
        if not MODEL_ID.fullmatch(value) or not label or any(ord(char) < 32 for char in label):
            continue
        choices.setdefault(value, {"id": value, "label": label, "description": ""})
    return list(choices.values())


async def _stop_discovery(process: asyncio.subprocess.Process) -> None:
    try:
        if os.name != "nt":
            # Also stop descendants holding stdout open after the CLI itself exits.
            os.killpg(process.pid, signal.SIGKILL)
        elif process.returncode is None:
            process.kill()
    except ProcessLookupError:
        pass
    # A full PIPE can keep asyncio's process.wait() pending even after kill.
    # Drain without retaining bytes so cleanup also remains memory bounded.
    if process.stdout:
        while await process.stdout.read(65536):
            pass
    await process.wait()


def _antigravity_command(config: Config) -> list[str]:
    # This setting is an executable path, never a shell command or arguments.
    return [str(Path(config.antigravity_bin).expanduser())]


async def discover_antigravity_models(config: Config) -> list[dict[str, str]]:
    # This command lists the CLI catalog only: no prompt, inference, or login flow.
    env = dict(os.environ)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        env.pop(key, None)
    startup = asyncio.create_task(asyncio.create_subprocess_exec(
        *_antigravity_command(config), "models", cwd=str(config.home), env=env,
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, start_new_session=os.name != "nt",
    ))
    try:
        process = await asyncio.shield(startup)
    except asyncio.CancelledError:
        process = await startup
        await _stop_discovery(process)
        raise

    async def read_output() -> bytes:
        output = bytearray()
        while chunk := await process.stdout.read(65536):
            output.extend(chunk)
            if len(output) > MODEL_OUTPUT_LIMIT:
                raise ValueError("Antigravity model output exceeds size limit")
        await process.wait()
        return bytes(output)

    try:
        output = await asyncio.wait_for(read_output(), DISCOVERY_TIMEOUT_S)
    except (Exception, asyncio.CancelledError):
        await _stop_discovery(process)
        raise
    if process.returncode:
        raise RuntimeError(f"Antigravity model discovery failed (exit {process.returncode})")
    return parse_antigravity_models(output.decode("utf-8", errors="replace"))


class ModelCatalog:
    def __init__(self, config: Config):
        self.config = config
        self._catalogs: dict[str, dict[str, Any]] = {}
        self._expires: dict[str, float] = {}
        self._locks = {harness: asyncio.Lock() for harness in ("claude", "antigravity")}
        self._cli_identity: dict[str, tuple[str | None, int | None]] = {}

    async def get(self, harness: str, *, refresh: bool = False) -> dict[str, Any]:
        if harness == "codex":
            models = await asyncio.to_thread(codex_models, self.config.codex_home)
            default = self.config.codex_model or (models[0]["id"] if models else None)
            return {"models": models, "default_model": default, "source": "cache",
                    "warning": None if models else "还没有读到 Codex 模型清单；可使用默认模型或填写模型 ID。"}
        if harness not in self._locks:
            raise ValueError("不支持的运行工具")
        async with self._locks[harness]:
            if harness == "claude":
                path = claude_cli_path(self.config)
            else:
                command = _antigravity_command(self.config)
                path = (shutil.which(command[0]) or command[0]) if command else None
            try:
                modified = Path(path).stat().st_mtime_ns if path else None
            except OSError:
                modified = None
            identity = (path, modified)
            if identity != self._cli_identity.get(harness):
                self._expires[harness] = 0.0
                self._cli_identity[harness] = identity
            if not refresh and harness in self._catalogs and time.monotonic() < self._expires[harness]:
                return self._catalogs[harness]
            try:
                discover = discover_claude_models if harness == "claude" else discover_antigravity_models
                models = await asyncio.wait_for(discover(self.config), timeout=DISCOVERY_TIMEOUT_S)
            except Exception as exc:
                # CLI diagnostics may contain credentials or login URLs; never echo them.
                logger.warning("%s model discovery failed (%s)", harness, type(exc).__name__)
                models = []
            if harness == "claude":
                catalog = {
                    "models": models or CLAUDE_ALIASES, "default_model": self.config.model,
                    "source": "runtime" if models else "aliases",
                    "warning": None if models else "暂时读不到 Claude 的模型清单，以下为通用别名；能否使用取决于账号权限。",
                }
            else:
                catalog = {
                    "models": models, "default_model": self.config.antigravity_model,
                    "source": "runtime" if models else "unavailable",
                    "warning": None if models else "暂时读不到 Gemini 模型清单；请检查服务器 agy CLI 的安装和登录状态。仍可使用默认模型或填写模型 ID。",
                }
            self._catalogs[harness] = catalog
            self._expires[harness] = time.monotonic() + (300 if models else 30)
            return catalog
