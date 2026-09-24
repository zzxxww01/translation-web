"""Project-local, content-addressed stage checkpoints (not a global answer cache).

Only callers that have validated a stage result may save it. Input bodies and
credentials are never written into keys or logs. Cache misses are safe; corrupt,
oversized, incompatible and failed results are never silently treated as work.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import portalocker
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any, Callable, TypeVar

from src.core.file_utils import write_json_atomic

logger = logging.getLogger(__name__)
T = TypeVar("T")
_active: ContextVar["CheckpointSession | None"] = ContextVar("stage_checkpoints", default=None)
_SCHEMA = 1


def normalized(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("Checkpoint object keys must be strings")
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError(f"Unsupported checkpoint value: {type(value).__name__}")


def fingerprint(value: Any) -> str:
    encoded = json.dumps(normalized(value), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def provider_fingerprint(provider: Any) -> str:
    # Include the configured route and generation defaults, not object identity.
    # as_llm_provider attaches the adapter's already-hashed plan fingerprint.
    identity = {"class": type(provider).__module__ + "." + type(provider).__qualname__}
    for name in ("model_alias", "model_name", "default_model", "temperature", "max_tokens",
                 "request_timeout", "timeout", "_route_fingerprint", "_phase_config"):
        value = getattr(provider, name, None)
        if value is not None and isinstance(value, (str, int, float, bool, dict)):
            identity[name] = value
    return fingerprint(identity)


def prompt_fingerprint(names: tuple[str, ...] = ()) -> str:
    from src.prompts import get_prompt_manager, active_rule_snapshot
    manager = get_prompt_manager()
    # Include composition/contract version even when selecting task-specific texts.
    snapshot = manager.snapshot()
    if names:
        payload = {name: manager.get(name) for name in names}
    else:
        payload = snapshot.get("digest", snapshot)
    return fingerprint({"prompt": payload, "rules": active_rule_snapshot(),
                        "composer": snapshot.get("composer_hash"),
                        "checkpoint_contract": "efficiency-stages-v1"})


class WorkCheckpointStore:
    """A bounded store under one validated project's artifact directory."""
    MAX_BYTES = 8 * 1024 * 1024
    MAX_ENTRIES = 1024

    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        self._guard = Lock()
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self._safe_root()

    def _safe_root(self):
        if any(p.is_symlink() for p in (self.root, *self.root.parents)):
            raise ValueError("Checkpoint path must not contain symlinks")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, task: str, key: str) -> Path:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,60}", task) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("Invalid checkpoint identity")
        self._safe_root()
        path = self.root / f"{task}-{key}.json"
        if path.is_symlink():
            raise ValueError("Checkpoint file must not be a symlink")
        return path

    def load(self, task: str, key: str, validator: Callable[[Any], T]) -> T | None:
        try:
            path = self._path(task, key)
            if path.stat().st_size > self.MAX_BYTES:
                raise ValueError("Checkpoint exceeds size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") != _SCHEMA or payload.get("key") != key or payload.get("task") != task:
                raise ValueError("Checkpoint version or identity mismatch")
            result = payload["result"]
            if fingerprint(result) != payload.get("result_digest"):
                raise ValueError("Checkpoint result digest mismatch")
            value = validator(deepcopy(result))
        except (OSError, ValueError, KeyError, TypeError):
            with self._guard:
                self.misses += 1
            return None
        with self._guard:
            self.hits += 1
        return value

    def save(self, task: str, key: str, result: Any) -> None:
        data = normalized(result)
        payload = {"schema": _SCHEMA, "task": task, "key": key,
                   "result_digest": fingerprint(data), "result": data}
        if len(json.dumps(payload, ensure_ascii=False).encode()) > self.MAX_BYTES:
            logger.warning("Checkpoint too large; leaving stage uncached: %s", task)
            return
        # Cache loss must not lose canonical translations. Atomic replace and a
        # bounded per-project lock protect concurrent writers/pruning.
        import portalocker
        with self._guard:
            path = self._path(task, key)
            lock_path = self.root / ".write.lock"
            if lock_path.is_symlink():
                raise ValueError("Checkpoint lock must not be a symlink")
            with portalocker.Lock(str(lock_path), timeout=10):
                write_json_atomic(path, payload)
                path.chmod(0o600)
                self.writes += 1
                files = sorted((p for p in self.root.glob("*.json") if not p.is_symlink()),
                               key=lambda p: p.stat().st_mtime_ns)
                for stale in files[:-self.MAX_ENTRIES]:
                    stale.unlink(missing_ok=True)

    def summary(self) -> dict:
        with self._guard:
            return {"hits": self.hits, "misses": self.misses, "writes": self.writes,
                    "scope": "project", "counts_as_model_calls": False}


class CheckpointSession:
    def __init__(self, store: WorkCheckpointStore, *, read_enabled: bool = True):
        self.store = store
        self.read_enabled = read_enabled


@contextmanager
def checkpoint_scope(store: WorkCheckpointStore, *, read_enabled: bool = True):
    token = _active.set(CheckpointSession(store, read_enabled=read_enabled))
    try:
        yield
    finally:
        _active.reset(token)


@contextmanager
def fresh_stage_scope(fresh: bool):
    session = _active.get()
    if not fresh or session is None:
        yield
        return
    with checkpoint_scope(session.store, read_enabled=False):
        yield


def checkpoint_call(task: str, provider: Any, inputs: Any, call: Callable[[], T],
                    validator: Callable[[Any], T], *, prompts: tuple[str, ...] = (),
                    cacheable: Callable[[T], bool] = lambda value: True) -> T:
    """Validate on both read and write. A failed call cannot poison a checkpoint."""
    session = _active.get()
    if session is None:
        return validator(call())
    from src.llm.execution_context import check_active
    check_active()
    key = fingerprint({"inputs": inputs, "provider": provider_fingerprint(provider),
                       "policy": prompt_fingerprint(prompts)})
    if session.read_enabled:
        cached = session.store.load(task, key, validator)
        if cached is not None and cacheable(cached):
            return cached
    result = validator(call())
    check_active()  # abandoned workers do not commit late results
    try:
        if cacheable(result):
            session.store.save(task, key, result)
    except (OSError, ValueError, TypeError, portalocker.exceptions.LockException) as exc:
        logger.warning("Stage completed without a checkpoint (%s): %s", task, type(exc).__name__)
    return result
