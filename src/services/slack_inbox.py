"""
Slack 收件箱。

用个人网页会话凭证（xoxc token + d cookie）读取「我」所在的频道和私信，
给前端 Slack 页展示。企业版工作区禁用了 conversations.list / users.conversations，
会话清单从网页端自己用的 client.userBoot（侧栏）+ client.counts（未读数）拿。

完全只读：所有 API 调用都过白名单，白名单里只有查询方法，其余一律抛错；不发送、不改消息，
也不改 Slack 里的已读状态。在 momo 里看过的位置只记在本地（slack.db 的 read_state），
显示未读时取「Slack 的已读位置」和「momo 本地已读位置」里更新的那个。凭证只发给 slack.com。
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from src.services.slack_store import SlackStore
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://slack.com/api"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 只读白名单：新增方法前先确认它不会写入、发送或改变已读状态（用户要求 Slack 及其状态完全只读）
ALLOWED_METHODS = frozenset({
    "auth.test",
    "client.counts",
    "client.userBoot",
    "conversations.info",
    "conversations.history",
    "conversations.replies",
    "search.messages",
    "subscriptions.thread.getView",
    "users.info",
})


# 私信只展示最近有往来的（天数可由 settings.slack_dm_recent_days 覆盖）
DM_RECENT_DAYS = 30
# Slackbot / Slack 官方通知账号不算往来
HIDDEN_DM_USERS = frozenset({"USLACKBOT", "USLACK"})

COUNTS_TTL_S = 30
BOOT_TTL_S = 300
# 本地副本：同一个会话 15 秒内不重复去 Slack 问有没有新消息
FRESH_TTL_S = 15
# 第一次打开一个会话先拉多少条；往前翻时一次补多少条
FIRST_PAGE = 100
BACKFILL_PAGE = 200
# 每隔多久重拉最近几天的消息，补上编辑、删除、表情、回复数这些「旧消息上的变化」
REFRESH_EVERY_S = 300
REFRESH_WINDOW_DAYS = 7
# thread：多久增量拉一次新回复、多久整个重拉一次（补编辑和删除）
THREAD_FETCH_TTL_S = 30
THREAD_FULL_EVERY_S = 600
# 后台同步间隔；图片目录超过这个大小就删最旧的
SYNC_INTERVAL_S = 60
FILES_MAX_BYTES = 2 * 1024 * 1024 * 1024
# 侧栏展开频道时列出最近多少天有动静的 thread
THREAD_RECENT_DAYS = 7
# 私信交给回复 agent 时带最近多少条
AGENT_DM_MESSAGES = 30
# AI 速览：每个会话 / thread 最多带多少条未读
DIGEST_MAX_MESSAGES = 40
SEARCH_COUNT = 30
# Muse 的 @我 兜底搜索：Slack 搜索索引会晚一点，每次往回多看这么久；最多翻几页（每页 50）
MENTION_SEARCH_LOOKBACK_S = 1800
MENTION_SEARCH_PAGES = 3
AUTH_TTL_S = 600
MAX_FILE_BYTES = 25 * 1024 * 1024

CONVERSATION_ID_RE = re.compile(r"^[CDG][A-Z0-9]{6,20}$")
FILE_ID_RE = re.compile(r"^F[A-Z0-9]{6,20}$")
TS_RE = re.compile(r"^\d{9,11}\.\d{1,6}$")

_TOKEN_RE = re.compile(r"<([^<>]+)>")
# 这些全员提醒也算「@我」
BROADCAST_MENTIONS = ("<!here", "<!channel", "<!everyone")


class SlackInboxError(Exception):
    """带错误码的用户可读错误；code 供前端分支处理（如弹出凭证输入框）。"""

    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------- 凭证


@dataclass(frozen=True)
class SlackCredentials:
    token: str
    cookie_d: str


def normalize_credentials(token: str, cookie_d: str) -> SlackCredentials:
    token = (token or "").strip()
    cookie = (cookie_d or "").strip()
    if cookie.lower().startswith("cookie:"):
        cookie = cookie[len("cookie:"):].strip()
    if cookie.startswith("d="):
        cookie = cookie[2:]
    cookie = cookie.strip(" ;")
    if not token.startswith("xoxc-"):
        raise SlackInboxError("INVALID_CREDENTIALS", "token 应该以 xoxc- 开头", 400)
    if not cookie.startswith("xoxd-"):
        raise SlackInboxError("INVALID_CREDENTIALS", "d cookie 应该以 xoxd- 开头", 400)
    if any(ch in token + cookie for ch in "\r\n;"):
        raise SlackInboxError("INVALID_CREDENTIALS", "凭证里不能有换行或分号", 400)
    return SlackCredentials(token=token, cookie_d=cookie)


class SlackCredentialStore:
    """凭证存成 JSON 文件（600 权限），格式与 PoC 的 slack_config.json 相同。"""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Optional[SlackCredentials]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            logger.warning("Slack 凭证文件无法解析: %s", self.path)
            return None
        try:
            return normalize_credentials(data.get("token", ""), data.get("cookie_d", ""))
        except SlackInboxError:
            return None

    def save(self, token: str, cookie_d: str) -> SlackCredentials:
        creds = normalize_credentials(token, cookie_d)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"token": creds.token, "cookie_d": creds.cookie_d}, fh)
        os.replace(tmp_path, self.path)
        return creds


# ---------------------------------------------------------------- 只读客户端


def _is_slack_file_url(url: str) -> bool:
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "slack.com" or host.endswith(".slack.com"))


class SlackReadOnlyClient:
    def __init__(self, creds: SlackCredentials, http: Optional[httpx.Client] = None):
        # 不走 .env 里给 LLM 配的 HTTP(S)_PROXY：那个代理连不到 Slack，而服务器直连 slack.com 是通的
        self._http = http or httpx.Client(timeout=20.0, follow_redirects=False, trust_env=False)
        self._headers = {
            "Authorization": f"Bearer {creds.token}",
            "Cookie": f"d={creds.cookie_d}",
            "User-Agent": USER_AGENT,
        }

    def call(self, method: str, **params: Any) -> Dict[str, Any]:
        if method not in ALLOWED_METHODS:
            raise SlackInboxError("METHOD_NOT_ALLOWED", f"Slack 方法 {method} 不在只读白名单里", 500)
        try:
            resp = self._http.get(f"{API_BASE}/{method}", params=params, headers=self._headers)
        except httpx.HTTPError as exc:
            raise SlackInboxError("SLACK_UNREACHABLE", f"连不上 Slack：{exc.__class__.__name__}") from exc
        if resp.status_code == 429:
            raise SlackInboxError("RATE_LIMITED", "Slack 限流了，稍等一分钟再刷新", 429)
        try:
            data = resp.json()
        except ValueError as exc:
            raise SlackInboxError("SLACK_BAD_RESPONSE", f"Slack 返回了非 JSON（HTTP {resp.status_code}）") from exc
        if not data.get("ok"):
            error = str(data.get("error") or "unknown_error")
            if error in {"invalid_auth", "not_authed", "token_revoked", "account_inactive", "token_expired"}:
                raise SlackInboxError("CREDENTIALS_EXPIRED", "Slack 凭证已失效，请重新复制一份填进来", 401)
            if error == "ratelimited":
                raise SlackInboxError("RATE_LIMITED", "Slack 限流了，稍等一分钟再刷新", 429)
            raise SlackInboxError("SLACK_ERROR", f"Slack 接口 {method} 报错：{error}")
        return data

    def download(self, url: str) -> Tuple[bytes, str]:
        if not _is_slack_file_url(url):
            raise SlackInboxError("FILE_NOT_ALLOWED", "只下载 slack.com 上的文件", 400)
        try:
            with self._http.stream("GET", url, headers=self._headers) as resp:
                if resp.status_code != 200:
                    raise SlackInboxError("FILE_DOWNLOAD_FAILED", f"文件下载失败（HTTP {resp.status_code}）")
                content_type = resp.headers.get("content-type", "application/octet-stream")
                # 凭证失效时 Slack 会回登录页 HTML 而不是 401
                if content_type.startswith("text/html"):
                    raise SlackInboxError("CREDENTIALS_EXPIRED", "Slack 凭证已失效，文件下载被重定向到登录页", 401)
                chunks: List[bytes] = []
                size = 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise SlackInboxError("FILE_TOO_LARGE", "文件超过 25MB，请到 Slack 里查看", 413)
                    chunks.append(chunk)
        except httpx.HTTPError as exc:
            raise SlackInboxError("SLACK_UNREACHABLE", f"连不上 Slack：{exc.__class__.__name__}") from exc
        return b"".join(chunks), content_type


# ---------------------------------------------------------------- 文本解析


def _unescape(text: str) -> str:
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def parse_slack_text(text: str, user_name: Callable[[str], str]) -> List[Dict[str, str]]:
    """把 Slack mrkdwn 拆成片段：text / link / mention。前端按片段渲染，不用 innerHTML。"""
    segments: List[Dict[str, str]] = []

    def push_text(value: str) -> None:
        if not value:
            return
        if segments and segments[-1]["type"] == "text":
            segments[-1]["text"] += value
        else:
            segments.append({"type": "text", "text": value})

    pos = 0
    for match in _TOKEN_RE.finditer(text or ""):
        push_text(_unescape(text[pos:match.start()]))
        pos = match.end()
        body = match.group(1)
        target, _, label = body.partition("|")
        label = _unescape(label)
        if target.startswith("@S"):
            # 搜索结果里用户组提及是 <@S…> 这种写法，S 开头的不是用户 ID
            segments.append({"type": "mention", "text": "@" + (label.lstrip("@") or "用户组")})
        elif target.startswith("@"):
            segments.append({"type": "mention", "text": "@" + (label.lstrip("@") or user_name(target[1:]))})
        elif target.startswith("#"):
            segments.append({"type": "mention", "text": "#" + (label or target[1:])})
        elif target.startswith("!subteam^"):
            segments.append({"type": "mention", "text": "@" + (label.lstrip("@") or "用户组")})
        elif target.startswith("!"):
            name = target[1:].split("^", 1)[0]
            segments.append({"type": "mention", "text": "@" + (label.lstrip("@") or name)})
        elif target.startswith("tel:"):
            push_text(label or target[4:])
        else:
            url = _unescape(target)
            if url.startswith(("http://", "https://", "mailto:")):
                segments.append({"type": "link", "url": url, "text": label or url})
            else:
                # slack://user?…|名字 这类应用内链接：有显示名就只留名字，不把标记原样露出来
                push_text(label or _unescape(match.group(0)))
    push_text(_unescape((text or "")[pos:]))
    return segments


def segments_to_plain(segments: List[Dict[str, str]]) -> str:
    parts = []
    for seg in segments:
        if seg["type"] == "link" and seg["text"] != seg["url"]:
            parts.append(f"{seg['text']} ({seg['url']})")
        else:
            parts.append(seg.get("text", ""))
    return "".join(parts)


def mpim_label(name: str, me: str) -> str:
    """群聊私信名：「Group messaging with: @a @b @me」或「mpdm-a--b--me-1」→「a, b」（去掉自己）。"""
    if name.lower().startswith("group messaging with:"):
        members = [m.lstrip("@") for m in name.split(":", 1)[1].split()]
    elif name.startswith("mpdm-"):
        members = re.sub(r"-\d+$", "", name[len("mpdm-"):]).split("--")
    else:
        return name
    others = [m for m in members if m and m != me]
    return ", ".join(others or members) or name


def _later(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """两个 ts 取更新的那个（都可能为空）。"""
    if not a:
        return b or None
    if not b:
        return a
    return a if float(a) >= float(b) else b


def format_ts(ts: str) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------------- 收件箱


class _TTLCache:
    def __init__(self) -> None:
        self._data: Dict[Any, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any, ttl: float) -> Any:
        with self._lock:
            hit = self._data.get(key)
            if hit and time.monotonic() - hit[0] < ttl:
                return hit[1]
        return None

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            if len(self._data) > 500:
                oldest = sorted(self._data.items(), key=lambda kv: kv[1][0])[:100]
                for k, _ in oldest:
                    self._data.pop(k, None)

    def pop(self, key: Any) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class SlackInbox:
    """进程级单例：缓存会话、用户名和附件，供路由同步调用（路由里走 run_blocking）。"""

    def __init__(
        self,
        store: SlackCredentialStore,
        cache_dir: Path,
        client_factory: Callable[[SlackCredentials], SlackReadOnlyClient] = SlackReadOnlyClient,
        now: Callable[[], float] = time.time,
        dm_recent_days: int = DM_RECENT_DAYS,
    ):
        self.store = store
        self.cache_dir = Path(cache_dir)
        self._client_factory = client_factory
        self._now = now
        self.dm_recent_days = dm_recent_days
        self._lock = threading.RLock()
        self._client: Optional[SlackReadOnlyClient] = None
        self._client_creds: Optional[SlackCredentials] = None
        self._cache = _TTLCache()
        self._users: Dict[str, Dict[str, Any]] = {}
        self._conv_info: Dict[str, Dict[str, Any]] = {}
        self._files: Dict[str, Dict[str, str]] = {}
        self._load_user_cache()
        # 消息的本地副本；同步时只向 Slack 要本地没有的
        self.db = SlackStore(self.cache_dir / "slack.db", now=now)
        self._conv_locks: Dict[str, threading.Lock] = {}
        self._sync_thread: Optional[threading.Thread] = None
        self._prefetch_queue: "queue.Queue[str]" = queue.Queue()
        self._prefetch_thread: Optional[threading.Thread] = None
        self._last_prune = 0.0
        self._last_sync: Optional[float] = None

    # -- 基础

    def client(self) -> SlackReadOnlyClient:
        creds = self.store.load()
        if creds is None:
            raise SlackInboxError("CREDENTIALS_MISSING", "还没有配置 Slack 凭证", 400)
        with self._lock:
            if self._client is None or creds != self._client_creds:
                self._client = self._client_factory(creds)
                self._client_creds = creds
                self._cache.clear()
            return self._client

    def save_credentials(self, token: str, cookie_d: str) -> Dict[str, Any]:
        self.store.save(token, cookie_d)
        return self.status()

    def auth(self) -> Dict[str, Any]:
        cached = self._cache.get("auth", AUTH_TTL_S)
        if cached:
            return cached
        data = self.client().call("auth.test")
        info = {
            "user": data.get("user", ""),
            "user_id": data.get("user_id", ""),
            "team": data.get("team", ""),
            "url": (data.get("url") or "").rstrip("/"),
        }
        self._cache.put("auth", info)
        return info

    def status(self) -> Dict[str, Any]:
        if self.store.load() is None:
            return {"configured": False, "ok": False, "error_code": "CREDENTIALS_MISSING", "error": "还没有配置 Slack 凭证"}
        try:
            return {"configured": True, "ok": True, **self.auth(), "local": {**self.db.stats(), "last_sync": self._last_sync}}
        except SlackInboxError as exc:
            return {"configured": True, "ok": False, "error_code": exc.code, "error": exc.message}

    # -- 用户

    def _user_cache_path(self) -> Path:
        return self.cache_dir / "users.json"

    def _load_user_cache(self) -> None:
        try:
            data = json.loads(self._user_cache_path().read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._users = {k: v for k, v in data.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            pass

    def _save_user_cache(self) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._user_cache_path().with_suffix(".tmp")
            tmp.write_text(json.dumps(self._users, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self._user_cache_path())
        except OSError:
            logger.warning("写 Slack 用户缓存失败", exc_info=True)

    def user(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return {"name": "", "is_bot": False}
        cached = self._users.get(user_id)
        if cached:
            return cached
        try:
            data = self.client().call("users.info", user=user_id).get("user", {})
        except SlackInboxError as exc:
            if exc.code in {"CREDENTIALS_EXPIRED", "CREDENTIALS_MISSING"}:
                raise
            return {"name": user_id, "is_bot": False}
        profile = data.get("profile", {}) or {}
        info = {
            "name": profile.get("display_name") or profile.get("real_name") or data.get("real_name") or data.get("name") or user_id,
            "real_name": profile.get("real_name") or data.get("real_name") or "",
            "is_bot": bool(data.get("is_bot")),
        }
        with self._lock:
            self._users[user_id] = info
            self._save_user_cache()
        return info

    def user_name(self, user_id: str) -> str:
        return self.user(user_id).get("name") or user_id

    # -- 会话

    def _remember_conversation(self, ch: Dict[str, Any]) -> Dict[str, Any]:
        channel_id = ch.get("id", "")
        if ch.get("is_im"):
            kind = "im"
        elif ch.get("is_mpim"):
            kind = "mpim"
        else:
            kind = "private" if ch.get("is_private") else "channel"
        info = {"id": channel_id, "kind": kind, "name": ch.get("name") or "", "user": ch.get("user") or ""}
        if kind == "mpim":
            purpose = ((ch.get("purpose") or {}).get("value") or "").strip()
            info["name"] = purpose or info["name"]
        with self._lock:
            self._conv_info[channel_id] = info
        return info

    def _conversation_info(self, channel_id: str) -> Dict[str, Any]:
        cached = self._conv_info.get(channel_id)
        if cached:
            return cached
        ch = self.client().call("conversations.info", channel=channel_id).get("channel", {})
        return self._remember_conversation({**ch, "id": channel_id})

    def _counts(self, refresh: bool = False) -> Dict[str, Any]:
        counts = None if refresh else self._cache.get("counts", COUNTS_TTL_S)
        if counts is None:
            counts = self.client().call("client.counts", thread_counts_by_channel="true")
            self._cache.put("counts", counts)
        return counts

    def _boot(self, refresh: bool = False) -> Dict[str, Any]:
        """网页端加载侧栏用的数据（完整频道列表、打开的私信）。拿不到就返回 {}，只靠 client.counts。"""
        cached = None if refresh else self._cache.get("boot", BOOT_TTL_S)
        if cached is not None:
            return cached
        try:
            data = self.client().call("client.userBoot")
        except SlackInboxError as exc:
            if exc.code in {"CREDENTIALS_EXPIRED", "CREDENTIALS_MISSING", "RATE_LIMITED"}:
                raise
            logger.warning("client.userBoot 不可用，会话列表只用 client.counts：%s", exc.message)
            data = {}
        boot = {"channels": data.get("channels") or [], "ims": data.get("ims") or [], "is_open": data.get("is_open"),
                "my_groups": _my_subteams(data)}
        self._cache.put("boot", boot)
        return boot

    def _thread_read(self, channel_id: str, thread_ts: str, followed: Optional[Dict[str, Any]],
                     local: Optional[Dict[tuple, str]] = None) -> Optional[str]:
        """thread 的已读位置：Slack 记的（只有我参与的 thread 才有）和 momo 本地记的，取更新的。"""
        local_ts = (local or {}).get((channel_id, thread_ts)) if local is not None else self.db.read_position(channel_id, thread_ts)
        return _later((followed or {}).get("last_read"), local_ts)

    def _thread_unread_counts(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """按频道数我参与的 thread 里有几个有新回复、几个新回复里 @了我（已结合本地已读）。"""
        local = self.db.read_positions()
        me = self.auth().get("user_id", "")
        unreads: Dict[str, int] = {}
        mentions: Dict[str, int] = {}
        for (cid, ts), f in self._followed_threads().items():
            read = self._thread_read(cid, ts, f, local)
            latest = str(f["root"].get("latest_reply") or "")
            if not latest or float(latest) <= float(read or 0):
                continue
            unreads[cid] = unreads.get(cid, 0) + 1
            if me and any(f"<@{me}" in (r.get("text") or "") for r in f["latest_replies"]
                          if float(r.get("ts") or 0) > float(read or 0)):
                mentions[cid] = mentions.get(cid, 0) + 1
        return unreads, mentions

    def thread_badge(self) -> Dict[str, Any]:
        unreads, mentions = self._thread_unread_counts()
        return {"has_unreads": bool(unreads), "mention_count": sum(mentions.values())}

    def conversations(self, refresh: bool = False) -> List[Dict[str, Any]]:
        counts = self._counts(refresh)
        boot = self._boot(refresh)
        me = self.auth().get("user_id", "")
        cutoff = self._now() - self.dm_recent_days * 86400
        open_ids = set(boot["is_open"] or [])

        # 候选会话：侧栏里的频道 + 打开着的私信，再补上 client.counts 里有动静的
        candidates: Dict[str, bool] = {}  # id -> 是否在 Slack 侧栏里打开着
        for ch in boot["channels"] + boot["ims"]:
            cid = ch.get("id", "")
            if not CONVERSATION_ID_RE.match(cid) or ch.get("is_archived"):
                continue
            info = self._remember_conversation(ch)
            is_open = info["kind"] in {"channel", "private"} or ch.get("is_open") or cid in open_ids
            if is_open:
                candidates[cid] = True
        counts_by_id: Dict[str, Dict[str, Any]] = {}
        for group in ("channels", "mpims", "ims"):
            for item in counts.get(group, []) or []:
                cid = item.get("id", "")
                if CONVERSATION_ID_RE.match(cid):
                    counts_by_id[cid] = item
                    candidates.setdefault(cid, False)

        thread_unreads, thread_mentions = self._thread_unread_counts()
        local_reads = self.db.read_positions()
        result = []
        for cid, is_open in candidates.items():
            item = counts_by_id.get(cid, {})
            latest = str(item.get("latest") or "0")
            try:
                latest_f = float(latest)
            except ValueError:
                latest_f = 0.0
            info = self._conversation_info(cid)
            # 私信：Slack 侧栏里打开着的都显示；没打开的只显示最近有往来的
            if info["kind"] in {"im", "mpim"} and not is_open and latest_f < cutoff:
                continue
            slack_read = str(item.get("last_read") or "")
            # Slack 只读：已读位置取 Slack 的和 momo 本地的里更新的那个；本地看到最新了就不算未读
            last_read = _later(slack_read if TS_RE.match(slack_read) else None, local_reads.get((cid, "")))
            read_all = bool(last_read) and latest_f > 0 and latest_f <= float(last_read)
            entry = {
                "id": cid,
                "kind": info["kind"],
                "name": info["name"],
                "latest_ts": latest if latest_f else None,
                "latest_time": format_ts(latest) if latest_f else "",
                "last_read": last_read,
                "has_unreads": bool(item.get("has_unreads")) and not read_all,
                "mention_count": 0 if read_all else int(item.get("mention_count") or 0),
                "thread_unreads": int(thread_unreads.get(cid) or 0),
                "thread_mentions": int(thread_mentions.get(cid) or 0),
            }
            if info["kind"] == "mpim":
                entry["name"] = mpim_label(info["name"], self.auth().get("user", ""))
            if info["kind"] == "im":
                peer = info["user"]
                if peer in HIDDEN_DM_USERS or peer == me:
                    continue
                user = self.user(peer)
                if user.get("is_bot"):
                    continue
                entry["name"] = user.get("real_name") or user.get("name") or peer
            result.append(entry)
        # 和 Slack 侧栏一样：频道按名字排，私信按最近消息排
        result.sort(key=lambda e: (0, e["name"].lower(), 0.0) if e["kind"] in {"channel", "private"}
                    else (1, "", -float(e["latest_ts"] or 0)))
        return result

    def _require_conversation(self, channel_id: str) -> None:
        if not CONVERSATION_ID_RE.match(channel_id or ""):
            raise SlackInboxError("BAD_CONVERSATION", "会话 ID 格式不对", 400)
        if channel_id not in {c["id"] for c in self.conversations()}:
            raise SlackInboxError("CONVERSATION_NOT_VISIBLE", "这个会话不在展示范围内", 404)

    # -- 消息

    def _permalink(self, channel_id: str, ts: str, thread_ts: Optional[str] = None) -> str:
        base = self.auth().get("url") or "https://app.slack.com"
        link = f"{base}/archives/{channel_id}/p{ts.replace('.', '')}"
        if thread_ts and thread_ts != ts:
            link += f"?thread_ts={thread_ts}&cid={channel_id}"
        return link

    def normalize_message(self, channel_id: str, msg: Dict[str, Any]) -> Dict[str, Any]:
        ts = str(msg.get("ts", ""))
        user_id = msg.get("user") or ""
        if user_id:
            sender = self.user_name(user_id)
        else:
            sender = (msg.get("bot_profile") or {}).get("name") or msg.get("username") or "Bot"
        segments = parse_slack_text(msg.get("text", ""), self.user_name)
        files = []
        for f in msg.get("files", []) or []:
            fid = self._register_file(f)
            if not fid:
                continue
            meta = self._files[fid]
            files.append({
                "id": fid,
                "name": meta["name"],
                "mimetype": meta["mimetype"],
                "is_image": meta["mimetype"].startswith("image/"),
                "url": f"/api/slack-inbox/files/{fid}",
            })
        attachments = []
        for a in msg.get("attachments", []) or []:
            # 卡片正文和消息正文一样是 mrkdwn：<网址|文字>、<@U…> 拆成片段，纯文本里不留标记
            card_segments = parse_slack_text(a.get("text") or "", self.user_name)
            attachments.append({
                "service_name": a.get("service_name") or "",
                "title": a.get("title") or a.get("fallback") or "",
                "title_link": a.get("title_link") or a.get("from_url") or "",
                "text": segments_to_plain(card_segments),
                "segments": card_segments,
            })
        thread_ts = msg.get("thread_ts")
        me = self.auth().get("user_id", "")
        raw_text = msg.get("text") or ""
        return {
            "ts": ts,
            "time": format_ts(ts),
            "user_id": user_id,
            "user_name": sender,
            "is_me": bool(me) and user_id == me,
            "mentions_me": bool(me) and (f"<@{me}" in raw_text or any(t in raw_text for t in BROADCAST_MENTIONS)),
            "subtype": msg.get("subtype"),
            "segments": segments,
            "text": segments_to_plain(segments),
            "thread_ts": thread_ts,
            "reply_count": int(msg.get("reply_count") or 0),
            "latest_reply": msg.get("latest_reply"),
            "edited": bool(msg.get("edited")),
            "files": files,
            "attachments": attachments,
            "reactions": [{"name": r.get("name", ""), "count": int(r.get("count") or 0)} for r in msg.get("reactions", []) or []],
            "permalink": self._permalink(channel_id, ts, thread_ts),
        }

    # -- 本地副本与增量同步

    def _conv_lock(self, channel_id: str) -> threading.Lock:
        with self._lock:
            return self._conv_locks.setdefault(channel_id, threading.Lock())

    def _fetch_history(self, channel_id: str, max_pages: int, **params: Any) -> Tuple[List[Dict[str, Any]], bool]:
        """按游标翻页拉 conversations.history，返回（消息，是否还有更多没拉）。"""
        collected: List[Dict[str, Any]] = []
        cursor = None
        for _ in range(max_pages):
            args = {"channel": channel_id, **params}
            if cursor:
                args["cursor"] = cursor
            data = self.client().call("conversations.history", **args)
            collected.extend(data.get("messages") or [])
            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not data.get("has_more"):
                return collected, False
            if not cursor:
                return collected, True  # 还有更多但翻不了页：当作没拉全
        return collected, True

    def sync_conversation(self, channel_id: str, latest_hint: Optional[str] = None, force: bool = False) -> int:
        """把会话的新消息拉进本地，返回新拉到的条数。latest_hint 是 client.counts 里的最新 ts：
        本地已经有了就一次都不问 Slack。隔一段时间重拉最近几天，补编辑、删除和回复数。"""
        if not force and self._cache.get(("fresh", channel_id), FRESH_TTL_S):
            return 0
        with self._conv_lock(channel_id):
            if not force and self._cache.get(("fresh", channel_id), FRESH_TTL_S):
                return 0
            state = self.db.conv_state(channel_id)
            now = self._now()
            new: List[Dict[str, Any]] = []
            if state["newest_ts"] is None:
                # 第一次：只拉最近一页，更早的等往上翻时再补
                new, more = self._fetch_history(channel_id, 1, limit=FIRST_PAGE)
                self.db.upsert(channel_id, new, in_history=True)
                tss = [str(m.get("ts")) for m in new if m.get("ts")]
                self.db.set_conv_state(
                    channel_id,
                    newest_ts=max(tss, key=float) if tss else "0",
                    oldest_ts=min(tss, key=float) if tss else None,
                    complete=not more,
                    refreshed_at=now,
                )
            else:
                if latest_hint is None or float(latest_hint) > float(state["newest_ts"] or 0):
                    new, _ = self._fetch_history(channel_id, 25, oldest=state["newest_ts"], limit=200)
                    if new:
                        self.db.upsert(channel_id, new, in_history=True)
                        newest = max([str(m["ts"]) for m in new if m.get("ts")] + [state["newest_ts"]], key=float)
                        self.db.set_conv_state(channel_id, newest_ts=newest)
                if now - state["refreshed_at"] > REFRESH_EVERY_S:
                    self._refresh_window(channel_id, now)
            self._cache.put(("fresh", channel_id), True)
        self._prefetch_images(new)
        return len(new)

    def _refresh_window(self, channel_id: str, now: float) -> None:
        since = now - REFRESH_WINDOW_DAYS * 86400
        recent, more = self._fetch_history(channel_id, 3, oldest=f"{since:.6f}", limit=200)
        self.db.upsert(channel_id, recent, in_history=True)
        if not more:
            # 拉全了这段时间：本地有、Slack 没有的就是被删了
            seen = {str(m.get("ts")) for m in recent}
            gone = [r["ts"] for r in self.db.history_since(channel_id, since) if r["ts"] not in seen]
            self.db.mark_deleted(channel_id, gone)
        self.db.set_conv_state(channel_id, refreshed_at=now)

    def _backfill(self, channel_id: str) -> None:
        """本地往前没有了：从本地最早那条再往前拉一页。"""
        with self._conv_lock(channel_id):
            state = self.db.conv_state(channel_id)
            if state["complete"]:
                return
            params: Dict[str, Any] = {"limit": BACKFILL_PAGE}
            if state["oldest_ts"]:
                params["latest"] = state["oldest_ts"]
            older, more = self._fetch_history(channel_id, 1, **params)
            self.db.upsert(channel_id, older, in_history=True)
            tss = [str(m.get("ts")) for m in older if m.get("ts")]
            oldest = min(tss + ([state["oldest_ts"]] if state["oldest_ts"] else []), key=float) if tss or state["oldest_ts"] else None
            self.db.set_conv_state(channel_id, oldest_ts=oldest, complete=not more or not older)

    def _latest_hint(self, channel_id: str) -> Optional[str]:
        conv = next((c for c in self.conversations() if c["id"] == channel_id), None)
        return (conv or {}).get("latest_ts")

    def messages(self, channel_id: str, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        """从本地副本读，新→旧；cursor 是上一页最早那条的 ts。本地不够时才去 Slack 往前补。"""
        self._require_conversation(channel_id)
        limit = max(1, min(int(limit), 200))
        if cursor and not TS_RE.match(cursor):
            raise SlackInboxError("BAD_CURSOR", "分页游标格式不对", 400)
        self.sync_conversation(channel_id, self._latest_hint(channel_id))
        rows = self.db.history(channel_id, before=cursor, limit=limit)
        if len(rows) < limit and not self.db.conv_state(channel_id)["complete"]:
            self._backfill(channel_id)
            rows = self.db.history(channel_id, before=cursor, limit=limit)
        complete = self.db.conv_state(channel_id)["complete"]
        # 还能往前翻：Slack 那边没拉全，或者本地还有更早的
        has_more = bool(rows) and (not complete or bool(self.db.history(channel_id, before=rows[-1]["ts"], limit=1)))
        msgs = [self.normalize_message(channel_id, m) for m in rows]
        return {"messages": msgs, "next_cursor": rows[-1]["ts"] if has_more else None}

    def sync_thread(self, channel_id: str, thread_ts: str, force: bool = False) -> None:
        """thread 进本地：隔 30 秒只要新回复，隔 10 分钟整个重拉一次（补编辑和删除）。"""
        key = f"{channel_id}:{thread_ts}"
        fetched: List[Dict[str, Any]] = []
        with self._conv_lock(key):
            state = self.db.thread_state(channel_id, thread_ts)
            now = self._now()
            if force or now - state["full_at"] > THREAD_FULL_EVERY_S:
                collected: List[Dict[str, Any]] = []
                cursor = None
                for _ in range(5):  # 最多 1000 条，够任何一个帖子 thread
                    params: Dict[str, Any] = {"channel": channel_id, "ts": thread_ts, "limit": 200}
                    if cursor:
                        params["cursor"] = cursor
                    data = self.client().call("conversations.replies", **params)
                    collected.extend(data.get("messages") or [])
                    cursor = (data.get("response_metadata") or {}).get("next_cursor")
                    if not data.get("has_more") or not cursor:
                        break
                self._store_thread(channel_id, thread_ts, collected)
                fetched = collected
                seen = {str(m.get("ts")) for m in collected}
                self.db.mark_deleted(channel_id, [m["ts"] for m in self.db.thread(channel_id, thread_ts)
                                                  if m["ts"] not in seen and m["ts"] != thread_ts])
                self.db.set_thread_state(channel_id, thread_ts, full_at=now, fetched_at=now,
                                         newest_ts=max(seen, key=float) if seen else thread_ts)
            elif now - state["fetched_at"] > THREAD_FETCH_TTL_S:
                data = self.client().call("conversations.replies", channel=channel_id, ts=thread_ts,
                                          oldest=state["newest_ts"] or thread_ts, limit=200)
                newer = data.get("messages") or []
                self._store_thread(channel_id, thread_ts, newer)
                fetched = newer
                tss = [str(m.get("ts")) for m in newer if m.get("ts")] + [state["newest_ts"] or thread_ts]
                self.db.set_thread_state(channel_id, thread_ts, fetched_at=now, newest_ts=max(tss, key=float))
        self._prefetch_images(fetched)

    def _store_thread(self, channel_id: str, thread_ts: str, messages: List[Dict[str, Any]]) -> None:
        # 根消息和「同时发到频道」的回复也在主消息流里；根消息带着最新的回复数，顺便把频道里那条更新掉
        in_stream = [m for m in messages if str(m.get("ts")) == thread_ts or m.get("subtype") == "thread_broadcast"]
        self.db.upsert(channel_id, in_stream, in_history=True)
        self.db.upsert(channel_id, [m for m in messages if m not in in_stream], in_history=False)

    def replies(self, channel_id: str, thread_ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(thread_ts or ""):
            raise SlackInboxError("BAD_TS", "thread ts 格式不对", 400)
        self.sync_thread(channel_id, thread_ts)
        collected = self.db.thread(channel_id, thread_ts)
        followed = self._followed_threads().get((channel_id, thread_ts))
        return {
            "messages": [self.normalize_message(channel_id, m) for m in collected],
            "last_read": self._thread_read(channel_id, thread_ts, followed),
        }

    def _recent_raw(self, channel_id: str, limit: int) -> List[Dict[str, Any]]:
        self.sync_conversation(channel_id, self._latest_hint(channel_id))
        return self.db.history(channel_id, limit=limit)

    # -- thread

    def _followed_threads(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """我参与（订阅）的 thread：(频道, thread_ts) -> 原始条目，带 Slack 记录的 thread 已读位置。"""
        cached = self._cache.get("thread_view", COUNTS_TTL_S)
        if cached is None:
            try:
                data = self.client().call("subscriptions.thread.getView", limit=50, org_wide_aware="true")
            except SlackInboxError as exc:
                if exc.code in {"CREDENTIALS_EXPIRED", "CREDENTIALS_MISSING", "RATE_LIMITED"}:
                    raise
                logger.warning("subscriptions.thread.getView 不可用：%s", exc.message)
                data = {}
            cached = {}
            for item in data.get("threads") or []:
                root = item.get("root_msg") or {}
                cid, ts = root.get("channel") or "", str(root.get("thread_ts") or root.get("ts") or "")
                if CONVERSATION_ID_RE.match(cid) and TS_RE.match(ts):
                    cached[(cid, ts)] = {
                        "root": root,
                        "last_read": str(root.get("last_read") or "") or None,
                        "latest_replies": item.get("latest_replies") or [],
                    }
            self._cache.put("thread_view", cached)
        return cached

    def _thread_entry(self, channel_id: str, root: Dict[str, Any], followed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        msg = self.normalize_message(channel_id, root)
        latest = str(root.get("latest_reply") or "")
        last_read = self._thread_read(channel_id, msg["ts"], followed)
        # 只有我参与的、或在 momo 里看过的 thread 才知道读到哪了
        unread = bool(last_read) and bool(latest) and float(latest) > float(last_read)
        new_replies = [
            self.normalize_message(channel_id, r)
            for r in (followed or {}).get("latest_replies", [])
            if float(r.get("ts") or 0) > float(last_read or 0)
        ]
        return {
            "channel_id": channel_id,
            "thread_ts": msg["ts"],
            "root": msg,
            "reply_count": msg["reply_count"],
            "latest_reply": latest or None,
            "latest_time": format_ts(latest) if latest else "",
            "last_read": last_read,
            "following": bool(followed),
            "has_unreads": unread,
            "mentions_me": (unread and msg["mentions_me"]) or any(r["mentions_me"] for r in new_replies),
            "latest_replies": [self.normalize_message(channel_id, r) for r in (followed or {}).get("latest_replies", [])],
        }

    def threads(self) -> Dict[str, Any]:
        """侧栏「Threads」：我参与的 thread，有新回复的排前面。"""
        visible = {c["id"] for c in self.conversations()}
        items = [
            self._thread_entry(cid, f["root"], f)
            for (cid, _), f in self._followed_threads().items()
            if cid in visible
        ]
        items.sort(key=lambda t: (not t["has_unreads"], -float(t["latest_reply"] or t["thread_ts"])))
        return {"threads": items}

    def channel_threads(self, channel_id: str) -> Dict[str, Any]:
        """侧栏展开频道：最近 THREAD_RECENT_DAYS 天有回复的 thread（最新一页消息里找 + 我参与的）。"""
        self._require_conversation(channel_id)
        followed = self._followed_threads()
        cutoff = self._now() - THREAD_RECENT_DAYS * 86400
        roots: Dict[str, Dict[str, Any]] = {}
        for m in self._recent_raw(channel_id, 200):
            ts = str(m.get("ts") or "")
            if m.get("reply_count") and m.get("thread_ts") == ts:
                roots[ts] = m
        for (cid, ts), f in followed.items():
            if cid == channel_id:
                roots.setdefault(ts, f["root"])
        items = []
        for ts, root in roots.items():
            if float(root.get("latest_reply") or ts) < cutoff:
                continue
            items.append(self._thread_entry(channel_id, root, followed.get((channel_id, ts))))
        items.sort(key=lambda t: -float(t["latest_reply"] or t["thread_ts"]))
        return {"threads": items[:30]}

    def activity(self) -> Dict[str, Any]:
        """「动态」列表：频道里最近 THREAD_RECENT_DAYS 天的 thread（含还没人回复的新帖）和私信，各占一行，按最近活动从新到旧。

        thread 行带根消息、最后一条回复和参与的人（来自本地副本；没参与的 thread 打开时才整个拉下来）。
        新帖（2026-11-21 起）也是一行 thread，reply_count 为 0：帖子翻译最常处理的就是刚发、还没人回的帖子。
        """
        me = self.auth().get("user_id", "")
        cutoff = self._now() - THREAD_RECENT_DAYS * 86400
        local_reads = self.db.read_positions()
        items: List[Dict[str, Any]] = []
        for conv in self.conversations():
            cid = conv["id"]
            if conv["kind"] in {"channel", "private"}:
                threads = self.channel_threads(cid)["threads"]
                listed = {t["thread_ts"] for t in threads}
                # channel_threads 已经同步过这个频道，这里直接读本地副本
                for m in self.db.history(cid, limit=200):
                    ts = str(m.get("ts") or "")
                    if not TS_RE.match(ts) or ts in listed or float(ts) < cutoff or m.get("reply_count"):
                        continue
                    if m.get("subtype") in _SILENT_SUBTYPES or (m.get("thread_ts") and m.get("thread_ts") != ts):
                        continue  # 系统消息、「同时发到频道」的 thread 回复
                    msg = self.normalize_message(cid, m)
                    read = _later(conv["last_read"], local_reads.get((cid, ts)))
                    items.append({
                        "type": "thread",
                        "channel_id": cid,
                        "channel_name": conv["name"],
                        "thread_ts": ts,
                        "root": msg,
                        "reply_count": 0,
                        "participants": [msg["user_name"]] if msg["user_name"] else [],
                        "last": None,
                        "latest_ts": ts,
                        "latest_time": msg["time"],
                        "has_unreads": not msg["is_me"] and (not read or float(ts) > float(read)),
                        "mentions_me": msg["mentions_me"],
                    })
                for t in threads:
                    local = self.db.thread(cid, t["thread_ts"])
                    replies = [m for m in local if str(m.get("ts")) != t["thread_ts"]]
                    people: List[str] = []
                    for m in [t["root"]] + [self.normalize_message(cid, r) for r in replies[-20:]]:
                        if m["user_name"] and m["user_name"] not in people:
                            people.append(m["user_name"])
                    mentioned = bool(me) and any(f"<@{me}" in (m.get("text") or "") for m in local)
                    items.append({
                        "type": "thread",
                        "channel_id": cid,
                        "channel_name": conv["name"],
                        "thread_ts": t["thread_ts"],
                        "root": t["root"],
                        "reply_count": t["reply_count"],
                        "participants": people[:6],
                        "last": self.normalize_message(cid, replies[-1]) if replies else None,
                        "latest_ts": t["latest_reply"] or t["thread_ts"],
                        "latest_time": t["latest_time"] or t["root"]["time"],
                        "has_unreads": t["has_unreads"],
                        "mentions_me": mentioned or t["mentions_me"] or t["root"]["mentions_me"],
                    })
            elif conv["latest_ts"]:
                last = self.db.history(cid, limit=1)
                items.append({
                    "type": "dm",
                    "channel_id": cid,
                    "channel_name": conv["name"],
                    "kind": conv["kind"],
                    "thread_ts": None,
                    "last": self.normalize_message(cid, last[0]) if last else None,
                    "latest_ts": conv["latest_ts"],
                    "latest_time": conv["latest_time"],
                    "has_unreads": conv["has_unreads"],
                    "mentions_me": conv["mention_count"] > 0,
                })
        items.sort(key=lambda item: -float(item["latest_ts"]))
        return {"items": items}

    # -- 已读：只记在 momo 本地，从不改 Slack

    def mark_conversation(self, channel_id: str, ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(ts or ""):
            raise SlackInboxError("BAD_TS", "ts 格式不对", 400)
        return {"ok": True, "marked": self.db.mark_read(channel_id, ts)}

    def mark_thread(self, channel_id: str, thread_ts: str, ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(thread_ts or "") or not TS_RE.match(ts or ""):
            raise SlackInboxError("BAD_TS", "ts 格式不对", 400)
        return {"ok": True, "marked": self.db.mark_read(channel_id, ts, thread_ts)}

    def mark_all_read(self) -> Dict[str, Any]:
        """「全部标为已读」：动态里所有未读的 thread / 新帖 / 私信，以及有未读的频道，都推到最新。只记在 momo 本地。"""
        marked = 0
        for item in self.activity()["items"]:
            if not item["has_unreads"]:
                continue
            if item["type"] == "thread":
                marked += self.db.mark_read(item["channel_id"], item["latest_ts"], item["thread_ts"])
            else:
                marked += self.db.mark_read(item["channel_id"], item["latest_ts"])
        for conv in self.conversations():
            if conv["has_unreads"] and conv["latest_ts"]:
                marked += self.db.mark_read(conv["id"], conv["latest_ts"])
        return {"ok": True, "marked": marked}

    # -- 附件

    def _register_file(self, f: Dict[str, Any]) -> Optional[str]:
        """记下文件的下载地址（只认 slack.com 的），返回文件 ID。"""
        fid = f.get("id", "")
        url = f.get("url_private") or ""
        if not FILE_ID_RE.match(fid) or not _is_slack_file_url(url):
            return None
        with self._lock:
            self._files[fid] = {
                "url": url,
                "mimetype": f.get("mimetype") or "application/octet-stream",
                "name": f.get("name") or f.get("title") or fid,
            }
        return fid

    def _prefetch_images(self, messages: List[Dict[str, Any]]) -> None:
        """新消息里的图片放进后台下载队列：打开时直接从本地出，Slack 那边过期了也还在。"""
        for m in messages:
            for f in m.get("files") or []:
                if not str(f.get("mimetype") or "").startswith("image/") or int(f.get("size") or 0) > MAX_FILE_BYTES:
                    continue
                fid = self._register_file(f)
                if fid and not (self.cache_dir / "files" / fid).is_file():
                    self._prefetch_queue.put(fid)
        if not self._prefetch_queue.empty():
            with self._lock:
                if self._prefetch_thread is None or not self._prefetch_thread.is_alive():
                    self._prefetch_thread = threading.Thread(target=self._prefetch_loop, name="slack-prefetch", daemon=True)
                    self._prefetch_thread.start()

    def _prefetch_loop(self) -> None:
        while True:
            try:
                fid = self._prefetch_queue.get(timeout=30)
            except queue.Empty:
                return  # 空闲就退出，下次有图片再起
            try:
                self.file(fid)
            except SlackInboxError as exc:
                logger.info("预取 Slack 图片 %s 失败：%s", fid, exc.message)
            except Exception:  # noqa: BLE001 - 预取失败不影响页面，打开时会再试
                logger.warning("预取 Slack 图片 %s 出错", fid, exc_info=True)

    def prune_files(self, max_bytes: int = FILES_MAX_BYTES) -> int:
        """图片目录超过上限：按最后修改时间删最旧的，删到上限的 80%。返回删掉的个数。"""
        files_dir = self.cache_dir / "files"
        if not files_dir.is_dir():
            return 0
        entries = [(p.stat().st_mtime, p.stat().st_size, p) for p in files_dir.iterdir()
                   if p.is_file() and not p.name.endswith((".json", ".tmp"))]
        total = sum(size for _, size, _ in entries)
        if total <= max_bytes:
            return 0
        removed = 0
        for _, size, path in sorted(entries):
            if total <= max_bytes * 0.8:
                break
            path.unlink(missing_ok=True)
            path.with_name(path.name + ".json").unlink(missing_ok=True)
            total -= size
            removed += 1
        return removed

    # -- 后台同步

    def start_background_sync(self, interval: float = SYNC_INTERVAL_S) -> None:
        """进程里起一个后台线程，定时把所有会话的新消息拉进本地（只拉新的）。重复调用无副作用。"""
        with self._lock:
            if self._sync_thread is not None and self._sync_thread.is_alive():
                return
            self._sync_thread = threading.Thread(target=self._sync_loop, args=(interval,), name="slack-sync", daemon=True)
            self._sync_thread.start()

    def _sync_loop(self, interval: float) -> None:
        while True:
            delay = interval
            try:
                self.sync_all()
            except SlackInboxError as exc:
                # 凭证失效或被限流就放慢，等页面上重新填凭证
                delay = interval * (10 if exc.code in {"CREDENTIALS_EXPIRED", "CREDENTIALS_MISSING"} else 3)
                logger.info("Slack 后台同步暂停：%s", exc.message)
            except Exception:  # noqa: BLE001 - 后台线程不能死
                logger.warning("Slack 后台同步出错", exc_info=True)
            time.sleep(delay)

    def sync_all(self) -> Dict[str, int]:
        """一轮同步：每个会话按 client.counts 的最新 ts 判断，有新的才拉；有新回复的 thread 拉新回复。"""
        if self.store.load() is None:
            return {"conversations": 0, "new": 0}
        new = 0
        convs = self.conversations()
        for conv in convs:
            new += self.sync_conversation(conv["id"], conv["latest_ts"])
        for t in self.threads()["threads"]:
            if t["has_unreads"]:
                self.sync_thread(t["channel_id"], t["thread_ts"])
        self._last_sync = self._now()
        if self._now() - self._last_prune > 3600:
            self._last_prune = self._now()
            self.prune_files()
        return {"conversations": len(convs), "new": new}

    def file(self, file_id: str) -> Tuple[Path, str, str]:
        if not FILE_ID_RE.match(file_id or ""):
            raise SlackInboxError("BAD_FILE", "文件 ID 格式不对", 400)
        meta = self._files.get(file_id)
        files_dir = self.cache_dir / "files"
        meta_path = files_dir / f"{file_id}.json"
        data_path = files_dir / file_id
        if data_path.is_file() and meta_path.is_file():
            try:
                cached = json.loads(meta_path.read_text(encoding="utf-8"))
                return data_path, cached.get("mimetype", "application/octet-stream"), cached.get("name", file_id)
            except (OSError, ValueError):
                pass
        if not meta:
            raise SlackInboxError("FILE_UNKNOWN", "先打开包含这个文件的消息再下载", 404)
        body, content_type = self.client().download(meta["url"])
        files_dir.mkdir(parents=True, exist_ok=True)
        tmp = data_path.with_suffix(".tmp")
        tmp.write_bytes(body)
        os.replace(tmp, data_path)
        mimetype = meta["mimetype"] or content_type
        meta_path.write_text(json.dumps({"mimetype": mimetype, "name": meta["name"]}, ensure_ascii=False), encoding="utf-8")
        return data_path, mimetype, meta["name"]

    # -- 导出

    def export(self, channel_id: str, limit: int = 200) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        info = next(c for c in self.conversations() if c["id"] == channel_id)
        history: List[Dict[str, Any]] = []
        cursor = None
        while len(history) < limit:
            page = self.messages(channel_id, limit=min(200, limit - len(history)), cursor=cursor)
            history.extend(page["messages"])
            cursor = page["next_cursor"]
            if not cursor:
                break
        history.reverse()  # 导出按时间正序
        for msg in history:
            if msg["reply_count"] and msg["thread_ts"] == msg["ts"]:
                msg["replies"] = self.replies(channel_id, msg["ts"])["messages"][1:]
        return {"conversation": info, "exported_at": format_ts(str(self._now())), "messages": history}

    # -- AI 速览：收集未读（只读，不标已读）

    def unread_material(self) -> List[Dict[str, Any]]:
        """每个有未读的会话、每个有新回复的 thread：我之外的人在已读位置之后发的消息（时间正序）。"""
        sections: List[Dict[str, Any]] = []
        for conv in self.conversations():
            if not conv["has_unreads"] or not conv["last_read"]:
                continue
            msgs = [
                m for m in reversed(self._history_messages(conv["id"]))
                if float(m["ts"]) > float(conv["last_read"]) and not m["is_me"]
            ][-DIGEST_MAX_MESSAGES:]
            if msgs:
                sections.append({"kind": conv["kind"], "conversation": conv, "thread_ts": None,
                                 "last_read": conv["last_read"], "messages": msgs})
        names = {c["id"]: c for c in self.conversations()}
        for t in self.threads()["threads"]:
            if not t["has_unreads"] or t["channel_id"] not in names:
                continue
            msgs = [
                m for m in self.replies(t["channel_id"], t["thread_ts"])["messages"][1:]
                if float(m["ts"]) > float(t["last_read"] or 0) and not m["is_me"]
            ][-DIGEST_MAX_MESSAGES:]
            if msgs:
                sections.append({"kind": "thread", "conversation": names[t["channel_id"]], "thread_ts": t["thread_ts"],
                                 "root": t["root"], "last_read": t["last_read"], "messages": msgs})
        return sections

    def _history_messages(self, channel_id: str) -> List[Dict[str, Any]]:
        return [self.normalize_message(channel_id, m) for m in self._recent_raw(channel_id, 100)]

    # -- 搜索（search.messages，只读）

    def search(self, query: str, count: int = SEARCH_COUNT) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise SlackInboxError("BAD_QUERY", "搜索词不能为空", 400)
        data = self.client().call("search.messages", query=query[:200], count=max(1, min(count, 50)), sort="timestamp")
        found = data.get("messages") or {}
        visible = {c["id"]: c for c in self.conversations()}
        results = []
        for match in found.get("matches") or []:
            ch = match.get("channel") or {}
            cid = ch.get("id") or ""
            if not CONVERSATION_ID_RE.match(cid):
                continue
            permalink = match.get("permalink") or ""
            thread_ts = (parse_qs(urlparse(permalink).query).get("thread_ts") or [None])[0]
            msg = self.normalize_message(cid, {**match, "thread_ts": thread_ts or match.get("thread_ts")})
            if permalink.startswith("https://"):
                msg["permalink"] = permalink
            conv = visible.get(cid)
            results.append({
                "channel_id": cid,
                "channel_name": conv["name"] if conv else (ch.get("name") or cid),
                "kind": conv["kind"] if conv else ("im" if ch.get("is_im") else "mpim" if ch.get("is_mpim") else "channel"),
                "visible": bool(conv),
                "thread_ts": thread_ts if thread_ts and thread_ts != msg["ts"] else None,
                "message": msg,
            })
        return {"query": query, "total": int(found.get("total") or 0), "results": results}

    # -- 交给 AI agent 的上下文

    def agent_context(self, channel_id: str, thread_ts: Optional[str] = None, limit: int = AGENT_DM_MESSAGES) -> Dict[str, Any]:
        """thread 给全部消息，会话（私信）给最近 limit 条；带上「谁是我」，供 skill agent 读取。"""
        self._require_conversation(channel_id)
        info = next(c for c in self.conversations() if c["id"] == channel_id)
        if thread_ts:
            if not TS_RE.match(thread_ts):
                raise SlackInboxError("BAD_TS", "thread ts 格式不对", 400)
            messages = self.replies(channel_id, thread_ts)["messages"]
            source = f"slack:{channel_id}:{thread_ts}"
        else:
            messages = list(reversed(self.messages(channel_id, limit=limit)["messages"]))
            source = f"slack:{channel_id}"
        history = [
            {"role": "me" if m["is_me"] else "them", "content": m["text"]}
            for m in messages if m["text"].strip()
        ]
        title_msg = messages[0] if thread_ts and messages else None
        if title_msg:
            title = title_msg["text"].strip().splitlines()[0][:50] if title_msg["text"].strip() else "thread"
        else:
            title = info["name"]
        return {
            "source": source,
            "kind": "thread" if thread_ts else info["kind"],
            "title": title,
            "conversation": info,
            "latest_ts": messages[-1]["ts"] if messages else None,
            "markdown": agent_context_markdown(info, messages, self.auth().get("user", ""), is_thread=bool(thread_ts)),
            "history": history,
        }

    # -- Muse 自动化：since 之后谁 @ 了我（只读本地副本，不标已读）

    def my_groups(self) -> List[str]:
        try:
            return list(self._boot().get("my_groups") or [])
        except SlackInboxError:
            return []

    def mentions_since(self, since: float, group_ids: Iterable[str] = (), limit: int = 200) -> List[Dict[str, Any]]:
        """since 之后需要我看的消息：私信里别人发的每一条记 dm；其余会话按 @ 分 direct / group / channel。

        group_ids：手配的用户组；再加上 client.userBoot 里自动识别到的我所在的组。旧→新，每条只出现一次。
        """
        me = self.auth().get("user_id", "")
        groups = sorted({g for g in group_ids if g} | set(self.my_groups()))
        needles = [f"<@{me}"] if me else []
        needles += [f"<!subteam^{g}" for g in groups] + list(BROADCAST_MENTIONS)
        dm_ids = self._dm_ids()
        found: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for raw in self.db.messages_in(dm_ids, since, limit=limit):
            if _is_from_someone(raw, me):
                found[(raw["channel_id"], str(raw.get("ts") or ""))] = self._mention_record(raw, "dm")
        searched = self._search_mentions(since, me) if me else []
        for raw in self.db.messages_containing(since, needles, limit=limit) + searched:
            key = (raw["channel_id"], str(raw.get("ts") or ""))
            if key in found or not _is_from_someone(raw, me):
                continue
            if raw["channel_id"] in dm_ids:
                found[key] = self._mention_record(raw, "dm")
                continue
            kind = mention_type(raw.get("text") or "", me, groups)
            if kind is None:  # 只在附件 / 卡片里出现，不算
                continue
            found[key] = self._mention_record(raw, kind)
        return sorted(found.values(), key=lambda m: float(m["message_ts"]))[-limit:]

    def _search_mentions(self, since: float, me: str) -> List[Dict[str, Any]]:
        """兜底：本地副本只同步我参与的 thread，没参与、Slack 也没自动订阅的 thread 里 @我 的回复会漏。
        用 search.messages（只读）搜 <@我>，本地还没有的存进本地副本并返回；已经在本地的说明报过或会从本地查到，跳过。

        搜索索引有延迟，往回多看 MENTION_SEARCH_LOOKBACK_S；靠「本地有没有」去重，所以同一条只报一次。失败只记日志。
        """
        start = max(0.0, since - MENTION_SEARCH_LOOKBACK_S)
        # after: 按天、不含当天，再往前一天兜住时区差；精确过滤在下面按 ts 做
        after = datetime.fromtimestamp(start, timezone.utc).date().isoformat()
        query = f"<@{me}> after:{(datetime.fromisoformat(after) - timedelta(days=1)).date().isoformat()}"
        fresh: List[Dict[str, Any]] = []
        try:
            for page in range(1, MENTION_SEARCH_PAGES + 1):
                data = self.client().call("search.messages", query=query, count=50, sort="timestamp",
                                          sort_dir="desc", page=page)
                matches = (data.get("messages") or {}).get("matches") or []
                for match in matches:
                    cid = (match.get("channel") or {}).get("id") or ""
                    ts = str(match.get("ts") or "")
                    if not CONVERSATION_ID_RE.match(cid) or not TS_RE.match(ts) or float(ts) <= start:
                        continue
                    if self.db.message(cid, ts) is not None:
                        continue
                    permalink = match.get("permalink") or ""
                    thread_ts = (parse_qs(urlparse(permalink).query).get("thread_ts") or [None])[0]
                    raw = {k: match[k] for k in ("ts", "user", "username", "text", "attachments", "files", "bot_profile")
                           if k in match}
                    if thread_ts and thread_ts != ts:
                        raw["thread_ts"] = thread_ts
                    self.db.upsert(cid, [raw], in_history=not raw.get("thread_ts"))
                    fresh.append({**raw, "channel_id": cid})
                oldest = min((float(m.get("ts") or 0) for m in matches), default=0.0)
                paging = (data.get("messages") or {}).get("paging") or {}
                if not matches or oldest <= start or page >= int(paging.get("pages") or 1):
                    break
        except SlackInboxError as exc:
            logger.warning("@我 兜底搜索失败，只用本地副本：%s", exc.message)
        return fresh

    def _dm_ids(self) -> set:
        """展示范围内的私信和群聊私信（已去掉 Slackbot、bot 和自己）。"""
        try:
            return {c["id"] for c in self.conversations() if c["kind"] in {"im", "mpim"}}
        except SlackInboxError:
            return set()

    def _mention_record(self, raw: Dict[str, Any], kind: str) -> Dict[str, Any]:
        cid = raw["channel_id"]
        ts = str(raw.get("ts") or "")
        thread_ts = raw.get("thread_ts")
        user_id = raw.get("user") or ""
        return {
            "conversation_id": cid,
            "conversation_name": self._mention_conversation_name(cid),
            "message_ts": ts,
            "thread_ts": thread_ts if thread_ts and thread_ts != ts else None,
            "time": datetime.fromtimestamp(float(ts), timezone.utc).isoformat().replace("+00:00", "Z"),
            "from_user": self.user_name(user_id) if user_id
            else (raw.get("bot_profile") or {}).get("name") or raw.get("username") or "Bot",
            "text": segments_to_plain(parse_slack_text(raw.get("text") or "", self.user_name)),
            "mention_type": kind,
            "permalink": self._permalink(cid, ts, thread_ts),
        }

    def _mention_conversation_name(self, channel_id: str) -> str:
        try:
            info = self._conversation_info(channel_id)
        except SlackInboxError:
            return channel_id
        if info["kind"] == "im":
            return self.user_name(info["user"])
        if info["kind"] == "mpim":
            return mpim_label(info["name"], self.auth().get("user", ""))
        return info["name"] or channel_id

    def translation_source(self, channel_id: str, ts: str, thread_ts: Optional[str] = None,
                           with_thread: bool = False) -> Dict[str, Any]:
        """Muse 的 translate-slack：一条消息（或它所在的整个 thread）的原文，带链接卡片里的帖子。只读。"""
        if not CONVERSATION_ID_RE.match(channel_id or ""):
            raise SlackInboxError("BAD_CONVERSATION", "会话 ID 格式不对", 400)
        if not TS_RE.match(ts or "") or (thread_ts and not TS_RE.match(thread_ts)):
            raise SlackInboxError("BAD_TS", "消息 ts 格式不对", 400)
        raw = self.db.message(channel_id, ts)
        if raw is None:
            self.sync_conversation(channel_id, self._latest_hint(channel_id))
            if thread_ts:
                self.sync_thread(channel_id, thread_ts)
            raw = self.db.message(channel_id, ts)
        if raw is None:
            raise SlackInboxError("MESSAGE_NOT_FOUND", "本地副本里找不到这条消息（thread 里的回复要带 thread_ts）", 404)
        root = thread_ts or raw.get("thread_ts") or ts
        if with_thread:
            self.sync_thread(channel_id, root)
            raws = self.db.thread(channel_id, root)
        else:
            raws = [raw]
        messages = [self.normalize_message(channel_id, m) for m in raws]
        parts = []
        for raw_msg, msg in zip(raws, messages):
            body = msg["text"].strip()
            # 卡片正文用 Slack 原始文本解析（normalize_message 里的已经反转义过，再解析会把字面的 < > 当标记）
            for card, raw_card in zip(msg["attachments"], raw_msg.get("attachments") or []):
                text = segments_to_plain(parse_slack_text(raw_card.get("text") or "", self.user_name)).strip()
                card_text = "\n".join(t for t in (card["title"].strip(), text) if t)
                if card_text:
                    body += ("\n\n" if body else "") + f"[{card['service_name'] or '链接卡片'}] {card_text}"
            if body:
                parts.append(f"{msg['user_name']}: {body}" if with_thread else body)
        return {
            "source_text": "\n\n".join(parts),
            "messages": len(messages),
            "permalink": self._permalink(channel_id, root if with_thread else ts,
                                         None if with_thread else raw.get("thread_ts")),
        }


def _my_subteams(boot: Dict[str, Any]) -> List[str]:
    """client.userBoot 里「我所在的用户组」：subteams.self（企业版 usergroups.* 被禁用，只能从这里拿）。没有就是空。"""
    subteams = boot.get("subteams")
    mine = subteams.get("self") if isinstance(subteams, dict) else None
    ids = [(item.get("id") if isinstance(item, dict) else item) for item in (mine or [])]
    return [i for i in ids if isinstance(i, str) and re.fullmatch(r"S[A-Z0-9]{6,20}", i)]


# 系统消息（入群、改名、置顶……）不算别人发给我的
_SILENT_SUBTYPES = {"channel_join", "channel_leave", "group_join", "group_leave", "channel_topic", "channel_purpose",
                    "channel_name", "group_topic", "group_purpose", "group_name", "pinned_item", "unpinned_item",
                    "bot_add", "bot_remove", "tombstone"}


def _is_from_someone(raw: Dict[str, Any], me: str) -> bool:
    if raw.get("subtype") in _SILENT_SUBTYPES:
        return False
    return not (me and raw.get("user") == me)


def mention_type(text: str, me: str, group_ids: Iterable[str] = ()) -> Optional[str]:
    """一条消息对我来说算哪类 @：direct（点名我）> group（我所在的用户组）> channel（@channel/@here）。"""
    if me and f"<@{me}" in text:
        return "direct"
    if any(f"<!subteam^{g}" in text for g in group_ids if g):
        return "group"
    if any(t in text for t in BROADCAST_MENTIONS):
        return "channel"
    return None


def agent_context_markdown(conv: Dict[str, Any], messages: List[Dict[str, Any]], me: str, is_thread: bool) -> str:
    """给 agent 读的 Markdown：每条消息标作者（我的标「我」）、时间、原文链接；链接卡片和附件完整列出。"""
    where = ("#" if conv["kind"] in {"channel", "private"} else "私信 · ") + conv["name"]
    lines = [
        f"# Slack {'thread' if is_thread else '会话'} · {where}",
        "",
        f"- 我是：{me or '（未知）'}，下面作者标「（我）」的是我发的",
        f"- 消息数：{len(messages)}，按时间正序" + ("；第一条是 thread 根消息" if is_thread else ""),
        "",
    ]
    for i, msg in enumerate(messages, 1):
        who = msg["user_name"] + ("（我）" if msg["is_me"] else "")
        lines.append(f"## {i}. {who} · {msg['time']}" + (" · 已编辑" if msg["edited"] else ""))
        lines.append(f"原文链接：{msg['permalink']}")
        lines.append("")
        lines.extend((msg["text"] or "").splitlines() or ["（无文字）"])
        for a in msg["attachments"]:
            if a["title"] or a["text"]:
                lines.append("")
                lines.append(f"[链接卡片{' · ' + a['service_name'] if a['service_name'] else ''}] {a['title']} {a['title_link']}".rstrip())
                lines.extend(f"> {line}" for line in (a["text"] or "").splitlines())
        for f in msg["files"]:
            lines.append(f"[{'图片' if f['is_image'] else '附件'}] {f['name']}")
        lines.append("")
    return "\n".join(lines)


def export_to_markdown(data: Dict[str, Any]) -> str:
    conv = data["conversation"]
    title = ("#" if conv["kind"] in {"channel", "private"} else "") + conv["name"]
    lines = [f"# Slack · {title}", "", f"导出时间：{data['exported_at']}", ""]

    def render(msg: Dict[str, Any], indent: str = "") -> None:
        lines.append(f"{indent}**{msg['user_name']}** · {msg['time']}")
        for line in (msg["text"] or "").splitlines() or [""]:
            lines.append(f"{indent}{line}")
        for f in msg["files"]:
            lines.append(f"{indent}[附件] {f['name']}")
        for a in msg["attachments"]:
            if a["title"]:
                lines.append(f"{indent}[链接卡片] {a['title']} {a['title_link']}".rstrip())
        lines.append("")

    for msg in data["messages"]:
        render(msg)
        for reply in msg.get("replies", []):
            render(reply, indent="> ")
    return "\n".join(lines)
