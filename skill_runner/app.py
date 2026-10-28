"""HTTP 接口，全部挂在 /api/skills 下（nginx 把这个前缀转给本服务，其余 /api 仍归 momo 后端）。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from . import agents, auth
from .config import BILLING_OVERRIDE_ENV, Config
from .models import ModelCatalog
from .runtime_updates import RuntimeUpdates
from .runner import Runner, RunnerError, SessionFactory, make_title
from .store import RunStore, UploadTooLarge

logger = logging.getLogger(__name__)

PREFIX = "/api/skills"
SSE_PING_S = 15.0


class LoginBody(BaseModel):
    password: str


class AnswerBody(BaseModel):
    qid: str
    answers: dict[str, Any] | None = None
    response: str | None = None


def _strip_billing_overrides() -> None:
    for name in BILLING_OVERRIDE_ENV:
        if os.environ.pop(name, None) is not None:
            logger.warning("已移除环境变量 %s：skill-runner 只用订阅额度，不走 API 计费或网关", name)


def create_app(
    config: Config,
    session_factory: SessionFactory | None = None,
    store: RunStore | None = None,
) -> FastAPI:
    store = store or RunStore(config.runs_dir)
    if session_factory is None:
        from .antigravity_session import make_antigravity_factory
        from .codex_session import make_codex_factory
        from .sdk_session import make_factory

        factories = {
            "claude": make_factory(config),
            "codex": make_codex_factory(config),
            "antigravity": make_antigravity_factory(config),
        }

        async def session_factory(spec):  # 按任务选的 harness 建会话
            if spec.harness not in factories:
                raise RunnerError(f"不支持的 harness：{spec.harness}")
            return await factories[spec.harness](spec)
    runner = Runner(config, store, session_factory)
    model_catalog = ModelCatalog(config)
    runtime_updates = RuntimeUpdates(config, runner)
    limiter = auth.LoginLimiter()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _strip_billing_overrides()
        recovered = runner.recover()
        if recovered:
            logger.warning("标记了 %d 个因重启中断的运行", recovered)
        runner.resume_auto_replies()
        if not config.password:
            logger.error("未设置 SKILL_RUNNER_PASSWORD，所有登录都会被拒绝")
        yield
        await runtime_updates.shutdown()
        await runner.shutdown()

    app = FastAPI(title="skill-runner", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.runner = runner
    app.state.runtime_updates = runtime_updates

    @app.exception_handler(RunnerError)
    async def _runner_error(_request: Request, exc: RunnerError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    def set_session(response: Response) -> None:
        response.set_cookie(
            auth.COOKIE_NAME,
            auth.issue_token(config.session_secret),
            max_age=auth.SESSION_TTL_S,
            httponly=True,
            secure=config.cookie_secure,
            samesite="strict",
            path=PREFIX,
        )

    def require_auth(request: Request, response: Response) -> None:
        token = request.cookies.get(auth.COOKIE_NAME)
        if not auth.verify_token(config.session_secret, token):
            raise HTTPException(status_code=401, detail="请先登录")
        if auth.should_refresh(token):
            set_session(response)

    public = APIRouter(prefix=PREFIX)
    api = APIRouter(prefix=PREFIX, dependencies=[Depends(require_auth)])

    @public.post("/login")
    async def login(body: LoginBody, response: Response):
        if not config.password:
            raise HTTPException(status_code=503, detail="服务器未配置口令")
        wait = limiter.locked_for()
        if wait > 0:
            raise HTTPException(status_code=429, detail=f"尝试过于频繁，请 {int(wait) + 1} 秒后再试")
        ok = auth.check_password(config.password, body.password)
        limiter.record(ok)
        if not ok:
            raise HTTPException(status_code=401, detail="口令不对")
        set_session(response)
        return {"ok": True}

    @public.post("/logout")
    async def logout(response: Response):
        response.delete_cookie(auth.COOKIE_NAME, path=PREFIX)
        return {"ok": True}

    @api.get("/me")
    async def me():
        return {"ok": True, "max_active": config.max_active, "max_upload_mb": config.max_upload_bytes // (1024 * 1024)}

    @api.get("/catalog")
    async def catalog():
        return agents.build_catalog(config)

    @api.get("/runs")
    async def list_runs():
        return [meta.to_dict() for meta in runner.list_runs()]

    @api.get("/models/{harness}")
    async def list_models(harness: str, refresh: bool = False):
        try:
            with runner.runtime_use():
                return await model_catalog.get(harness, refresh=refresh)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/runtime")
    async def runtime_status():
        return runtime_updates.snapshot()

    @api.post("/runtime/check")
    async def check_runtime_updates():
        return await runtime_updates.check()

    @api.post("/runtime/{harness}/update")
    async def update_runtime(harness: str):
        try:
            return await runtime_updates.start(harness)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _save_uploads(run_id: str, files: list[UploadFile]) -> list[str]:
        saved = []
        for upload in files:
            if not upload.filename:
                continue
            try:
                saved.append(store.save_upload(run_id, upload.filename, upload.file, config.max_upload_bytes))
            except UploadTooLarge as exc:
                raise HTTPException(
                    status_code=413,
                    detail=f"{exc} 超过 {config.max_upload_bytes // (1024 * 1024)} MB 上限",
                ) from exc
        return saved

    @api.post("/runs")
    async def create_run(
        request: Request,
        skill: str = Form(""),  # 留空即直接对话
        harness: str = Form("claude"),  # claude / codex / antigravity
        model: str = Form("", max_length=128),
        message: str = Form(""),
        # 等确认时多少分钟没回复就自动按推荐方案继续；0 = 一直等
        auto_reply_minutes: int = Form(0, ge=0, le=1440),
        title: str = Form("", max_length=200),  # 对话标题，不给就从消息里取
        files: list[UploadFile] = File(default=[]),
    ):
        names = [f.filename for f in files if f.filename]
        if not message.strip() and not names:
            raise HTTPException(status_code=400, detail="写点说明或者附个文件")
        meta = runner.create(skill, make_title(message, names, title), harness, auto_reply_minutes * 60, model=model)
        try:
            saved = await asyncio.to_thread(_save_uploads, meta.id, files)
        except HTTPException:
            await runner.delete(meta.id, reason="upload_failed", client_ip=_client_ip(request))
            raise
        meta = await runner.begin(meta.id, message, saved)
        return meta.to_dict()

    @api.get("/runs/{run_id}")
    async def get_run(run_id: str):
        return runner.meta(run_id).to_dict()

    @api.post("/runs/{run_id}/messages")
    async def post_message(
        run_id: str,
        message: str = Form(""),
        files: list[UploadFile] = File(default=[]),
    ):
        runner.meta(run_id)  # 先确认存在，再写文件
        saved = await asyncio.to_thread(_save_uploads, run_id, files)
        meta = await runner.send_message(run_id, message, saved)
        return meta.to_dict()

    @api.post("/runs/{run_id}/answer")
    async def answer(run_id: str, body: AnswerBody):
        return runner.answer(run_id, body.qid, body.answers, body.response).to_dict()

    @api.post("/runs/{run_id}/interrupt")
    async def interrupt(run_id: str):
        return (await runner.interrupt(run_id)).to_dict()

    @api.post("/runs/{run_id}/stop")
    async def stop(run_id: str):
        return (await runner.stop(run_id)).to_dict()

    @api.delete("/runs/{run_id}")
    async def delete_run(run_id: str, request: Request):
        await runner.delete(run_id, client_ip=_client_ip(request))
        return {"ok": True}

    @api.get("/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0):
        last_id = request.headers.get("last-event-id", "")
        if last_id.isdigit():
            after = max(after, int(last_id))
        backlog, queue = runner.subscribe(run_id, after)

        async def stream():
            try:
                # 先让浏览器知道断线后隔多久重连
                yield "retry: 3000\n\n"
                for event in backlog:
                    yield _sse(event)
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=SSE_PING_S)
                    except asyncio.TimeoutError:
                        # 用具名事件而不是注释：注释到不了页面脚本，页面靠它判断连接是否还活着。
                        # 经代理/隧道的长连接偶尔会卡住却不断开，页面收不到心跳就会自己重连。
                        yield "event: ping\ndata: {}\n\n"
                        continue
                    if event is None:  # 运行被删除或服务关闭
                        return
                    yield _sse(event)
            finally:
                runner.unsubscribe(run_id, queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api.get("/runs/{run_id}/files")
    async def list_files(run_id: str):
        runner.meta(run_id)
        return await asyncio.to_thread(store.list_files, run_id)

    @api.get("/runs/{run_id}/files/{rel_path:path}")
    async def download(run_id: str, rel_path: str):
        runner.meta(run_id)
        path = store.resolve_file(run_id, rel_path)
        if path is None:
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(path, filename=path.name)

    app.include_router(public)
    app.include_router(api)
    return app


def _client_ip(request: Request) -> str | None:
    """经 Cloudflare / nginx 转发时真实来源在 X-Forwarded-For 第一个。"""
    first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return first or (request.client.host if request.client else None)


def _sse(event: dict[str, Any]) -> str:
    return f"id: {event['seq']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
