"""
Chatbot 的会话：每个会话一个 JSON 文件（data/chat_sessions/<id>.json），换浏览器、换设备都在。

会话里只存消息；模型、是否联网是页面上的选择，每次发消息时带过来。
助手消息另记 model（用的模型别名）、sources（联网时引用的网页）、note（如「这个模型不能联网」）。
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

SESSION_ID_RE = re.compile(r"^c_[0-9a-f]{12}$")
MAX_MESSAGES = 400
MAX_CONTENT = 60_000
MAX_SOURCES = 20
TITLE_LIMIT = 40


class ChatSessionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def make_title(text: str) -> str:
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    return line[:TITLE_LIMIT] or "新对话"


def _message(role: str, content: str, **extra: Any) -> Dict[str, Any]:
    message = {"id": uuid.uuid4().hex[:12], "role": role, "content": content[:MAX_CONTENT], "created_at": time.time()}
    message.update({k: v for k, v in extra.items() if v})
    return message


def clean_sources(sources: Any) -> List[Dict[str, str]]:
    out = []
    for source in sources or []:
        if isinstance(source, dict) and str(source.get("url") or "").startswith(("http://", "https://")):
            out.append({"title": str(source.get("title") or source["url"])[:200], "url": str(source["url"])[:2000]})
    return out[:MAX_SOURCES]


def summarize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """会话列表里的一行。"""
    messages = doc.get("messages") or []
    return {
        "id": doc["id"],
        "title": doc.get("title") or "新对话",
        "count": len(messages),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "pinned_at": doc.get("pinned_at"),
    }


class ChatSessionStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        if not SESSION_ID_RE.match(session_id or ""):
            raise ChatSessionError("BAD_CHAT_ID", "对话 ID 不对")
        return self.root / f"{session_id}.json"

    def _read(self, session_id: str) -> Dict[str, Any]:
        path = self._path(session_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ChatSessionError("CHAT_NOT_FOUND", "这个对话已经删掉了", 404) from None
        except (OSError, ValueError) as exc:
            raise ChatSessionError("CHAT_UNREADABLE", f"对话读不出来：{exc.__class__.__name__}", 500) from exc

    def _write(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(doc["id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return doc

    def get(self, session_id: str) -> Dict[str, Any]:
        return self._read(session_id)

    def list(self, limit: int = 300) -> List[Dict[str, Any]]:
        """置顶的在前，各自按最近更新从新到旧。"""
        docs = []
        if self.root.is_dir():
            for path in self.root.glob("c_*.json"):
                try:
                    docs.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        docs.sort(key=lambda d: (d.get("pinned_at") is not None, d.get("updated_at") or 0), reverse=True)
        return [summarize(d) for d in docs[:limit]]

    def create(self, messages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """新对话；messages 用来导入以前存在浏览器里的对话。"""
        imported = [_message(m["role"], m["content"]) for m in (messages or [])
                    if m.get("role") in ("user", "assistant") and str(m.get("content") or "").strip()][-MAX_MESSAGES:]
        first_user = next((m["content"] for m in imported if m["role"] == "user"), "")
        now = time.time()
        doc = {"id": f"c_{uuid.uuid4().hex[:12]}", "title": make_title(first_user) if first_user else "新对话",
               "created_at": now, "updated_at": now, "messages": imported}
        with self._lock:
            return self._write(doc)

    def rename(self, session_id: str, title: str) -> Dict[str, Any]:
        title = (title or "").strip()[:TITLE_LIMIT]
        if not title:
            raise ChatSessionError("BAD_TITLE", "标题不能为空")
        with self._lock:
            doc = self._read(session_id)
            doc["title"] = title
            doc["titled"] = True
            return self._write(doc)

    def pin(self, session_id: str, pinned: bool) -> Dict[str, Any]:
        """置顶 / 取消置顶；不算更新，不动 updated_at。"""
        with self._lock:
            doc = self._read(session_id)
            if pinned:
                doc["pinned_at"] = time.time()
            else:
                doc.pop("pinned_at", None)
            return self._write(doc)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            try:
                self._path(session_id).unlink()
                return True
            except FileNotFoundError:
                return False

    def add_user(self, session_id: str, content: str) -> Dict[str, Any]:
        """用户发的话先存下，回复失败也不丢；第一句话当标题（用户改过标题就不动）。"""
        content = content.strip()
        if not content:
            raise ChatSessionError("EMPTY_MESSAGE", "消息不能为空")
        with self._lock:
            doc = self._read(session_id)
            if len(doc["messages"]) >= MAX_MESSAGES:
                raise ChatSessionError("CHAT_TOO_LONG", "这个对话太长了，开个新对话接着聊吧")
            if not doc.get("titled") and not any(m["role"] == "user" for m in doc["messages"]):
                doc["title"] = make_title(content)
            doc["messages"].append(_message("user", content))
            doc["updated_at"] = time.time()
            return self._write(doc)

    def drop_trailing_replies(self, session_id: str) -> Dict[str, Any]:
        """重新回答：去掉最后一条用户消息之后的回复。"""
        with self._lock:
            doc = self._read(session_id)
            while doc["messages"] and doc["messages"][-1]["role"] == "assistant":
                doc["messages"].pop()
            if not doc["messages"]:
                raise ChatSessionError("NOTHING_TO_ANSWER", "这个对话里还没有问题")
            return self._write(doc)

    def add_reply(self, session_id: str, after_id: str, content: str, *, model: str = "",
                  sources: Any = None, note: str = "") -> Dict[str, Any]:
        """回复接在它回答的那条用户消息后面；那条已经不是最后一条（期间又发了别的、或删了）就不存。"""
        with self._lock:
            doc = self._read(session_id)
            if not doc["messages"] or doc["messages"][-1]["id"] != after_id:
                raise ChatSessionError("CHAT_CHANGED", "对话在别处改过了，已重新载入", 409)
            doc["messages"].append(_message("assistant", content, model=model, sources=clean_sources(sources), note=note))
            doc["updated_at"] = time.time()
            return self._write(doc)
