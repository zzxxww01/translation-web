"""Muse 用 Claude / Codex / Gemini(agy) 精翻文章：在服务器上做网页文章页「交给 Agent 翻」的那一套。

网页是浏览器带着登录 cookie 调 skill-runner（Claude 页）；后端没有浏览器，就读 skill-runner 的 env 文件，
只取口令（或 SKILL_RUNNER_SECRET），按 skill_runner.auth 同样的算法签一个 cookie。口令不落盘、不打日志。

流程和 web/frontend/src/features/articles/lib/claude.ts 一致：
上传 source.html 跑 four-step-translate → 这一轮结束、不在等确认 → 取同一目录的 zh.md / en.md →
article_primary.import_agent_version 导成该 Agent 的译本（{主id}--{agent}）。
轮询在后台（agent_translate_loop），不依赖有人开着网页；记录存在 data/automation_agent_runs.json，重启后接着轮询。
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

from skill_runner.auth import COOKIE_NAME, PREVIOUS_COOKIE_NAME, issue_token
from src.core.file_utils import read_json, write_json_atomic

logger = logging.getLogger(__name__)

AGENTS = ("claude", "codex", "antigravity")
SKILL = "four-step-translate"
# 和网页 lib/claude.ts 的 CLAUDE_MESSAGE、skills/api.ts 的 AUTO_REPLY_MINUTES 一致
MESSAGE = "精翻附件里的这篇文章。输出目录放在当前目录下的 output/ 里（不用 SKILL.md 配置里的 output_root）。"
AUTO_REPLY_MINUTES = 10
WORKING = {"running", "waiting", "queued"}

_direct = build_opener(ProxyHandler({}))  # 本机直连，不走 .env 里给外网用的代理


class AgentRunError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message, self.status_code = message, status_code


def read_skill_runner_secret(env_file: Path) -> bytes:
    """和 skill_runner.config.Config.from_env 一样从口令派生签名密钥。env 文件里有非 UTF-8 字节，按行容错。"""
    values: Dict[str, str] = {}
    try:
        raw = env_file.read_bytes()
    except OSError as error:
        raise AgentRunError(f"读不到 Claude 页的配置：{error.strerror}", 503) from error
    for line in raw.splitlines():
        text = line.decode("utf-8", "surrogateescape").strip()
        if text.startswith("export "):
            text = text[7:].lstrip()
        key, sep, value = text.partition("=")
        if sep and key.strip() in ("SKILL_RUNNER_SECRET", "SKILL_RUNNER_PASSWORD"):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            values[key.strip()] = value
    password = values.get("SKILL_RUNNER_PASSWORD", "")
    seed = values.get("SKILL_RUNNER_SECRET") or f"skill-runner-session:{password}"
    if not values.get("SKILL_RUNNER_SECRET") and not password:
        raise AgentRunError("Claude 页没配口令", 503)
    return hashlib.sha256(seed.encode("utf-8", "surrogateescape")).digest()


class SkillRunnerClient:
    def __init__(self, base_url: str, env_file: Path):
        self.base_url = base_url.rstrip("/")
        self.env_file = env_file

    def _request(self, method: str, path: str, *, data: Optional[bytes] = None,
                 content_type: Optional[str] = None, timeout: float = 30) -> bytes:
        cookie = issue_token(read_skill_runner_secret(self.env_file))
        # 两个名字都带：skill-runner 重启前只认改名前的 cookie，重启后认新的（同一个签名，哪个都有效）
        headers = {"Cookie": f"{COOKIE_NAME}={cookie}; {PREVIOUS_COOKIE_NAME}={cookie}"}
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with _direct.open(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail")
            except (ValueError, OSError, AttributeError):
                detail = None
            raise AgentRunError(f"Claude 页返回 {error.code}：{detail or error.reason}",
                                404 if error.code == 404 else 502) from error
        except (URLError, TimeoutError, ConnectionError) as error:
            raise AgentRunError(f"连不上 Claude 页：{getattr(error, 'reason', error)}", 503) from error

    def _json(self, method: str, path: str, **kwargs) -> Any:
        return json.loads(self._request(method, path, **kwargs).decode("utf-8"))

    def start(self, *, html: bytes, filename: str, harness: str, title: str) -> Dict[str, Any]:
        boundary = f"----translation{uuid.uuid4().hex}"
        fields = {"skill": SKILL, "harness": harness, "message": MESSAGE,
                  "auto_reply_minutes": str(AUTO_REPLY_MINUTES), "title": title[:200]}
        parts: List[bytes] = []
        for name, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{filename}"\r\n'
                      "Content-Type: text/html\r\n\r\n").encode() + html + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self._json("POST", "/runs", data=b"".join(parts),
                          content_type=f"multipart/form-data; boundary={boundary}", timeout=120)

    def run(self, run_id: str) -> Dict[str, Any]:
        return self._json("GET", f"/runs/{quote(run_id, safe='')}")

    def files(self, run_id: str) -> List[Dict[str, Any]]:
        return self._json("GET", f"/runs/{quote(run_id, safe='')}/files")

    def read(self, run_id: str, path: str) -> str:
        return self._request("GET", f"/runs/{quote(run_id, safe='')}/files/{quote(path)}", timeout=60).decode("utf-8")

    def me(self) -> Dict[str, Any]:
        return self._json("GET", "/me")


def find_outputs(files: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """最新的 zh.md 和同一目录的 en.md（同 lib/claude.ts findClaudeOutputs）。"""
    zh_files = sorted((f for f in files if f["path"] == "zh.md" or f["path"].endswith("/zh.md")),
                      key=lambda f: f.get("mtime", 0), reverse=True)
    paths = {f["path"] for f in files}
    for zh in zh_files:
        en = zh["path"][: -len("zh.md")] + "en.md"
        if en in paths:
            return {"zh": zh["path"], "en": en}
    return None


class AgentRunStore:
    """{project_id: {agent: {run_id, status: running|done|failed, started_at, error, variant_id, model}}}"""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def all(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        try:
            data = read_json(self.path) if self.path.exists() else {}
        except (OSError, ValueError):
            data = {}
        return data if isinstance(data, dict) else {}

    def get(self, project_id: str) -> Dict[str, Dict[str, Any]]:
        return self.all().get(project_id) or {}

    def update(self, project_id: str, agent: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            data = self.all()
            record = {**(data.get(project_id, {}).get(agent) or {}), **fields, "updated_at": time.time()}
            data.setdefault(project_id, {})[agent] = record
            self.path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(self.path, data)
            return record

    def running(self) -> List[tuple]:
        return [(pid, agent, rec) for pid, agents in self.all().items()
                for agent, rec in agents.items() if rec.get("status") == "running"]
