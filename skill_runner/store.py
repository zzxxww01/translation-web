"""运行目录的磁盘布局：每次运行一个目录，元数据、事件记录、上传文件和 Claude 的产出都在里面。

    runs/<run_id>/meta.json      状态与会话 ID（原子写）
    runs/<run_id>/events.jsonl   页面事件，一行一个，只追加；页面重连时从这里回放
    runs/<run_id>/input/         用户上传的文件
    runs/<run_id>/...            其余都是 Claude 的工作目录内容，页面上可下载
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO, Iterable

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
META_FILE = "meta.json"
EVENTS_FILE = "events.jsonl"
INPUT_DIR = "input"
# 页面文件列表里不展示的根目录条目
INTERNAL_FILES = {META_FILE, EVENTS_FILE}
MAX_LISTED_FILES = 2000
CHUNK = 1024 * 1024


class UploadTooLarge(Exception):
    pass


@dataclass
class RunMeta:
    id: str
    skill: str
    title: str
    status: str
    created_at: float
    updated_at: float
    session_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", base).strip().lstrip(".")
    if len(base) > 120:
        stem, dot, ext = base.rpartition(".")
        base = (stem[: 120 - len(ext) - 1] + "." + ext) if dot and len(ext) <= 10 else base[:120]
    return base or "file"


class RunStore:
    def __init__(self, runs_dir: Path):
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    # ---- 目录与元数据 ----

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.match(run_id):
            raise KeyError(run_id)
        return self.runs_dir / run_id

    def exists(self, run_id: str) -> bool:
        try:
            return (self.run_dir(run_id) / META_FILE).is_file()
        except KeyError:
            return False

    def create(self, skill: str, title: str) -> RunMeta:
        now = time.time()
        while True:
            run_id = time.strftime("%Y%m%d-%H%M%S", time.localtime(now)) + "-" + secrets.token_hex(3)
            path = self.runs_dir / run_id
            try:
                path.mkdir()
                break
            except FileExistsError:
                continue
        (path / INPUT_DIR).mkdir()
        meta = RunMeta(id=run_id, skill=skill, title=title, status="idle", created_at=now, updated_at=now)
        self.save_meta(meta)
        return meta

    def save_meta(self, meta: RunMeta) -> None:
        path = self.run_dir(meta.id) / META_FILE
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    def load_meta(self, run_id: str) -> RunMeta | None:
        try:
            raw = json.loads((self.run_dir(run_id) / META_FILE).read_text(encoding="utf-8"))
        except (KeyError, OSError, ValueError):
            return None
        fields = RunMeta.__dataclass_fields__
        return RunMeta(**{k: v for k, v in raw.items() if k in fields})

    def list_meta(self) -> list[RunMeta]:
        metas = []
        for child in self.runs_dir.iterdir():
            if child.is_dir() and RUN_ID_RE.match(child.name):
                meta = self.load_meta(child.name)
                if meta is not None:
                    metas.append(meta)
        return sorted(metas, key=lambda m: m.created_at, reverse=True)

    def delete(self, run_id: str) -> None:
        shutil.rmtree(self.run_dir(run_id))

    # ---- 事件记录 ----

    def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self.run_dir(run_id) / EVENTS_FILE, "a", encoding="utf-8") as fh:
            fh.write(line)

    def read_events(self, run_id: str, after_seq: int = 0) -> list[dict[str, Any]]:
        path = self.run_dir(run_id) / EVENTS_FILE
        if not path.is_file():
            return []
        events = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    event = json.loads(line)
                except ValueError:
                    # 进程在写一半时被杀会留下残行，跳过即可，不影响其余事件
                    continue
                if event.get("seq", 0) > after_seq:
                    events.append(event)
        return events

    def last_seq(self, run_id: str) -> int:
        events = self.read_events(run_id)
        return max((e.get("seq", 0) for e in events), default=0)

    # ---- 文件 ----

    def save_upload(self, run_id: str, filename: str, src: BinaryIO, max_bytes: int) -> str:
        input_dir = self.run_dir(run_id) / INPUT_DIR
        input_dir.mkdir(exist_ok=True)
        name = safe_filename(filename)
        target = input_dir / name
        stem, suffix = target.stem, target.suffix
        n = 1
        while target.exists():
            target = input_dir / f"{stem}-{n}{suffix}"
            n += 1
        written = 0
        try:
            with open(target, "wb") as out:
                while chunk := src.read(CHUNK):
                    written += len(chunk)
                    if written > max_bytes:
                        raise UploadTooLarge(name)
                    out.write(chunk)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return f"{INPUT_DIR}/{target.name}"

    def list_files(self, run_id: str) -> list[dict[str, Any]]:
        root = self.run_dir(run_id)
        files: list[dict[str, Any]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # 隐藏目录（.claude、.cache 之类）是工具的内部状态，不是产出
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            rel_dir = Path(dirpath).relative_to(root)
            for name in sorted(filenames):
                if name.startswith(".") or (rel_dir == Path(".") and name in INTERNAL_FILES):
                    continue
                full = Path(dirpath) / name
                try:
                    stat = full.stat()
                except OSError:
                    continue
                files.append({
                    "path": (rel_dir / name).as_posix(),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                })
                if len(files) >= MAX_LISTED_FILES:
                    break
            if len(files) >= MAX_LISTED_FILES:
                break
        return sorted(files, key=lambda f: f["path"])

    def resolve_file(self, run_id: str, rel_path: str) -> Path | None:
        root = Path(os.path.realpath(self.run_dir(run_id)))
        candidate = Path(os.path.realpath(root / rel_path))
        try:
            rel = candidate.relative_to(root)
        except ValueError:
            return None
        if not rel.parts or rel.parts[0] in INTERNAL_FILES or any(p.startswith(".") for p in rel.parts):
            return None
        return candidate if candidate.is_file() else None


def iter_skill_catalog(skills_dir: Path, names: Iterable[str]) -> list[dict[str, Any]]:
    """读 SKILL.md 的 frontmatter：是否装了、简介。agent 名片缺项时拿它兜底。"""
    catalog = []
    for name in names:
        skill_md = skills_dir / name / "SKILL.md"
        description = ""
        available = skill_md.is_file()
        if available:
            try:
                text = skill_md.read_text(encoding="utf-8")
            except OSError:
                text = ""
            match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
            if match:
                description = match.group(1).strip().strip("'\"")
        catalog.append({"name": name, "description": description[:400], "available": available})
    return catalog
