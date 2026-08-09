"""
Project and section management endpoints.
"""

import asyncio
import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, unquote, urlsplit

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from src.core.models import ElementType
from src.core.image_assets import (
    BROWSER_IMAGE_EXTENSIONS,
    parse_markdown_image_reference,
)
from src.core.project import ProjectManager
from src.api.utils.concurrency import run_blocking

from ..dependencies import ProjectManagerDep, get_project_manager
from ..middleware import BadRequestException, ConflictException, NotFoundException
from ..middleware.rate_limit import limiter
from .projects_models import CreateProjectRequest, ProjectResponse
from .translate_utils import validate_path_component
from src.services.translation_run_registry import translation_run_registry


router = APIRouter()
SUPPORTED_SOURCE_EXTENSIONS = {".html", ".htm", ".md", ".markdown"}
HTML_SOURCE_EXTENSIONS = {".html", ".htm"}
PROJECT_ASSET_EXTENSIONS = BROWSER_IMAGE_EXTENSIONS


def _is_external_asset_url(path: str) -> bool:
    value = path.strip()
    if not value:
        return False
    if value.startswith("//"):
        return True
    if value.startswith(("data:", "blob:")):
        return True
    parsed = urlsplit(value)
    return bool(parsed.scheme and parsed.netloc)


def _project_asset_url(project_id: str, path: Optional[str]) -> Optional[str]:
    if not path:
        return path

    value = path.strip()
    if not value:
        return value
    markdown_reference = parse_markdown_image_reference(value)
    if markdown_reference is not None:
        value = markdown_reference.source
    if _is_external_asset_url(value):
        return value

    local_url = urlsplit(value)
    normalized = unquote(local_url.path).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    if not normalized or any(part in {"", ".", ".."} for part in normalized.split("/")):
        return None
    encoded_path = quote(normalized, safe="/")
    return f"/api/projects/{project_id}/assets/{encoded_path}"


_IMAGE_SRC_PATTERN = re.compile(
    r"(?P<prefix>\bsrc\s*=\s*)(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)


def _rewrite_project_image_html(project_id: str, html: Optional[str]) -> Optional[str]:
    if not html:
        return html

    def replace(match: re.Match[str]) -> str:
        source = match.group("url")
        normalized = _project_asset_url(project_id, source)
        if not normalized:
            return match.group(0)
        quote_char = match.group("quote")
        return f"{match.group('prefix')}{quote_char}{normalized}{quote_char}"

    return _IMAGE_SRC_PATTERN.sub(replace, html)


def _build_project_response(meta) -> ProjectResponse:
    return ProjectResponse(
        id=meta.id,
        title=meta.title,
        status=meta.status.value,
        progress={
            "total": meta.progress.total_paragraphs,
            "approved": meta.progress.approved,
            "percent": meta.progress.progress_percent,
        },
        created_at=meta.created_at.isoformat(),
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(pm: ProjectManagerDep):
    # Read only list fields; full metadata can include megabytes of legacy
    # section snapshots and total=0 must not trigger a sections scan here.
    projects = await asyncio.to_thread(pm.list_summaries)
    return [_build_project_response(p) for p in projects]


@router.post("/projects", response_model=ProjectResponse)
@limiter.limit("30/minute")
async def create_project(
    request: Request,
    body: CreateProjectRequest,
    pm: ProjectManagerDep,
):
    try:
        meta = await asyncio.to_thread(pm.create, body.name, body.html_path)
        return _build_project_response(meta)
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))


@router.post("/projects/upload", response_model=ProjectResponse)
@limiter.limit("30/minute")
async def upload_project(
    request: Request,
    pm: ProjectManager = Depends(get_project_manager),
    name: str = Form(...),
    file: UploadFile = File(...),
    assets: Optional[List[UploadFile]] = File(None),
):
    def _safe_asset_path(base_dir: Path, filename: str) -> Optional[Path]:
        if not filename:
            return None
        normalized = filename.replace("\\", "/").lstrip("/")
        if re.match(r"^[A-Za-z]:", normalized):
            normalized = normalized.split(":", 1)[1].lstrip("/\\")
        if not normalized:
            return None
        rel_path = Path(normalized)
        if any(part == ".." for part in rel_path.parts):
            return None
        dest_path = (base_dir / rel_path).resolve()
        base_resolved = base_dir.resolve()
        if not str(dest_path).startswith(str(base_resolved)):
            return None
        return dest_path

    try:
        if not file.filename:
            raise BadRequestException(detail="Please upload a source file")

        source_suffix = Path(file.filename).suffix.lower()
        if source_suffix not in SUPPORTED_SOURCE_EXTENSIONS:
            raise BadRequestException(detail="Please upload an HTML or Markdown file")
        is_html_source = source_suffix in HTML_SOURCE_EXTENSIONS

        def stage_and_create():
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                temp_source_path = temp_dir_path / Path(file.filename).name

                with open(temp_source_path, "wb") as out_file:
                    shutil.copyfileobj(file.file, out_file)

                if assets and is_html_source:
                    for asset in assets:
                        if not asset.filename:
                            continue
                        dest_path = _safe_asset_path(
                            temp_dir_path,
                            asset.filename,
                        )
                        if not dest_path:
                            continue
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(dest_path, "wb") as out_file:
                            shutil.copyfileobj(asset.file, out_file)

                return pm.create(name, str(temp_source_path))

        # Staging, conversion, section writes, and temporary cleanup are all
        # blocking work and must stay off the FastAPI event loop.
        meta = await run_blocking(stage_and_create)

        return _build_project_response(meta)
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except BadRequestException:
        raise
    except Exception as e:
        import os
        import logging
        logging.getLogger(__name__).error(f"Upload failed: {e}")
        detail = (
            f"Upload failed: {e}"
            if os.getenv("DEBUG") == "true"
            else "Upload failed. Please try again or contact support."
        )
        raise BadRequestException(detail=detail)
    finally:
        await file.close()
        if assets:
            await asyncio.gather(*(asset.close() for asset in assets))


