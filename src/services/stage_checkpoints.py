"""Project-scoped, input-addressed checkpoints for completed, validated work.

Candidates never imply approval. No response is cached until its parser and
validator succeed. Explicit retranslation bypasses reads, not safety checks.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from threading import Lock
from pathlib import Path
from typing import Any, Callable, TypeVar
from contextlib import contextmanager
from contextvars import ContextVar

import portalocker
from src.core.file_utils import write_json_atomic

T = TypeVar("T")
logger = logging.getLogger(__name__)
_active: ContextVar["StageCheckpoints | None"] = ContextVar("stage_checkpoints", default=None)


def normalized(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"Unsupported checkpoint input: {type(value).__name__}")


def fingerprint(value: Any) -> str:
    raw = json.dumps(normalized(value), ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def provider_identity(provider: Any) -> dict:
    """Route/config identity without persisting credentials or their hashes."""
    result = {"type": f"{type(provider).__module__}.{type(provider).__qualname__}"}
    for key in ("model_alias", "model_name", "default_model", "base_url", "_phase_config"):
        value = getattr(provider, key, None)
        if isinstance(value, (str, int, float, dict)):
            result[key] = value
    # Adapter facades carry an immutable, credential-free route description.
    route = getattr(provider, "_checkpoint_route", None)
    if isinstance(route, (list, dict)):
        result["route"] = route
    return result


def source_identity(sections: list) -> list:
    """Include formatting/structure, but exclude drafts and mutable timestamps."""
    return [dict(section_id=s.section_id, title=s.title,
                 synthetic=getattr(s, "synthetic", False),
                 paragraphs=[p.model_dump(mode="json", exclude={
                     "translations", "confirmed", "confirmed_tokenized", "confirmed_format_issues",
                     "history", "status", "ai_insight", "format_recovery_status", "format_errors"
                 }) for p in s.paragraphs]) for s in sections]


class StageCheckpoints:
    SCHEMA = 1
    MAX_BYTES = 32 * 1024 * 1024

    def __init__(self, project_dir: Path, namespace: Any, *, enabled: bool = True, reuse_enabled: bool = True):
        self.project_dir = Path(project_dir)
        self.root = self.project_dir / "artifacts" / "stage-cache-v1"
        self.namespace = fingerprint(namespace)
        self.enabled = enabled
        self.reuse_enabled = reuse_enabled
        self._stats_lock = Lock()
        self.hits = 0
        self.misses = 0

    def _path(self, stage: str, inputs: Any) -> tuple[Path, str]:
        key = fingerprint([self.SCHEMA, self.namespace, stage, inputs])
        # Reject even in-tree symlinks; do not turn a cache hit into file access.
        for part in (self.project_dir, self.project_dir / "artifacts", self.root):
            if part.is_symlink():
                raise ValueError("Checkpoint directory must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / (key + ".json")
        if path.is_symlink() or path.with_suffix(".lock").is_symlink():
            raise ValueError("Checkpoint entry must not be a symlink")
        return path, key

    @contextmanager
    def _entry_lock(self, path: Path):
        from src.llm.execution_context import check_active, bounded_sleep, remaining_timeout
        lock = portalocker.Lock(str(path.with_suffix(".lock")), timeout=0, mode="a")
        started = time.monotonic()
        acquired = False
        try:
            while not acquired:
                check_active()
                try:
                    lock.acquire()
                    acquired = True
                except portalocker.exceptions.LockException:
                    # Poll cooperatively; do not duplicate paid work on contention.
                    # Without a caller deadline, standalone cache waits remain bounded.
                    if remaining_timeout() is None and time.monotonic() - started >= 600:
                        raise TimeoutError("Checkpoint is busy; retry after its owner finishes")
                    bounded_sleep(0.05)
            yield
        finally:
            if acquired:
                lock.release()

    def compute(self, stage: str, inputs: Any, fn: Callable[[], T], *,
                encode: Callable[[T], Any] = normalized,
                decode: Callable[[Any], T] = lambda value: value,
                reuse: bool = True, cache_if: Callable[[T], bool] = lambda value: True) -> T:
        if not self.enabled:
            return fn()
        from src.llm.execution_context import check_active
        check_active()
        path, key = self._path(stage, inputs)
        # Coalesce equal concurrent work across threads/processes in one project.
        # A finite lock wait cannot outlive the caller's deadline unnoticed.
        with self._entry_lock(path):
            check_active()
            if reuse and self.reuse_enabled and path.exists():
                try:
                    if path.stat().st_size > self.MAX_BYTES:
                        raise ValueError("Oversize checkpoint")
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if (payload.get("schema") != self.SCHEMA or payload.get("key") != key
                            or fingerprint(payload["value"]) != payload.get("value_hash")):
                        raise ValueError("Checkpoint hash mismatch")
                    result = decode(payload["value"])
                    with self._stats_lock:
                        self.hits += 1
                    return result
                except (ValueError, KeyError, TypeError, OSError):
                    logger.warning("Ignoring invalid %s checkpoint %s", stage, key)
            with self._stats_lock:
                self.misses += 1
            result = fn()
            if not cache_if(result):
                return result
            value = encode(result)
            # Decode also validates freshly created values before writing.
            decode(value)
            payload = dict(schema=self.SCHEMA, key=key, stage=stage,
                           value=value, value_hash=fingerprint(value))
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            if len(encoded.encode("utf-8")) <= self.MAX_BYTES:
                # A cancelled late worker must not save a candidate as completed.
                check_active()
                write_json_atomic(path, payload)
            return result


@contextmanager
def checkpoint_scope(store: StageCheckpoints):
    token = _active.set(store)
    try:
        yield store
    finally:
        _active.reset(token)


def cached_stage(stage: str, inputs: Any, fn: Callable[[], T], **kwargs) -> T:
    store = _active.get()
    return store.compute(stage, inputs, fn, **kwargs) if store is not None else fn()
