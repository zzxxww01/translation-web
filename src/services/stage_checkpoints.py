"""Legacy checkpoint API delegating to the bounded canonical store.

Both PRs now share validation, lock coalescing, cancellation and persistence.
"""
from pathlib import Path
from typing import Any, Callable, TypeVar
from contextlib import contextmanager
from contextvars import ContextVar
from .work_checkpoints import (
    WorkCheckpointStore, normalized, fingerprint, checkpoint_scope as work_checkpoint_scope,
)
T = TypeVar("T")
_active: ContextVar["StageCheckpoints | None"] = ContextVar("legacy_stage_checkpoints", default=None)

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
    MAX_BYTES = WorkCheckpointStore.MAX_BYTES

    def __init__(self, project_dir: Path, namespace: Any, *, enabled: bool = True, reuse_enabled: bool = True):
        self.project_dir = Path(project_dir)
        self.root = self.project_dir / "artifacts" / "work-checkpoints-v1"
        self.namespace = fingerprint(namespace)
        self.enabled = enabled
        self.reuse_enabled = reuse_enabled
        self.store = WorkCheckpointStore(self.root)

    @property
    def hits(self):
        return self.store.hits

    @property
    def misses(self):
        return self.store.misses

    def compute(self, stage: str, inputs: Any, fn: Callable[[], T], *,
                encode: Callable[[T], Any] = normalized,
                decode: Callable[[Any], T] = lambda value: value,
                reuse: bool = True, cache_if: Callable[[T], bool] = lambda value: True) -> T:
        if not self.enabled:
            return decode(encode(fn()))
        key = fingerprint([self.SCHEMA, self.namespace, stage, inputs])
        # Canonical storage normalizes validated models on write. A legacy
        # custom encoder must be applied before validation, not twice on hits.
        return self.store.compute(stage, key, lambda: encode(fn()), decode,
                                  reuse=reuse and self.reuse_enabled, cacheable=cache_if, encode=encode)


@contextmanager
def checkpoint_scope(store: StageCheckpoints):
    token = _active.set(store)
    try:
        if store.enabled:
            with work_checkpoint_scope(store.store, read_enabled=store.reuse_enabled, namespace=store.namespace):
                yield store
        else:
            yield store
    finally:
        _active.reset(token)


def cached_stage(stage: str, inputs: Any, fn: Callable[[], T], **kwargs) -> T:
    store = _active.get()
    return store.compute(stage, inputs, fn, **kwargs) if store is not None else fn()
