"""Resolve the Claude executable consistently for sessions, models, and updates."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil


def native_claude_path() -> Path:
    return Path.home() / ".local" / "bin" / ("claude.exe" if os.name == "nt" else "claude")


def claude_cli_path(config) -> str | None:
    explicit = getattr(config, "claude_bin", None)
    if explicit:
        return str(Path(explicit).expanduser())
    native = native_claude_path()
    if native.is_file() and os.access(native, os.X_OK):
        return str(native)
    command = shutil.which("claude")
    if command:
        return command
    try:
        spec = importlib.util.find_spec("claude_agent_sdk")
        if spec and spec.origin:
            bundled = Path(spec.origin).parent / "_bundled" / native.name
            if bundled.is_file():
                return str(bundled)
    except (ImportError, ValueError):
        pass
    return None
