"""Authenticated routes delegate fixed, verified runtime maintenance to this service.

No request controls an executable, package, URL, or target version. Runner owns the
admission gate; it must reserve synchronously before the background task starts.
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import tempfile
import time
from urllib.request import urlopen

from .runner import Busy
from .runtime_paths import claude_cli_path, native_claude_path

PACKAGES = {"claude": "@anthropic-ai%2fclaude-code", "codex": "@openai%2fcodex"}
# Official native manifest endpoint from https://antigravity.google/cli/install.sh.
ANTIGRAVITY_RELEASES = "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app"
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


def _valid_version(value: str) -> str:
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError("官方 registry 未返回有效的稳定版本号")
    return value


def _latest_version(harness: str) -> str:
    if harness == "antigravity":
        system = {"Linux": "linux", "Darwin": "darwin", "Windows": "windows"}.get(platform.system())
        arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
        if not system or not arch:
            raise ValueError("当前平台无法查询 Gemini（agy CLI）官方版本")
        suffix = "_musl" if system == "linux" and platform.libc_ver()[0] == "musl" else ""
        url = f"{ANTIGRAVITY_RELEASES}/manifests/{system}_{arch}{suffix}.json"
    else:
        url = f"https://registry.npmjs.org/{PACKAGES[harness]}/latest"
    with urlopen(url, timeout=10) as response:
        data = response.read(262145)
    if len(data) > 262144:
        raise ValueError("版本信息超出大小限制")
    return _valid_version(json.loads(data)["version"])


async def _command(argv: list[str], timeout: float = 15) -> str:
    # A file prevents installer logs from filling memory or blocking a PIPE.
    with tempfile.TemporaryFile() as output:
        process = await asyncio.create_subprocess_exec(
            *argv, stdout=output, stderr=asyncio.subprocess.STDOUT,
            start_new_session=os.name != "nt",
        )
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except (TimeoutError, asyncio.CancelledError) as exc:
            try:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise TimeoutError(f"命令超时（{timeout:g} 秒）") from exc
        output.seek(0, os.SEEK_END)
        output.seek(max(0, output.tell() - 4096))
        text = output.read().decode("utf-8", errors="replace").strip()
    if process.returncode:
        raise RuntimeError(f"命令失败（退出码 {process.returncode}）：{text}")
    return text


class RuntimeUpdates:
    def __init__(self, config, runner):
        self.config, self.runner = config, runner
        self._task: asyncio.Task | None = None
        self._active = self._checking = False
        self._checked_at = None
        self._runtimes = {
            harness: {
                "harness": harness, "label": label, "current": None, "latest": None,
                "update_available": False, "can_update": False, "reason": None,
                "error": None, "status": "unchecked", "message": None, "updated_at": None,
            }
            for harness, label in (("claude", "Claude Code"), ("codex", "Codex"), ("antigravity", "Gemini"))
        }

    @property
    def active(self) -> bool:
        return self._active

    def snapshot(self) -> dict:
        return copy.deepcopy({
            "active": self.active, "checking": self._checking,
            "checked_at": self._checked_at, "runtimes": list(self._runtimes.values()),
        })

    def _executable(self, harness: str) -> list[str]:
        if harness == "antigravity":
            binary = getattr(self.config, "antigravity_bin", "agy")
            if not binary:
                raise ValueError("未配置 Gemini（agy CLI）可执行程序")
            return [str(Path(binary).expanduser())]
        if harness == "codex":
            argv = shlex.split(self.config.codex_bin)
            if not argv:
                raise ValueError("未配置 Codex 可执行程序")
            return argv
        path = claude_cli_path(self.config)
        if not path:
            raise ValueError("未找到 Claude Code；请先在服务器安装 Claude Code 或 claude-agent-sdk")
        return [path]

    async def _current(self, harness: str) -> str:
        output = await _command(self._executable(harness) + ["--version"])
        match = re.search(r"(?<![\w.])([0-9]+\.[0-9]+\.[0-9]+)(?![\w.+-])", output)
        if not match:
            raise ValueError("无法识别当前可执行程序的版本号")
        return match.group(1)

    async def _install_command(self, harness: str, target: str) -> list[str]:
        _valid_version(target)
        if harness == "antigravity":
            raise ValueError("Gemini（agy CLI）使用官方自动更新；此处仅检查版本。")
        argv = self._executable(harness)
        if harness == "claude":
            explicit = getattr(self.config, "claude_bin", None)
            if explicit and Path(explicit).expanduser().absolute() != native_claude_path().absolute():
                raise ValueError("Claude 使用自定义路径；请手动更新该程序，或移除 SKILL_RUNNER_CLAUDE_BIN 以使用原生安装")
            return argv + ["install", target]
        npm = shutil.which("npm")
        if not npm or len(argv) != 1:
            raise ValueError("网页更新 Codex 需要 npm 全局安装；请在服务器手动更新自定义命令")
        root = Path((await _command([npm, "root", "--global"])).strip())
        prefix = Path((await _command([npm, "prefix", "--global"])).strip())
        executable = shutil.which(argv[0])
        expected = root / "@openai" / "codex" / "bin" / "codex.js"
        if not executable or not expected.is_file() or Path(executable).resolve() != expected.resolve():
            raise ValueError("当前 Codex 不属于此 npm 全局安装；请在服务器手动更新或修正 SKILL_RUNNER_CODEX_BIN")
        binary_dir = prefix / "bin" if (prefix / "bin").is_dir() else prefix
        if not all(os.access(path, os.W_OK) for path in (prefix, root, binary_dir, expected.parent.parent)):
            raise ValueError("服务用户没有 npm 全局目录写入权限；请由管理员更新或改用用户目录安装")
        return [npm, "install", "--global", "--registry=https://registry.npmjs.org", f"@openai/codex@{target}"]

    async def check(self) -> dict:
        if self.active or self._checking:
            raise Busy("正在更新或检查版本，请稍后再试")
        self._checking = True
        try:
            await asyncio.gather(*(self._check_one(harness) for harness in self._runtimes))
            self._checked_at = time.time()
        finally:
            self._checking = False
        return self.snapshot()

    async def _check_one(self, harness: str) -> None:
        state = self._runtimes[harness]
        state.update(current=None, latest=None, update_available=False, can_update=False,
                     reason=None, error=None, status="ready", message=None)
        try:
            state["current"] = await self._current(harness)
            state["latest"] = _valid_version(await asyncio.to_thread(_latest_version, harness))
            state["update_available"] = tuple(map(int, state["latest"].split("."))) > tuple(map(int, state["current"].split(".")))
            try:
                await self._install_command(harness, state["latest"])
                state["can_update"] = state["update_available"]
            except Exception as exc:
                state["reason"] = str(exc)
        except Exception as exc:
            state.update(error=str(exc), status="failed")

    async def start(self, harness: str) -> dict:
        if not isinstance(harness, str) or harness not in self._runtimes:
            raise ValueError("不支持的运行工具")
        if self.active or self._checking:
            raise Busy("正在更新或检查版本，请稍后再试")
        state = self._runtimes[harness]
        if not state["can_update"] or not state["latest"]:
            raise ValueError(state["reason"] or "请先检查更新，并确认有可安装的新版本")
        target = _valid_version(state["latest"])
        self.runner.reserve_runtime_update()  # No await before reservation and active flag.
        self._active = True
        state.update(status="updating", can_update=False, error=None, message=f"正在更新到 {target}")
        self._task = asyncio.create_task(self._update(harness, target))
        return self.snapshot()

    async def _update(self, harness: str, target: str) -> None:
        state = self._runtimes[harness]
        try:
            await self.runner.close_idle_for_runtime_update()
            state["current"] = await self._current(harness)
            if tuple(map(int, state["current"].split("."))) >= tuple(map(int, target.split("."))):
                raise ValueError("实际运行版本已经变化，请重新检查更新")
            argv = await self._install_command(harness, target)
            await _command(argv, timeout=300)
            state["current"] = await self._current(harness)
            if state["current"] != target:
                raise RuntimeError(f"安装后实际运行版本为 {state['current']}，未达到目标 {target}；请检查服务器安装路径")
            state.update(status="succeeded", update_available=False, updated_at=time.time(),
                         message=f"已更新到 {target}；新对话将使用此版本")
        except asyncio.CancelledError:
            state.update(status="failed", error="服务关闭中断了更新；请重新检查实际版本", message=None)
            raise
        except Exception as exc:
            state.update(status="failed", error=str(exc), message=None)
        finally:
            self._active = False
            self.runner.release_runtime_update()

    async def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            # Cancellation before the task's first instruction skips its finally.
            if self.active:
                for state in self._runtimes.values():
                    if state["status"] == "updating":
                        state.update(status="failed", error="服务关闭中断了更新", message=None)
                self._active = False
                self.runner.release_runtime_update()
