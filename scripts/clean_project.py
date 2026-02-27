"""项目清理脚本（面向开源发布前检查）"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
from pathlib import Path


TRANSIENT_DIRS = [
    "tests",
    ".pytest_cache",
    ".tmp_testdata",
    "web/frontend/node_modules",
    "web/frontend/dist",
]
TRANSIENT_FILES = [
    "test_prompts.py",
    "test_api.py",
]
TEMP_PATTERNS = ["*~", ".DS_Store", "Thumbs.db", "*.tmp", "*.pyc"]
PROTECTED_TOP_LEVEL_DIRS = {".venv", "conversations", "data", "projects"}


def _remove_path(path: Path, removed: list[str]) -> None:
    if not path.exists():
        return
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            if path.exists():
                return
            removed.append(f"目录: {path.as_posix()}/")
        else:
            path.unlink(missing_ok=True)
            if path.exists():
                return
            removed.append(f"文件: {path.as_posix()}")
    except Exception:
        return


def _is_protected(path: Path, base_path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(base_path.resolve())
    except Exception:
        return True
    if not rel.parts:
        return False
    return rel.parts[0] in PROTECTED_TOP_LEVEL_DIRS


def clean_project(base_dir: str = ".", release_mode: bool = False) -> list[str]:
    """清理项目中的测试文件、缓存和临时产物。"""
    base_path = Path(base_dir)
    removed_items: list[str] = []

    for rel in TRANSIENT_FILES:
        _remove_path(base_path / rel, removed_items)

    for rel in TRANSIENT_DIRS:
        _remove_path(base_path / rel, removed_items)

    for root, dirs, files in os.walk(base_path, topdown=True, onerror=lambda _e: None):
        root_path = Path(root)
        if _is_protected(root_path, base_path):
            dirs[:] = []
            continue

        for dirname in list(dirs):
            dir_path = root_path / dirname
            if dirname == "__pycache__" and not _is_protected(dir_path, base_path):
                _remove_path(dir_path, removed_items)
                dirs.remove(dirname)

        for filename in files:
            file_path = root_path / filename
            if _is_protected(file_path, base_path):
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in TEMP_PATTERNS):
                _remove_path(file_path, removed_items)

    if release_mode:
        # 仅清理明确的测试样例项目，不碰进行中的翻译项目。
        for rel in ("projects/test-project", "projects/test2-project"):
            _remove_path(base_path / rel, removed_items)

    print("\n" + "=" * 50)
    print("清理完成")
    print("=" * 50)
    if not removed_items:
        print("未发现可清理项。")
        return removed_items

    print(f"共清理 {len(removed_items)} 项：")
    for item in removed_items:
        print(f"  - {item}")
    return removed_items


def main() -> None:
    parser = argparse.ArgumentParser(description="清理项目中的临时与测试产物")
    parser.add_argument("project_dir", nargs="?", default=os.getcwd(), help="项目根目录")
    parser.add_argument(
        "--release",
        action="store_true",
        help="发布清理模式：额外清理已知测试项目目录",
    )
    args = parser.parse_args()

    print(f"开始清理项目: {args.project_dir}")
    clean_project(args.project_dir, release_mode=args.release)


if __name__ == "__main__":
    main()
