"""
翻译稿（翻译记录）接口，以及 Slack 帖子的固定流程：提取 → 翻译 → 标题。

- 帖子翻译页和 Slack 翻译模式都用 GET/PUT /api/post-drafts/... 读写同一种翻译稿（见 src/services/post_drafts.py）。
- POST /api/post-drafts/slack/{频道}/{thread_ts}/run：后端跑完整流程（新建，或「重新提取」时追加新版本）。
- 后台任务 auto_translate_loop：有人在 thread 里直接 @我、而这个 thread 还没有翻译稿时自动跑一遍（设置里可关）。
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.requests import Request as StarletteRequest

from src.api.utils.concurrency import run_blocking
from src.services.post_drafts import (
    DraftError,
    PostDraftStore,
    new_manual_id,
    slack_draft_id,
)
from src.services.slack_inbox import SlackInboxError
from src.settings import settings

from ..middleware import APIException
from ..middleware.rate_limit import limiter
from .slack_inbox import _run_ai, _to_api_error, get_slack_ai, get_slack_inbox, read_slack_settings
from .translate_models import GenerateTitleRequest, PostTranslateRequest
from .translate_posts import generate_title, translate_post

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/post-drafts")

AUTO_INTERVAL_S = 60
AUTO_RETRY_AFTER_S = 3600
MAX_TITLES = 8


@lru_cache(maxsize=1)
def get_draft_store() -> PostDraftStore:
    return PostDraftStore(Path(settings.post_drafts_dir))


def _draft_error(error: DraftError) -> APIException:
    return APIException(status_code=error.status_code, detail=error.message, error_code=error.code)


async def _store(func, *args, **kwargs):
    try:
        return await run_blocking(func, *args, **kwargs)
    except DraftError as error:
        raise _draft_error(error) from error


# ---------------------------------------------------------------- 翻译记录：读写

class DraftBody(BaseModel):
    state: Dict[str, Any]
    images: List[Dict[str, Any]] = Field(default_factory=list, max_length=60)
    status: str = "draft"
    seen: bool = True
    rev: Optional[int] = None


@router.get("")
async def list_drafts(q: str = Query("", max_length=200), source: str = Query("", pattern="^(|slack|manual)$")):
    return {"items": await _store(get_draft_store().list, q, source)}


@router.post("")
@limiter.limit("60/minute")
async def create_manual_draft(request: Request, body: DraftBody):
    """帖子翻译页第一次出译文时建稿。"""
    doc = await _store(get_draft_store().save, new_manual_id(), body.model_dump(exclude={"rev"}), rev=None, source="manual")
    return doc


@router.get("/slack/{channel_id}/{thread_ts}")
async def get_slack_draft(channel_id: str, thread_ts: str):
    return {"draft": await _store(get_draft_store().get, slack_draft_id(channel_id, thread_ts))}


@router.get("/{draft_id}")
async def get_draft(draft_id: str):
    doc = await _store(get_draft_store().get, draft_id)
    if not doc:
        raise APIException(status_code=404, detail="找不到这份翻译稿", error_code="DRAFT_NOT_FOUND")
    return doc


@router.put("/{draft_id}")
@limiter.limit("120/minute")
async def save_draft(request: Request, draft_id: str, body: DraftBody):
    return await _store(get_draft_store().save, draft_id, body.model_dump(exclude={"rev"}), rev=body.rev)


@router.get("/{draft_id}/images.zip")
@limiter.limit("20/minute")
async def download_images(request: Request, draft_id: str):
    """配图打包下载，按发帖顺序编号：01-xxx.png、02-xxx.jpg……"""
    doc = await _store(get_draft_store().get, draft_id)
    if not doc or not doc.get("images"):
        raise APIException(status_code=404, detail="这份翻译稿没有配图", error_code="NO_IMAGES")
    inbox = get_slack_inbox()
    slack = doc.get("slack") or {}

    def build() -> bytes:
        if slack:
            inbox.replies(slack["channel_id"], slack["thread_ts"])  # 登记文件下载地址（重启后内存里没有）
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
            for n, img in enumerate(doc["images"], start=1):
                path, _mimetype, name = inbox.file(img["id"])
                zf.write(path, f"{n:02d}-{Path(name).name}")
        return buf.getvalue()

    try:
        body = await run_blocking(build)
    except SlackInboxError as error:
        raise _to_api_error(error) from error
    title = ((doc.get("slack") or {}).get("title") or "配图")[:40]
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(title + '.zip')}"},
    )


# ---------------------------------------------------------------- Slack 帖子：提取 → 翻译 → 标题

_thread_locks: Dict[str, asyncio.Lock] = {}


def _internal_request() -> StarletteRequest:
    # 直接调翻译 / 标题的处理函数（绕过网页限流），它们不读 request
    return StarletteRequest({"type": "http", "method": "POST", "path": "/internal", "headers": []})


def _empty_state() -> Dict[str, Any]:
    return {
        "originalText": "", "sourceRevision": 0, "versions": [], "currentVersionId": None,
        "versionMetadata": {}, "generatedTitles": [], "selectedTitle": "", "titleContentIdentity": "",
    }


def _add_version(state: Dict[str, Any], content: str, model_used: Optional[str], instruction: Optional[str]) -> str:
    """和前端 postStore.addVersion 同构：追加一版并设为当前。"""
    version_id = f"v-{uuid.uuid4()}"
    number = max([v.get("versionNumber", 0) for v in state["versions"]] + [0]) + 1
    for v in state["versions"]:
        v["isCurrent"] = False
    state["versions"].append({
        "id": version_id,
        "versionNumber": number,
        "content": content,
        "type": "translation",
        **({"instruction": instruction} if instruction else {}),
        "sourceRevision": state["sourceRevision"],
        "sourceText": state["originalText"],
        "isCurrent": True,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    state["currentVersionId"] = version_id
    state.setdefault("versionMetadata", {})[version_id] = {
        "name": f"{'重新提取后翻译' if number > 1 else '初始翻译'} v{number}",
        "pinned": False,
        "modelUsed": model_used,
    }
    return version_id


async def run_slack_pipeline(channel_id: str, thread_ts: str, *, instruction: Optional[str] = None,
                             auto: bool = False) -> Dict[str, Any]:
    """提取原文和配图 → 翻译成新版本 → 生成标题，存成翻译稿。已有稿子时保留旧版本，追加新的。"""
    key = f"{channel_id}:{thread_ts}"
    lock = _thread_locks.setdefault(key, asyncio.Lock())
    async with lock:
        store = get_draft_store()
        material = await run_blocking(get_slack_inbox().post_material, channel_id, thread_ts)
        images_by_id = {img["id"]: img for img in material["images"]}
        extraction = await get_slack_ai().extract_post(material["thread"], list(images_by_id), instruction)

        def to_ts(ids: List[int]) -> List[str]:
            return [material["message_ts"][n - 1] for n in ids if 1 <= n <= len(material["message_ts"])]

        draft_id = slack_draft_id(channel_id, thread_ts)
        existing = await _store(store.get, draft_id)
        state = (existing or {}).get("state") or _empty_state()
        state["originalText"] = extraction["source_text"]
        state["sourceRevision"] = int(state.get("sourceRevision") or 0) + 1
        doc = {
            **(existing or {}),
            "id": draft_id,
            "source": "slack",
            "slack": {
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "channel_name": material["channel_name"],
                "title": material["title"],
                "permalink": material["permalink"],
                "latest_ts": material["latest_ts"],
            },
            "extraction": {
                "has_post": extraction["has_post"],
                "note": extraction["note"],
                "message_ts": to_ts(extraction["message_ids"]),
                "candidates": [{**c, "message_ts": to_ts(c.pop("message_ids"))} for c in extraction["candidates"]],
                "instruction": instruction or "",
                "extracted_at": time.time(),
                "latest_ts": material["latest_ts"],
            },
            "images": [{"id": i, "name": images_by_id[i]["name"]} for i in extraction["image_ids"]],
            "status": "draft",
            "auto": auto if not existing else bool(existing.get("auto")) and auto,
            "seen": not auto,
            "state": state,
        }
        # 先把提取结果存下来：后面翻译失败，用户也能看到原文和配图，手动点「重新翻译」
        doc = await _store(store.put_system, doc)
        source = extraction["source_text"].strip()
        if not extraction["has_post"] or not source:
            return doc

        translated = await translate_post.__wrapped__(
            request=_internal_request(), body=PostTranslateRequest(content=source[:10000]))
        version_id = _add_version(state, translated.translation, translated.model_used, instruction)
        content = translated.translation
        try:
            titles = await generate_title.__wrapped__(
                request=_internal_request(), body=GenerateTitleRequest(content=content))
            state["generatedTitles"] = [t.strip() for t in titles.title.splitlines() if t.strip()][:MAX_TITLES]
            state["selectedTitle"] = ""
            # 和前端 titleContentIdentity 一致，标题才不会显示「内容已变更」
            state["titleContentIdentity"] = f"version:{version_id}:{content}"
        except Exception:  # noqa: BLE001 - 标题失败不影响译文，用户可以再点「生成」
            logger.warning("Slack 帖子标题生成失败 %s", key, exc_info=True)
        doc["state"] = state
        return await _store(store.put_system, doc)


class RunBody(BaseModel):
    instruction: Optional[str] = Field(None, max_length=500)


@router.post("/slack/{channel_id}/{thread_ts}/run")
@limiter.limit("20/minute")
async def run_slack(request: Request, channel_id: str, thread_ts: str, body: RunBody):
    try:
        return await _run_ai(run_slack_pipeline(channel_id, thread_ts, instruction=body.instruction), "帖子提取")
    except DraftError as error:
        raise _draft_error(error) from error


# ---------------------------------------------------------------- 后台：@我 的 thread 自动翻译

def _attempts_path() -> Path:
    return Path(settings.slack_cache_dir) / "auto_translate.json"


def _load_attempts() -> Dict[str, float]:
    try:
        data = json.loads(_attempts_path().read_text(encoding="utf-8"))
        return {k: float(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_attempts(attempts: Dict[str, float]) -> None:
    path = _attempts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 30 * 86400
    path.write_text(json.dumps({k: v for k, v in attempts.items() if v > cutoff}), encoding="utf-8")


async def auto_translate_once(attempts: Dict[str, float]) -> int:
    """跑一轮：返回这轮自动翻了几个 thread。"""
    if not read_slack_settings().get("auto_translate_mentions"):
        return 0
    inbox = get_slack_inbox()
    if inbox.store.load() is None:
        return 0
    store = get_draft_store()
    done = 0
    for channel_id, thread_ts in await run_blocking(inbox.direct_mention_threads):
        draft_id = slack_draft_id(channel_id, thread_ts)
        if time.time() - attempts.get(draft_id, 0) < AUTO_RETRY_AFTER_S or await run_blocking(store.get, draft_id):
            continue
        attempts[draft_id] = time.time()
        await run_blocking(_save_attempts, attempts)
        try:
            await run_slack_pipeline(channel_id, thread_ts, auto=True)
            done += 1
        except Exception:  # noqa: BLE001 - 一个 thread 失败不影响其他，一小时后再试
            logger.warning("自动翻译 @我 的 thread 失败 %s", draft_id, exc_info=True)
    return done


async def auto_translate_loop() -> None:
    attempts = await run_blocking(_load_attempts)
    while True:
        await asyncio.sleep(AUTO_INTERVAL_S)
        try:
            await auto_translate_once(attempts)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 后台任务不能死
            logger.warning("自动翻译轮询出错", exc_info=True)
