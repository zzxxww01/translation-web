"""skill-runner 配置。全部来自环境变量，服务器上写在 ~/.config/skill-runner/env（权限 600）。"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SKILLS = ("four-step-translate", "video-bilingual-subber", "podcast-cn-dubber")

# 沙箱里的 Bash 只能连这些域名：Gemini（字幕转写/翻译）、DashScope 与 OSS（播客 ASR/TTS）、
# YouTube（yt-dlp 下载）。新 skill 要连别的域名时，用 SKILL_RUNNER_ALLOWED_DOMAINS 整体覆盖。
DEFAULT_ALLOWED_DOMAINS = (
    "generativelanguage.googleapis.com",
    "dashscope.aliyuncs.com",
    "*.aliyuncs.com",
    "youtube.com",
    "*.youtube.com",
    "youtu.be",
    "*.googlevideo.com",
    "*.ytimg.com",
)

# 这两个变量一旦存在，Claude Code 就改走 API 计费或第三方网关，不再用订阅额度。
BILLING_OVERRIDE_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")


def _split(value: str | None, sep: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(sep) if item.strip())


def _flag(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Config:
    home: Path
    password: str
    session_secret: bytes
    skills: tuple[str, ...] = DEFAULT_SKILLS
    skills_dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "skills")
    max_active: int = 2
    idle_timeout_s: float = 600.0
    max_upload_bytes: int = 1024 * 1024 * 1024
    sandbox: bool = True
    extra_write: tuple[Path, ...] = ()
    allowed_domains: tuple[str, ...] = DEFAULT_ALLOWED_DOMAINS
    unsandboxed_commands: tuple[str, ...] = ()
    model: str | None = None
    cookie_secure: bool = True
    host: str = "127.0.0.1"
    port: int = 18090

    @property
    def runs_dir(self) -> Path:
        return self.home / "runs"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = dict(os.environ if env is None else env)
        home = Path(env.get("SKILL_RUNNER_HOME") or Path.home() / "skill-runner").expanduser()
        password = env.get("SKILL_RUNNER_PASSWORD", "")
        # 默认从口令派生签名密钥：改口令即让所有旧 cookie 失效，不用另外维护一个密钥。
        secret_seed = env.get("SKILL_RUNNER_SECRET") or f"skill-runner-session:{password}"
        skills_dir = env.get("SKILL_RUNNER_SKILLS_DIR")
        return cls(
            home=home,
            password=password,
            session_secret=hashlib.sha256(secret_seed.encode("utf-8")).digest(),
            skills=_split(env.get("SKILL_RUNNER_SKILLS"), ",") or DEFAULT_SKILLS,
            skills_dir=Path(skills_dir).expanduser() if skills_dir else Path.home() / ".claude" / "skills",
            max_active=int(env.get("SKILL_RUNNER_MAX_ACTIVE") or 2),
            idle_timeout_s=float(env.get("SKILL_RUNNER_IDLE_TIMEOUT_S") or 600),
            max_upload_bytes=int(env.get("SKILL_RUNNER_MAX_UPLOAD_MB") or 1024) * 1024 * 1024,
            sandbox=_flag(env.get("SKILL_RUNNER_SANDBOX"), True),
            extra_write=tuple(Path(p).expanduser() for p in _split(env.get("SKILL_RUNNER_EXTRA_WRITE"), os.pathsep)),
            allowed_domains=_split(env.get("SKILL_RUNNER_ALLOWED_DOMAINS"), ",") or DEFAULT_ALLOWED_DOMAINS,
            # Bash 规则里本身带空格和逗号，所以用分号分隔
            unsandboxed_commands=_split(env.get("SKILL_RUNNER_UNSANDBOXED_COMMANDS"), ";"),
            model=env.get("SKILL_RUNNER_MODEL") or None,
            cookie_secure=_flag(env.get("SKILL_RUNNER_COOKIE_SECURE"), True),
            host=env.get("SKILL_RUNNER_HOST") or "127.0.0.1",
            port=int(env.get("SKILL_RUNNER_PORT") or 18090),
        )
