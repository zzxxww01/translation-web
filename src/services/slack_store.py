"""
Slack 消息的本地副本（SQLite，data/slack_cache/slack.db）。

存 Slack 原样返回的消息 JSON，读的时候再转换（用户名、链接这些随时可能变）。每个会话记下
「本地最新到哪条」「最早到哪条」「历史是否已拉全」，同步时只向 Slack 要比最新那条更新的消息；
往前翻页时本地没有的才去 Slack 补。thread 同理按 thread 记录。

只是缓存：删掉 slack.db 不丢任何东西，下次打开会重新从 Slack 拉。
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    channel_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    ts_num REAL NOT NULL,
    thread_ts TEXT,
    -- 1 = 出现在频道主消息流里（conversations.history 返回的：普通消息、thread 根、广播到频道的回复）
    in_history INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    raw TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (channel_id, ts)
);
CREATE INDEX IF NOT EXISTS idx_history ON messages (channel_id, in_history, ts_num);
CREATE INDEX IF NOT EXISTS idx_thread ON messages (channel_id, thread_ts, ts_num);

CREATE TABLE IF NOT EXISTS conv_state (
    channel_id TEXT PRIMARY KEY,
    newest_ts TEXT,           -- 本地主消息流里最新的一条
    oldest_ts TEXT,           -- 本地主消息流里最早的一条
    complete INTEGER NOT NULL DEFAULT 0,  -- 更早的历史已经拉全
    refreshed_at REAL NOT NULL DEFAULT 0  -- 上次重拉最近几天（补编辑、删除、回复数）的时间
);

-- momo 自己的已读位置（Slack 是只读的，不往回写）。thread_ts 为空串表示整个会话
CREATE TABLE IF NOT EXISTS read_state (
    channel_id TEXT NOT NULL,
    thread_ts TEXT NOT NULL DEFAULT '',
    ts TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (channel_id, thread_ts)
);

CREATE TABLE IF NOT EXISTS thread_state (
    channel_id TEXT NOT NULL,
    thread_ts TEXT NOT NULL,
    newest_ts TEXT,           -- 本地这个 thread 里最新的一条
    fetched_at REAL NOT NULL DEFAULT 0,
    full_at REAL NOT NULL DEFAULT 0,      -- 上次整个 thread 重拉的时间
    PRIMARY KEY (channel_id, thread_ts)
);
"""


def _num(ts: Any) -> float:
    try:
        return float(ts)
    except (TypeError, ValueError):
        return 0.0


