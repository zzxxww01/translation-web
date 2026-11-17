"""
Slack 收件箱。

用个人网页会话凭证（xoxc token + d cookie）读取「我」所在的频道和私信，
给前端 Slack 页展示。企业版工作区禁用了 conversations.list / users.conversations，
会话清单从网页端自己用的 client.userBoot（侧栏）+ client.counts（未读数）拿。

只读是硬约束：所有 API 调用都过白名单，白名单外的方法直接抛错。唯一的例外是
MARK_METHODS——把「我」的已读位置往前推，别人看不到，不发送、不修改任何消息。
凭证只发给 slack.com。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://slack.com/api"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 只读白名单：新增方法前先确认它不会写入、发送或改变已读状态
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

# 只改「我」自己的已读位置（和在 Slack 里看过一样）；不发送、不改消息，别人不可见
MARK_METHODS = frozenset({
    "conversations.mark",
    "subscriptions.thread.mark",
})

# 私信只展示最近有往来的（天数可由 settings.slack_dm_recent_days 覆盖）
DM_RECENT_DAYS = 30
# Slackbot / Slack 官方通知账号不算往来
HIDDEN_DM_USERS = frozenset({"USLACKBOT", "USLACK"})

COUNTS_TTL_S = 30
BOOT_TTL_S = 300
HISTORY_TTL_S = 30
# 侧栏展开频道时列出最近多少天有动静的 thread
THREAD_RECENT_DAYS = 7
# 私信交给回复 agent 时带最近多少条
AGENT_DM_MESSAGES = 30
# AI 速览：每个会话 / thread 最多带多少条未读
DIGEST_MAX_MESSAGES = 40
SEARCH_COUNT = 30
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
        if method not in ALLOWED_METHODS and method not in MARK_METHODS:
            raise SlackInboxError("METHOD_NOT_ALLOWED", f"Slack 方法 {method} 不在只读白名单里", 500)
        try:
            if method in MARK_METHODS:
                resp = self._http.post(f"{API_BASE}/{method}", data=params, headers=self._headers)
            else:
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
                push_text(_unescape(match.group(0)))
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
            return {"configured": True, "ok": True, **self.auth()}
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
        boot = {"channels": data.get("channels") or [], "ims": data.get("ims") or [], "is_open": data.get("is_open")}
        self._cache.put("boot", boot)
        return boot

    def thread_badge(self) -> Dict[str, Any]:
        threads = self._counts().get("threads") or {}
        return {"has_unreads": bool(threads.get("has_unreads")), "mention_count": int(threads.get("mention_count") or 0)}

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

        thread_counts = counts.get("threads") or {}
        thread_unreads = thread_counts.get("unread_count_by_channel") or {}
        thread_mentions = thread_counts.get("mention_count_by_channel") or {}
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
            last_read = str(item.get("last_read") or "")
            entry = {
                "id": cid,
                "kind": info["kind"],
                "name": info["name"],
                "latest_ts": latest if latest_f else None,
                "latest_time": format_ts(latest) if latest_f else "",
                "last_read": last_read if TS_RE.match(last_read) else None,
                "has_unreads": bool(item.get("has_unreads")),
                "mention_count": int(item.get("mention_count") or 0),
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
            fid = f.get("id", "")
            url = f.get("url_private") or ""
            if not FILE_ID_RE.match(fid) or not _is_slack_file_url(url):
                continue
            mimetype = f.get("mimetype") or "application/octet-stream"
            name = f.get("name") or f.get("title") or fid
            with self._lock:
                self._files[fid] = {"url": url, "mimetype": mimetype, "name": name}
            files.append({
                "id": fid,
                "name": name,
                "mimetype": mimetype,
                "is_image": mimetype.startswith("image/"),
                "url": f"/api/slack-inbox/files/{fid}",
            })
        attachments = []
        for a in msg.get("attachments", []) or []:
            attachments.append({
                "service_name": a.get("service_name") or "",
                "title": a.get("title") or a.get("fallback") or "",
                "title_link": a.get("title_link") or a.get("from_url") or "",
                "text": _unescape(a.get("text") or ""),
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

    def _history(self, channel_id: str, limit: int, cursor: Optional[str] = None) -> Dict[str, Any]:
        key = ("history", channel_id, limit, cursor or "")
        data = self._cache.get(key, HISTORY_TTL_S)
        if data is None:
            params: Dict[str, Any] = {"channel": channel_id, "limit": limit}
            if cursor:
                params["cursor"] = cursor
            data = self.client().call("conversations.history", **params)
            self._cache.put(key, data)
        return data

    def messages(self, channel_id: str, limit: int = 50, cursor: Optional[str] = None) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        limit = max(1, min(int(limit), 200))
        data = self._history(channel_id, limit, cursor)
        msgs = [self.normalize_message(channel_id, m) for m in data.get("messages", [])]
        next_cursor = (data.get("response_metadata") or {}).get("next_cursor") or None
        return {"messages": msgs, "next_cursor": next_cursor if data.get("has_more") else None}

    def replies(self, channel_id: str, thread_ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(thread_ts or ""):
            raise SlackInboxError("BAD_TS", "thread ts 格式不对", 400)
        key = ("replies", channel_id, thread_ts)
        collected = self._cache.get(key, HISTORY_TTL_S)
        if collected is None:
            collected = []
            cursor = None
            for _ in range(5):  # 最多 1000 条，够任何一个帖子 thread
                params: Dict[str, Any] = {"channel": channel_id, "ts": thread_ts, "limit": 200}
                if cursor:
                    params["cursor"] = cursor
                data = self.client().call("conversations.replies", **params)
                collected.extend(data.get("messages", []))
                cursor = (data.get("response_metadata") or {}).get("next_cursor")
                if not data.get("has_more") or not cursor:
                    break
            self._cache.put(key, collected)
        followed = self._followed_threads().get((channel_id, thread_ts))
        return {
            "messages": [self.normalize_message(channel_id, m) for m in collected],
            "last_read": (followed or {}).get("last_read") or None,
        }

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
        last_read = (followed or {}).get("last_read")
        unread = bool(followed) and bool(latest) and float(latest) > float(last_read or 0)
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
        for m in self._history(channel_id, 100).get("messages", []):
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

    # -- 已读（只改我自己的已读位置）

    def mark_conversation(self, channel_id: str, ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(ts or ""):
            raise SlackInboxError("BAD_TS", "ts 格式不对", 400)
        current = next((c for c in self.conversations() if c["id"] == channel_id), {})
        if current.get("last_read") and float(ts) <= float(current["last_read"]):
            return {"ok": True, "marked": False}  # 不往回退已读位置
        self.client().call("conversations.mark", channel=channel_id, ts=ts)
        self._cache.pop("counts")
        return {"ok": True, "marked": True}

    def mark_thread(self, channel_id: str, thread_ts: str, ts: str) -> Dict[str, Any]:
        self._require_conversation(channel_id)
        if not TS_RE.match(thread_ts or "") or not TS_RE.match(ts or ""):
            raise SlackInboxError("BAD_TS", "ts 格式不对", 400)
        followed = self._followed_threads().get((channel_id, thread_ts))
        if not followed:
            return {"ok": True, "marked": False}  # 没参与的 thread Slack 不记已读
        if followed["last_read"] and float(ts) <= float(followed["last_read"]):
            return {"ok": True, "marked": False}
        self.client().call("subscriptions.thread.mark", channel=channel_id, thread_ts=thread_ts, ts=ts, read="1")
        self._cache.pop("thread_view")
        self._cache.pop("counts")
        return {"ok": True, "marked": True}

    # -- 附件

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
        return [self.normalize_message(channel_id, m) for m in self._history(channel_id, 100).get("messages", [])]

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
