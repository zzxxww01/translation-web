"""
Project and section management endpoints.
"""

import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.core.models import ElementType
from src.core.project import ProjectManager

from ..dependencies import ProjectManagerDep, get_project_manager
from ..middleware import BadRequestException, NotFoundException
from .projects_models import CreateProjectRequest, ProjectResponse


router = APIRouter()
SUPPORTED_SOURCE_EXTENSIONS = {".html", ".htm", ".md", ".markdown"}
HTML_SOURCE_EXTENSIONS = {".html", ".htm"}


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
    if _is_external_asset_url(value):
        return value

    normalized = value.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    if not normalized:
        return None
    return f"/projects/{project_id}/{normalized}"


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
    projects = pm.list_all()
    return [_build_project_response(p) for p in projects]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    pm: ProjectManagerDep,
):
    try:
        meta = pm.create(request.name, request.html_path)
        return _build_project_response(meta)
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except FileNotFoundError as e:
        raise NotFoundException(detail=str(e))


@router.post("/projects/upload", response_model=ProjectResponse)
async def upload_project(
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

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            safe_source_name = Path(file.filename).name
            temp_source_path = temp_dir_path / safe_source_name

            with open(temp_source_path, "wb") as out_file:
                shutil.copyfileobj(file.file, out_file)

            # Keep existing HTML assets upload behavior unchanged.
            if assets and is_html_source:
                for asset in assets:
                    if not asset.filename:
                        continue
                    dest_path = _safe_asset_path(temp_dir_path, asset.filename)
                    if not dest_path:
                        continue
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_path, "wb") as out_file:
                        shutil.copyfileobj(asset.file, out_file)

            meta = pm.create(name, str(temp_source_path))

        return _build_project_response(meta)
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except BadRequestException:
        raise
    except Exception as e:
        raise BadRequestException(detail=f"Upload failed: {str(e)}")
    finally:
        file.file.close()
        if assets:
            for asset in assets:
                asset.file.close()


@router.get("/projects/{project_id}")
async def get_project(project_id: str, pm: ProjectManagerDep):
    try:
        meta = pm.get(project_id)
        sections = pm.get_sections(project_id)
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


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, pm: ProjectManagerDep):
    try:
        pm.delete(project_id)
        return {"message": "Project deleted"}
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.post("/projects/{project_id}/export")
async def export_project(
    project_id: str,
    pm: ProjectManagerDep,
    include_source: bool = False,
    format: str = "zh",
):
    try:
        content = pm.export(project_id, include_source=include_source, format=format)
        filename = pm.get_export_filename(project_id, format=format)
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
    try:
        sections = pm.get_sections(project_id)
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
    def _normalize_image_source(paragraph) -> str:
        if paragraph.element_type != ElementType.IMAGE:
            return paragraph.source
        return _project_asset_url(project_id, paragraph.source) or paragraph.source

    def _normalize_image_html(paragraph) -> Optional[str]:
        if not paragraph.source_html:
            return paragraph.source_html
        html = paragraph.source_html
        html = html.replace("src=\"./images/", f"src=\"/projects/{project_id}/images/")
        html = html.replace("src=\"images/", f"src=\"/projects/{project_id}/images/")
        html = html.replace("src=\"./", f"src=\"/projects/{project_id}/")
        html = html.replace("href=\"./", f"href=\"/projects/{project_id}/")
        return html

    try:
        section = pm.get_section(project_id, section_id)
        if not section:
            try:
                pm.get(project_id)
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