class SlackStore:
    def __init__(self, path: Path, now=time.time):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._now = now
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=NORMAL")
            self._db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- 消息

    def upsert(self, channel_id: str, messages: Iterable[Dict[str, Any]], in_history: bool) -> int:
        """写入 / 更新消息。in_history 只升不降：thread 里拉到的根消息不会把它从主消息流里拿掉。"""
        now = self._now()
        rows = []
        for m in messages:
            ts = str(m.get("ts") or "")
            if not ts:
                continue
            rows.append((channel_id, ts, _num(ts), m.get("thread_ts"), 1 if in_history else 0,
                         json.dumps(m, ensure_ascii=False), now))
        if not rows:
            return 0
        with self._lock:
            self._db.execute("BEGIN")
            self._db.executemany(
                """INSERT INTO messages (channel_id, ts, ts_num, thread_ts, in_history, deleted, raw, updated_at)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                   ON CONFLICT (channel_id, ts) DO UPDATE SET
                     thread_ts = excluded.thread_ts,
                     in_history = MAX(messages.in_history, excluded.in_history),
                     deleted = 0, raw = excluded.raw, updated_at = excluded.updated_at""",
                rows,
            )
            self._db.execute("COMMIT")
        return len(rows)

    def mark_deleted(self, channel_id: str, ts_list: Iterable[str]) -> int:
        ts_list = list(ts_list)
        if not ts_list:
            return 0
        with self._lock:
            cur = self._db.executemany(
                "UPDATE messages SET deleted = 1, updated_at = ? WHERE channel_id = ? AND ts = ?",
                [(self._now(), channel_id, ts) for ts in ts_list],
            )
            return cur.rowcount

    def history(self, channel_id: str, before: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """主消息流，新→旧；before 不含本身。"""
        sql = "SELECT raw FROM messages WHERE channel_id = ? AND in_history = 1 AND deleted = 0"
        args: List[Any] = [channel_id]
        if before:
            sql += " AND ts_num < ?"
            args.append(_num(before))
        sql += " ORDER BY ts_num DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            return [json.loads(r["raw"]) for r in self._db.execute(sql, args)]

    def history_since(self, channel_id: str, since: float) -> List[Dict[str, Any]]:
        """主消息流里 since 之后的（含已删除标记，供刷新比对用），新→旧。"""
        with self._lock:
            rows = self._db.execute(
                "SELECT ts FROM messages WHERE channel_id = ? AND in_history = 1 AND deleted = 0 AND ts_num >= ?",
                (channel_id, since),
            ).fetchall()
        return [{"ts": r["ts"]} for r in rows]

    def thread(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """thread：根消息 + 回复，旧→新。"""
        with self._lock:
            rows = self._db.execute(
                """SELECT raw FROM messages WHERE channel_id = ? AND deleted = 0 AND (ts = ? OR thread_ts = ?)
                   ORDER BY ts_num ASC""",
                (channel_id, thread_ts, thread_ts),
            ).fetchall()
        return [json.loads(r["raw"]) for r in rows]

    def message(self, channel_id: str, ts: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._db.execute("SELECT raw FROM messages WHERE channel_id = ? AND ts = ? AND deleted = 0",
                                   (channel_id, ts)).fetchone()
        return json.loads(row["raw"]) if row else None

    # -- 同步进度

    def conv_state(self, channel_id: str) -> Dict[str, Any]:
        with self._lock:
            row = self._db.execute("SELECT * FROM conv_state WHERE channel_id = ?", (channel_id,)).fetchone()
        if not row:
            return {"newest_ts": None, "oldest_ts": None, "complete": False, "refreshed_at": 0.0}
        return {"newest_ts": row["newest_ts"], "oldest_ts": row["oldest_ts"],
                "complete": bool(row["complete"]), "refreshed_at": row["refreshed_at"]}

    def set_conv_state(self, channel_id: str, **fields: Any) -> None:
        state = {**self.conv_state(channel_id), **fields}
        with self._lock:
            self._db.execute(
                """INSERT INTO conv_state (channel_id, newest_ts, oldest_ts, complete, refreshed_at) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT (channel_id) DO UPDATE SET newest_ts = excluded.newest_ts, oldest_ts = excluded.oldest_ts,
                     complete = excluded.complete, refreshed_at = excluded.refreshed_at""",
                (channel_id, state["newest_ts"], state["oldest_ts"], 1 if state["complete"] else 0, state["refreshed_at"]),
            )

    def thread_state(self, channel_id: str, thread_ts: str) -> Dict[str, Any]:
        with self._lock:
            row = self._db.execute("SELECT * FROM thread_state WHERE channel_id = ? AND thread_ts = ?",
                                   (channel_id, thread_ts)).fetchone()
        if not row:
            return {"newest_ts": None, "fetched_at": 0.0, "full_at": 0.0}
        return {"newest_ts": row["newest_ts"], "fetched_at": row["fetched_at"], "full_at": row["full_at"]}

    def set_thread_state(self, channel_id: str, thread_ts: str, **fields: Any) -> None:
        state = {**self.thread_state(channel_id, thread_ts), **fields}
        with self._lock:
            self._db.execute(
                """INSERT INTO thread_state (channel_id, thread_ts, newest_ts, fetched_at, full_at) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT (channel_id, thread_ts) DO UPDATE SET newest_ts = excluded.newest_ts,
                     fetched_at = excluded.fetched_at, full_at = excluded.full_at""",
                (channel_id, thread_ts, state["newest_ts"], state["fetched_at"], state["full_at"]),
            )

    # -- momo 本地已读

    def read_position(self, channel_id: str, thread_ts: str = "") -> Optional[str]:
        with self._lock:
            row = self._db.execute("SELECT ts FROM read_state WHERE channel_id = ? AND thread_ts = ?",
                                   (channel_id, thread_ts)).fetchone()
        return row["ts"] if row else None

    def read_positions(self) -> Dict[tuple, str]:
        with self._lock:
            rows = self._db.execute("SELECT channel_id, thread_ts, ts FROM read_state").fetchall()
        return {(r["channel_id"], r["thread_ts"]): r["ts"] for r in rows}

    def mark_read(self, channel_id: str, ts: str, thread_ts: str = "") -> bool:
        """只往前推；返回是否真的推进了。"""
        current = self.read_position(channel_id, thread_ts)
        if current and _num(ts) <= _num(current):
            return False
        with self._lock:
            self._db.execute(
                """INSERT INTO read_state (channel_id, thread_ts, ts, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT (channel_id, thread_ts) DO UPDATE SET ts = excluded.ts, updated_at = excluded.updated_at""",
                (channel_id, thread_ts, ts, self._now()),
            )
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            msgs = self._db.execute("SELECT COUNT(*) FROM messages WHERE deleted = 0").fetchone()[0]
            convs = self._db.execute("SELECT COUNT(*) FROM conv_state").fetchone()[0]
        size = sum(p.stat().st_size for p in self.path.parent.glob(self.path.name + "*") if p.is_file())
        return {"messages": msgs, "conversations": convs, "db_bytes": size}
