"""
翻译稿：帖子翻译页（手动粘贴）和 Slack 翻译模式共用的存档，也是「翻译记录」的数据来源。

每篇一个 JSON 文件（data/post_drafts/<id>.json）：
- state：和帖子翻译页前端 store 同构的快照（原文、各版译文、版本信息、标题），前端整份读写；
- Slack 来的稿子另有 slack（来源 thread）、extraction（选材说明）、images（配图）；
- rev 每存一次 +1，前端带着自己读到的 rev 来存，对不上（别处改过）就拒绝，避免互相覆盖。
- sent_at / sent_digest：「已发送」（在 Slack 等系统外发出去后手动标的），和 status（草稿 / 已完成）分开；
  只有 set_sent 能改，前端存稿、后台重翻都原样保留，也不动 rev（不算内容改动，不让正在编辑的页面冲突）。
  没标过的稿子建了超过两周（SENT_AUTO_AFTER）就当已发送（2026-11-23 用户要求，「未发送」只看两周内的）；
  对这种稿子手动「撤销已发送」会记 sent_cleared，之后按未发送算。
"""

from __future__ import annotations

import hashlib
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
SENT_AUTO_AFTER = 14 * 86400


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


def _digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def sent_view(doc: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
    """sent：算不算已发送；sent_at：手动标的时间（没标过 None）；sent_auto：没标过、超过两周默认已发送；
    sent_changed：标了之后当前译文又变了。"""
    sent_at = doc.get("sent_at")
    if not isinstance(sent_at, (int, float)):
        created = doc.get("created_at")
        auto = (not doc.get("sent_cleared") and isinstance(created, (int, float))
                and (now if now is not None else _now()) - created > SENT_AUTO_AFTER)
        return {"sent": auto, "sent_at": None, "sent_auto": auto, "sent_changed": False}
    return {"sent": True, "sent_at": sent_at, "sent_auto": False,
            "sent_changed": doc.get("sent_digest") != _digest(current_translation(doc.get("state") or {}))}


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
        **sent_view(doc),
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
    out.update(_kept_sent(existing))
    return out


def _kept_sent(existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {k: existing[k] for k in ("sent_at", "sent_digest", "sent_cleared") if k in (existing or {})}


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
            doc = {**_kept_sent(existing), **doc, "rev": (existing or {}).get("rev", 0) + 1, "updated_at": _now()}
            doc.setdefault("created_at", (existing or {}).get("created_at", _now()))
            self._write(doc)
            return doc

    def set_sent(self, draft_id: str, sent: bool) -> Dict[str, Any]:
        """标记 / 撤销已发送；再标一次按现在的译文重算。rev、updated_at 不变。"""
        with self._lock:
            doc = self.get(draft_id)
            if not doc:
                raise DraftError("DRAFT_NOT_FOUND", "找不到这份翻译稿", 404)
            doc.pop("sent_at", None)
            doc.pop("sent_digest", None)
            doc.pop("sent_cleared", None)
            if sent:
                doc["sent_at"] = _now()
                doc["sent_digest"] = _digest(current_translation(doc.get("state") or {}))
            else:
                doc["sent_cleared"] = True  # 超过两周的稿子撤销后也按未发送算
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

    def list(self, query: str = "", source: str = "", limit: int = 300, sent: str = "") -> List[Dict[str, Any]]:
        """翻译记录：按最近修改从新到旧；query 在标题、原文、译文里找（每个词都要出现）；
        sent：yes 只要已发送（含超两周默认的），no 只要未发送。"""
        words = [w.lower() for w in (query or "").split() if w]
        now = _now()
        out = []
        for doc in self._all():
            if source and doc.get("source") != source:
                continue
            if sent and sent_view(doc, now)["sent"] != (sent == "yes"):
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
                    **{k: v for k, v in sent_view(doc).items() if k in ("sent", "sent_at", "sent_auto")},
                    "auto": bool(doc.get("auto")),
                    "seen": bool(doc.get("seen", True)),
                    "versions": len(state.get("versions") or []),
                    "no_post": bool((doc.get("extraction") or {}).get("has_post") is False),
                    # 列表行显示「建议 11/29 23:00 发」
                    "send_time": _send_time_badge(doc.get("send_time")),
                }
        return out


def _send_time_badge(send_time: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(send_time, dict):
        return None
    return {k: send_time.get(k) for k in ("shanghai", "shanghai_label", "date_only", "source_local", "source_label", "text")}
