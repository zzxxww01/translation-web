"""Translation Agent API entrypoint."""

from dotenv import load_dotenv

load_dotenv()

import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .middleware import LoggingMiddleware, register_error_handlers
from .routers import (
    confirmation,
    consistency,
    glossary,
    project_glossary,
    projects,
    segmentation,
    slack,
    tasks,
    tools,
    translate,
)


app = FastAPI(
    title="Translation Agent API",
    description="High-quality translation platform API",
    version="2.0.0",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
register_error_handlers(app)


app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(glossary.router, prefix="/api", tags=["glossary"])
app.include_router(project_glossary.router, prefix="/api", tags=["projects"])
app.include_router(confirmation.router, prefix="/api", tags=["confirmation"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(slack.router, prefix="/api", tags=["slack"])
app.include_router(tools.router, prefix="/api", tags=["tools"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(consistency.router, prefix="/api", tags=["consistency"])
app.include_router(segmentation.router, prefix="/api", tags=["segmentation"])


frontend_dist_path = Path(__file__).parent.parent.parent / "web" / "frontend" / "dist"


class OptimizedStaticFiles(StaticFiles):
    """StaticFiles that skip source map requests."""

    def lookup_path(self, path: str):
        if path.endswith(".map"):
            return None, None
        return super().lookup_path(path)


class SafeStaticFiles(StaticFiles):
    """StaticFiles that gracefully ignore invalid paths on Windows."""

    def lookup_path(self, path: str):
        try:
            return super().lookup_path(path)
        except OSError as exc:
            import logging
            logging.getLogger(__name__).debug("SafeStaticFiles: ignoring OSError for path %r: %s", path, exc)
            return "", None


if frontend_dist_path.exists():
    app.mount(
        "/assets",
        OptimizedStaticFiles(directory=str(frontend_dist_path / "assets")),
        name="assets",
    )
    app.mount("/static", StaticFiles(directory=str(frontend_dist_path)), name="static")

projects_path = Path(__file__).parent.parent.parent / "projects"
if projects_path.exists():
    app.mount("/projects", SafeStaticFiles(directory=str(projects_path)), name="projects")


@app.get(
    "/api/health",
    summary="Health check",
    description="Check whether the API service is running",
    tags=["system"],
)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Translation Agent API"}


@app.get(
    "/",
    response_class=HTMLResponse,
    summary="Web UI",
    description="Return the Translation Agent web UI",
    tags=["system"],
    include_in_schema=False,
)
async def root():
    """Return the React frontend app."""
    index_path = frontend_dist_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return HTMLResponse(
        "<h1>Translation Agent API</h1><p>Frontend not built. Run <code>cd web/frontend && npm run build</code></p>"
    )


@app.get("/api/docs-toggle", include_in_schema=False)
async def docs_toggle():
    """Return whether docs are enabled."""
    return {"enabled": True}


def _collect_port_connections(port: int) -> list[str]:
    """Collect active netstat lines for a given port without using shell pipelines."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = result.stdout.splitlines() if result.stdout else []
    except Exception:
        return []

    needle = f":{port}"
    return [line.strip() for line in lines if needle in line]


@app.get("/api/system/connections")
async def connection_status():
    """Return basic connection stats for the API port."""
    try:
        connections = _collect_port_connections(54321)
        return {
            "active_connections": len(connections),
            "connections": connections,
            "status": "healthy" if len(connections) < 10 else "warning",
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get(
    "/{full_path:path}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def spa_fallback(full_path: str):
    """Serve index.html for non-API routes."""
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "Not Found"}, status_code=404)

    index_path = frontend_dist_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return HTMLResponse(
        "<h1>Translation Agent API</h1><p>Frontend not built. Run <code>cd web/frontend && npm run build</code></p>"
    )
