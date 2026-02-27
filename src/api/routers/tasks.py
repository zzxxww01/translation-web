"""
Tasks Router - 任务管理 API

管理简单的任务列表。
"""

import json
from pathlib import Path
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="", tags=["tasks"])

TASKS_FILE = Path("data/tasks.json")


# ============ Models ============


class Task(BaseModel):
    id: str
    text: str
    completed: bool = False


class TasksData(BaseModel):
    tasks: List[Task] = Field(default_factory=list)


# ============ Default Tasks ============

DEFAULT_TASKS = [
    {
        "id": "1",
        "text": "XHS, successfully logged in - put all content into chinese and upload",
        "completed": False,
    },
    {
        "id": "2",
        "text": "working on verifying our accounts for WeChat and XHS",
        "completed": False,
    },
    {
        "id": "3",
        "text": "starting: Douyin (short form video) and BiliBili (long form video)",
        "completed": False,
    },
    {"id": "4", "text": "upload past videos, begin new ones", "completed": False},
    {
        "id": "5",
        "text": "starting work on translating SemiAnalysis articles for WeChat",
        "completed": False,
    },
    {
        "id": "6",
        "text": "do research on Baidu, understand needs to create business platform",
        "completed": False,
    },
]


def _write_tasks(tasks: List[dict]) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f, ensure_ascii=False, indent=2)


def _load_tasks_or_default() -> List[dict]:
    if not TASKS_FILE.exists():
        _write_tasks(DEFAULT_TASKS)
        return DEFAULT_TASKS

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        tasks = data.get("tasks", [])
        return tasks if isinstance(tasks, list) else DEFAULT_TASKS
    except (json.JSONDecodeError, OSError, TypeError):
        # 文件损坏时回退默认值，保证接口可用
        _write_tasks(DEFAULT_TASKS)
        return DEFAULT_TASKS


# ============ API Endpoints ============


@router.get("/tasks")
async def get_tasks():
    """获取所有任务"""
    return _load_tasks_or_default()


@router.post("/tasks")
async def save_tasks(tasks: List[Task]):
    """保存所有任务"""
    _write_tasks([t.model_dump() for t in tasks])
    return {"message": "Tasks saved", "count": len(tasks)}
