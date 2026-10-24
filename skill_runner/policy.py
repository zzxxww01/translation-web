"""工具权限决策：命令和改文件自动执行，越界的才拒绝。

沙箱只管 Bash 及其子进程；Edit/Write 这类文件工具走权限规则，不受沙箱约束，所以写路径要在这里
再卡一次。能走到这里的 Bash 调用，说明它要求在沙箱外执行（沙箱内的命令已被自动放行）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


@dataclass(frozen=True)
class Decision:
    allow: bool
    message: str = ""


def _target_path(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
    value = tool_input.get(key)
    return value if isinstance(value, str) and value else None


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def writable(path: str, run_dir: Path, extra_write: tuple[Path, ...]) -> bool:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = run_dir / candidate
    # resolve 会跟随符号链接，防止借运行目录里的链接写到外面去
    resolved = Path(os.path.realpath(candidate))
    roots = (run_dir, *extra_write)
    return any(_within(resolved, Path(os.path.realpath(root))) for root in roots)


def decide(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    run_dir: Path,
    extra_write: tuple[Path, ...],
    sandbox: bool,
) -> Decision:
    if tool_name in WRITE_TOOLS:
        target = _target_path(tool_name, tool_input)
        if target is None:
            return Decision(False, f"{tool_name} 缺少目标路径")
        if writable(target, run_dir, extra_write):
            return Decision(True)
        return Decision(
            False,
            f"不允许写 {target}：只能写当前运行目录和白名单路径。请把产出写到当前目录下。",
        )
    if tool_name == "Bash" and sandbox:
        return Decision(
            False,
            "这条命令要求在沙箱外执行，skill-runner 不允许。请改用能在沙箱内运行的方式；"
            "确实需要时告诉用户由管理员把它加进 SKILL_RUNNER_UNSANDBOXED_COMMANDS。",
        )
    return Decision(True)