@router.get("/projects/{project_id}")
async def get_project(project_id: str, pm: ProjectManagerDep):
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    try:
        meta, sections = await run_blocking(
            lambda: (pm.get(project_id), pm.get_sections(project_id))
        )
        return {
            "id": meta.id,
            "title": meta.title,
            "status": meta.status.value,
            "progress": {
                "total_sections": meta.progress.total_sections,
                "total_paragraphs": meta.progress.total_paragraphs,
                "approved": meta.progress.approved,
                "percent": meta.progress.progress_percent,
            },
            "created_at": meta.created_at.isoformat(),
            "sections": [
                {
                    "section_id": s.section_id,
                    "title": s.title,
                    "title_translation": s.title_translation,
                    "total_paragraphs": s.total_paragraphs,
                    "approved_count": s.approved_count,
                    "is_complete": s.is_complete,
                }
                for s in sections
            ],
        }
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get(
    "/projects/{project_id}/assets/{asset_path:path}",
    include_in_schema=False,
)
async def get_project_asset(
    project_id: str,
    asset_path: str,
    pm: ProjectManagerDep,
):
    """Serve only browser-safe project image assets through the public API."""
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project asset not found")
    if Path(asset_path).suffix.lower() not in PROJECT_ASSET_EXTENSIONS:
        raise NotFoundException(detail="Project asset not found")

    try:
        resolved = await run_blocking(
            pm.resolve_project_asset,
            project_id,
            asset_path,
        )
    except (FileNotFoundError, ValueError, OSError):
        raise NotFoundException(detail="Project asset not found")

    headers = {
        "Cache-Control": "public, max-age=3600",
        "Cross-Origin-Resource-Policy": "same-origin",
        "X-Content-Type-Options": "nosniff",
    }
    if resolved.suffix.lower() == ".svg":
        headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        )
    return FileResponse(resolved, headers=headers)


@router.delete("/projects/{project_id}")
@limiter.limit("30/minute")
async def delete_project(request: Request, project_id: str, pm: ProjectManagerDep):
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    active_run = translation_run_registry.get_active_run(project_id)
    if active_run is not None:
        raise ConflictException(
            detail=(
                "Project has an active translation; cancel it before deleting "
                f"(run_id={active_run.run_id or 'starting'})"
            ),
            error_code="PROJECT_TRANSLATION_ACTIVE",
        )
    try:
        await run_blocking(pm.delete, project_id)
        return {"message": "Project deleted"}
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/export")
@limiter.limit("30/minute")
async def export_project(
    request: Request,
    project_id: str,
    pm: ProjectManagerDep,
    include_source: bool = False,
    format: str = "zh",
):
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    try:
        content, filename = await run_blocking(
            lambda: (
                pm.export(
                    project_id,
                    include_source=include_source,
                    format=format,
                ),
                pm.get_export_filename(project_id, format=format),
            )
        )
        return {
            "content": content,
            "path": f"projects/{project_id}/{filename}",
            "filename": filename,
            "format": format,
        }
    except ValueError as error:
        raise BadRequestException(detail=str(error))
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/projects/{project_id}/sections")
async def get_sections(project_id: str, pm: ProjectManagerDep):
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")
    try:
        sections = await run_blocking(pm.get_sections, project_id)
        return [
            {
                "section_id": s.section_id,
                "title": s.title,
                "title_translation": s.title_translation,
                "total_paragraphs": s.total_paragraphs,
                "approved_count": s.approved_count,
                "is_complete": s.is_complete,
            }
            for s in sections
        ]
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/projects/{project_id}/sections/{section_id}")
async def get_section(project_id: str, section_id: str, pm: ProjectManagerDep):
    # section_id 同样参与拼路径,漏校验即可通过 ..%5c 穿越读取任意 meta.json(审计 BE10)
    if not validate_path_component(project_id) or not validate_path_component(section_id):
        raise NotFoundException(detail="Project not found")

    def _normalize_image_source(paragraph) -> str:
        if paragraph.element_type != ElementType.IMAGE:
            return paragraph.source
        return _project_asset_url(project_id, paragraph.source) or paragraph.source

    def _normalize_image_html(paragraph) -> Optional[str]:
        return _rewrite_project_image_html(project_id, paragraph.source_html)

    try:
        section = await run_blocking(pm.get_section, project_id, section_id)
        if not section:
            try:
                await run_blocking(pm.get, project_id)
                raise NotFoundException(
                    detail=(
                        f"Section '{section_id}' not found in project '{project_id}'. "
                        "The section file may be missing or corrupted."
                    )
                )
            except FileNotFoundError:
                raise

        return {
            "section_id": section.section_id,
            "title": section.title,
            "title_translation": section.title_translation,
            "paragraphs": [
                {
                    "id": p.id,
                    "index": p.index,
                    "source": _normalize_image_source(p),
                    "source_html": _normalize_image_html(p),
                    "translation": p.best_translation_text() or None,
                    "status": p.status.value,
                    "confirmed": p.confirmed,
                    "element_type": p.element_type.value,
                    "parent_block_id": p.parent_block_id,
                    "format_recovery_status": p.format_recovery_status,
                    "format_errors": p.format_errors,
                }
                for p in section.paragraphs
            ],
        }
    except NotFoundException:
        raise
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
