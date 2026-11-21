"""
翻译稿：帖子翻译页（手动粘贴）和 Slack 翻译模式共用的存档，也是「翻译记录」的数据来源。

每篇一个 JSON 文件（data/post_drafts/<id>.json）：
- state：和帖子翻译页前端 store 同构的快照（原文、各版译文、版本信息、标题），前端整份读写；
- Slack 来的稿子另有 slack（来源 thread）、extraction（选材说明）、images（配图）；
- rev 每存一次 +1，前端带着自己读到的 rev 来存，对不上（别处改过）就拒绝，避免互相覆盖。
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DRAFT_ID_RE = re.compile(r"^(m_[0-9a-f]{12}|s_[A-Z0-9]{8,12}_[0-9]{9,11}_[0-9]{1,6})$")
FILE_ID_RE = re.compile(r"^F[A-Z0-9]{6,20}$")
MAX_STATE_BYTES = 2_000_000
MAX_IMAGES = 30
STATUSES = ("draft", "done")


class DraftError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def slack_draft_id(channel_id: str, thread_ts: str) -> str:
    return f"s_{channel_id}_{thread_ts.replace('.', '_')}"


def new_manual_id() -> str:
    return f"m_{uuid.uuid4().hex[:12]}"


def _now() -> float:
    return time.time()


def _str(value: Any, limit: int) -> str:
    return str(value or "")[:limit]


def _first_line(text: str, limit: int = 80) -> str:
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    return line[:limit]


def current_translation(state: Dict[str, Any]) -> str:
    versions = state.get("versions") or []
    current = state.get("currentVersionId")
    for v in versions:
        if isinstance(v, dict) and v.get("id") == current:
            return str(v.get("content") or "")
    return str(versions[-1].get("content") or "") if versions and isinstance(versions[-1], dict) else ""


def summarize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """翻译记录列表里的一行。"""
    state = doc.get("state") or {}
    titles = [t for t in state.get("generatedTitles") or [] if isinstance(t, str)]
    translation = current_translation(state)
    slack = doc.get("slack")
    return {
        "id": doc["id"],
        "source": doc["source"],
        "status": doc.get("status", "draft"),
        "auto": bool(doc.get("auto")),
        "seen": bool(doc.get("seen", True)),
        "title": state.get("selectedTitle") or (titles[0] if titles else "")
        or (slack or {}).get("title") or _first_line(state.get("originalText") or ""),
        "preview": translation[:160],
        "source_preview": _first_line(state.get("originalText") or "", 160),
        "versions": len(state.get("versions") or []),
        "images": [i["id"] for i in doc.get("images") or []][:1],
        "image_count": len(doc.get("images") or []),
        "slack": {k: slack.get(k) for k in ("channel_id", "thread_ts", "channel_name", "title")} if slack else None,
        "no_post": bool((doc.get("extraction") or {}).get("has_post") is False),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def clean_doc(doc: Dict[str, Any], existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """只收认识的字段，限长；id / source / slack / created_at 以已有的为准，前端改不了。"""
    if not isinstance(doc, dict):
        raise DraftError("BAD_DRAFT", "翻译稿格式不对")
    state = doc.get("state")
    if not isinstance(state, dict):
        raise DraftError("BAD_DRAFT", "翻译稿缺少内容")
    if len(json.dumps(state, ensure_ascii=False)) > MAX_STATE_BYTES:
        raise DraftError("DRAFT_TOO_LARGE", "翻译稿太大了（版本太多），删掉一些旧版本再存")
    images = []
    for img in doc.get("images") or []:
        if isinstance(img, dict) and FILE_ID_RE.match(str(img.get("id") or "")):
            images.append({"id": img["id"], "name": _str(img.get("name"), 200)})
    status = doc.get("status") if doc.get("status") in STATUSES else "draft"
    out = {
        "state": state,
        "images": images[:MAX_IMAGES],
        "status": status,
        "auto": bool(doc.get("auto", (existing or {}).get("auto", False))),
        "seen": bool(doc.get("seen", True)),
    }
    extraction = doc.get("extraction", (existing or {}).get("extraction"))
    if isinstance(extraction, dict):
        out["extraction"] = extraction
    return out


class PostDraftStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._lock = threading.Lock()

    def _path(self, draft_id: str) -> Path:
        if not DRAFT_ID_RE.match(draft_id or ""):
            raise DraftError("BAD_DRAFT_ID", "翻译稿 ID 不对")
        return self.root / f"{draft_id}.json"

    def get(self, draft_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(draft_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            raise DraftError("DRAFT_UNREADABLE", f"翻译稿读不出来：{exc.__class__.__name__}", 500) from exc

    def _write(self, doc: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(doc["id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def save(self, draft_id: str, doc: Dict[str, Any], *, rev: Optional[int], source: str = "manual",
             slack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """前端存稿。rev 是前端读到的版本号；新建时为 None。"""
        with self._lock:
            existing = self.get(draft_id)
            if existing and rev != existing.get("rev"):
                raise DraftError("DRAFT_CONFLICT", "这份翻译稿在别处改过了，已重新载入最新内容", 409)
            if not existing and rev not in (None, 0):
                raise DraftError("DRAFT_GONE", "这份翻译稿已经被删除了", 404)
            cleaned = clean_doc(doc, existing)
            now = _now()
            merged = {
                "id": draft_id,
                "source": existing["source"] if existing else source,
                "slack": existing.get("slack") if existing else slack,
                "created_at": existing["created_at"] if existing else now,
                **cleaned,
                "updated_at": now,
                "rev": (existing or {}).get("rev", 0) + 1,
            }
            self._write(merged)
            return merged

    def put_system(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """后端流程（提取 / 自动翻译）整份写入；rev +1。"""
        with self._lock:
            existing = self.get(doc["id"])
            doc = {**doc, "rev": (existing or {}).get("rev", 0) + 1, "updated_at": _now()}
            doc.setdefault("created_at", (existing or {}).get("created_at", _now()))
            self._write(doc)
            return doc

    def delete(self, draft_id: str) -> bool:
        with self._lock:
            path = self._path(draft_id)
            try:
                path.unlink()
                return True
            except FileNotFoundError:
                return False

    def _all(self) -> List[Dict[str, Any]]:
        docs = []
        if not self.root.is_dir():
            return docs
        for path in self.root.glob("*.json"):
            try:
                docs.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return docs

    def list(self, query: str = "", source: str = "", limit: int = 300) -> List[Dict[str, Any]]:
        """翻译记录：按最近修改从新到旧；query 在标题、原文、译文里找（每个词都要出现）。"""
        words = [w.lower() for w in (query or "").split() if w]
        out = []
        for doc in self._all():
            if source and doc.get("source") != source:
                continue
            if (doc.get("extraction") or {}).get("has_post") is False:
                continue  # 提取后发现没有要发的帖子（纯讨论）：不进翻译记录
            if words:
                state = doc.get("state") or {}
                hay = " ".join([
                    json.dumps(state.get("generatedTitles") or [], ensure_ascii=False),
                    state.get("originalText") or "",
                    current_translation(state),
                    ((doc.get("slack") or {}).get("title") or ""),
                ]).lower()
                if not all(w in hay for w in words):
                    continue
            out.append(summarize(doc))
        out.sort(key=lambda d: -(d.get("updated_at") or 0))
        return out[:limit]

    def slack_index(self) -> Dict[str, Dict[str, Any]]:
        """「频道:thread_ts」-> 状态，给 Slack 列表行和 thread 顶部显示「草稿 / 已完成」。"""
        out = {}
        for doc in self._all():
            slack = doc.get("slack")
            if doc.get("source") == "slack" and slack:
                state = doc.get("state") or {}
                out[f"{slack['channel_id']}:{slack['thread_ts']}"] = {
                    "id": doc["id"],
                    "status": doc.get("status", "draft"),
                    "auto": bool(doc.get("auto")),
                    "seen": bool(doc.get("seen", True)),
                    "versions": len(state.get("versions") or []),
                    "no_post": bool((doc.get("extraction") or {}).get("has_post") is False),
                }
        return out
