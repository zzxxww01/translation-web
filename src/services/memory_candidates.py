"""Explicitly reviewed rule candidates. Model output never activates a global rule."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import portalocker
from src.core.file_utils import write_json_atomic

class RuleCandidates:
    def __init__(self, active_path: Path):
        self.path = Path(active_path).with_name("memory_candidates.json")

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(str(self.path) + ".lock", timeout=10):
            yield

    def _load(self):
        if not self.path.exists():
            return []
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError("Invalid candidate store")
        return value

    def list(self):
        with self.locked():
            return self._load()

    def add(self, rules, source_kind: str, evidence: dict):
        evidence = {key: str(value)[:4000] for key, value in evidence.items()}
        evidence_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        added = []
        with self.locked():
            rows = self._load()
            known = {row["id"] for row in rows}
            for rule in rules:
                identity = hashlib.sha256((source_kind + "\0" + rule + "\0" + evidence_hash).encode()).hexdigest()[:24]
                if identity in known:
                    continue
                if len(rows) >= 1000:
                    raise ValueError("Candidate store full; review/archive candidates before adding more")
                row = {"id":identity,"rule":rule,"status":"pending","source_kind":source_kind,
                       "scope":"current_context","evidence":evidence,"evidence_hash":evidence_hash,
                       "created_at":datetime.now(timezone.utc).isoformat()}
                rows.append(row);known.add(identity);added.append(row)
            write_json_atomic(self.path, rows)
        return added

    def decide(self, candidate_id: str, action: str, activate):
        if action not in {"approve", "reject"}:
            raise ValueError("Unsupported rule decision")
        with self.locked():
            rows = self._load()
            row = next((r for r in rows if r["id"] == candidate_id), None)
            if row is None:
                raise KeyError(candidate_id)
            target = "approved" if action == "approve" else "rejected"
            if row["status"] == target:
                return row
            if row["status"] != "pending":
                raise ValueError("Candidate already reviewed; create a new explicit manual rule instead")
            if action == "approve":
                activate([row["rule"]])  # explicit user action, idempotent active-store append
                row["scope"] = "global"
            row["status"] = target
            row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(self.path, rows)
            return row
