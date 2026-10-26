"""文章工作台：三栏对照（英文 / 译本 1 / 译本 2）所需的数据、自动保存、人工改动、译本 2 的创建与导入。

译本 2 是同源孪生项目（见 src/services/article_variants.py），段落 id 与主项目一致。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src.api.utils.concurrency import run_blocking
from src.core.models import ElementType, Section
from src.services import article_edits, article_variants

from ..dependencies import ProjectManagerDep, TranslationStatusServiceDep
from ..middleware import BadRequestException, ConflictException, NotFoundException, ServiceUnavailableException
from ..middleware.rate_limit import limiter
from .projects_management import _project_asset_url
from .translate_utils import validate_path_component

router = APIRouter()

MAX_MARKDOWN_CHARS = 2_000_000


class SaveTextRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=200)  # 主项目或孪生项目 id
    section_id: str = Field(..., min_length=1, max_length=200)
    paragraph_id: Optional[str] = Field(None, max_length=200)  # 不填 = 章节标题
    text: str = Field(..., max_length=50_000)


class CreateVariantRequest(BaseModel):
    kind: Literal["model"] = "model"
    model: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=40)


class ImportClaudeRequest(BaseModel):
    run_id: Optional[str] = Field(None, max_length=100)
    agent: Literal["claude", "codex", "antigravity"] = "claude"  # 跑 four-step-translate 的 harness
    zh_markdown: str = Field(..., min_length=1, max_length=MAX_MARKDOWN_CHARS)
    en_markdown: str = Field(..., min_length=1, max_length=MAX_MARKDOWN_CHARS)


class ClaudeRunRequest(BaseModel):
    run_id: Optional[str] = Field(None, max_length=100)


class ReadingMarkRequest(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=400)  # 行的 key；不填 = 拿掉书签


def _check_id(project_id: str) -> None:
    if not validate_path_component(project_id):
        raise NotFoundException(detail="Project not found")


def _check_target(pm, project_id: str, target: str) -> None:
    """target 必须是这篇文章本身或它的孪生项目。"""
    _check_id(target)
    if target != project_id and pm.get(target).variant_of != project_id:
        raise BadRequestException(detail="这个译本不属于当前文章")


def _status_summary(progress: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "active": bool(progress.get("active_run_id")),
        "run_id": progress.get("active_run_id"),
        "status": progress.get("status"),
        "current_step": progress.get("current_step"),
        "translated": progress.get("translated_paragraphs"),
        "total": progress.get("total_paragraphs"),
        "error": progress.get("error") or progress.get("last_error"),
    }


def _mark_path(pm, project_id: str):
    # 不放 meta.json：后台翻译拿着旧快照存 meta 时会把它冲掉
    return pm._project_dir(project_id) / "artifacts" / "reading-mark.json"


def _read_mark(pm, project_id: str, row_keys: set[str]) -> Optional[Dict[str, str]]:
    try:
        record = pm._read_json(_mark_path(pm, project_id))
        if not isinstance(record, dict):
            return None
        key, at = record.get("key"), record.get("at")
        if not isinstance(key, str) or key not in row_keys or not isinstance(at, str):
            return None
        datetime.fromisoformat(at)
        return {"key": key, "at": at}
    except (OSError, ValueError):
        # 书签是可选状态，损坏、不可读或失效时仍然允许打开文章；不改动原文件。
        return None


def _paragraph_text(paragraph) -> Optional[str]:
    if paragraph.element_type == ElementType.IMAGE:
        return None
    return paragraph.best_translation_text() or None


def _build_rows(project_id: str, sections: List[Section], variants: Dict[str, List[Section]]) -> List[Dict[str, Any]]:
    variant_index = {
        vid: {s.section_id: s for s in v_sections} for vid, v_sections in variants.items()
    }
    rows: List[Dict[str, Any]] = []
    for section in sections:
        twins = {vid: index.get(section.section_id) for vid, index in variant_index.items()}
        if section.title and not section.synthetic:
            rows.append({
                "key": f"section:{section.section_id}",
                "kind": "section",
                "section_id": section.section_id,
                "paragraph_id": None,
                "source": section.title,
                "web": section.title_translation,
                "alt": {vid: twin.title_translation if twin else None for vid, twin in twins.items()},
            })
        for paragraph in section.paragraphs:
            alt: Dict[str, Optional[str]] = {}
            for vid, twin in twins.items():
                match = next((p for p in twin.paragraphs if p.id == paragraph.id), None) if twin else None
                alt[vid] = _paragraph_text(match) if match else None
            is_image = paragraph.element_type == ElementType.IMAGE
            rows.append({
                "key": f"{section.section_id}/{paragraph.id}",  # 段落 id 只在章节内唯一
                "kind": paragraph.element_type.value,
                "section_id": section.section_id,
                "paragraph_id": paragraph.id,
                "heading_level": paragraph.heading_level,
                "is_metadata": paragraph.is_metadata,
                "block": paragraph.parent_block_id,  # 导入时拆开的长段，几行同属原文一段
                "source": paragraph.source,
                "image": _project_asset_url(project_id, paragraph.source) if is_image else None,
                "web": _paragraph_text(paragraph),
                "alt": alt,
            })
    return rows


@router.get("/projects/{project_id}/workbench")
async def get_workbench(project_id: str, pm: ProjectManagerDep, status_service: TranslationStatusServiceDep):
    _check_id(project_id)

    def load():
        meta = pm.get(project_id)
        if meta.variant_of:
            raise BadRequestException(detail="这是译本 2 的孪生项目，请打开它的主项目", error_code="IS_VARIANT")
        sections = pm.get_sections(project_id)
        variant_metas = [pm.get(v.id) for v in article_variants.list_variants(pm, project_id)]
        variant_sections = {v.id: pm.get_sections(v.id) for v in variant_metas}
        imports = {v.id: article_variants.read_import_record(pm, v.id) for v in variant_metas if v.variant_kind == "claude"}
        rows = _build_rows(project_id, sections, variant_sections)
        mark = _read_mark(pm, project_id, {row["key"] for row in rows})
        return meta, variant_metas, imports, rows, mark

    try:
        meta, variant_metas, imports, rows, mark = await run_blocking(load)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")

    main_status = _status_summary(await status_service.get_translation_progress(project_id))
    variants = []
    for variant in variant_metas:
        variants.append({
            "id": variant.id,
            "kind": variant.variant_kind,
            "label": variant.variant_label or "译本 2",
            "title_translation": variant.title_translation,
            "progress": {"total": variant.progress.total_paragraphs, "approved": variant.progress.approved},
            "status": _status_summary(await status_service.get_translation_progress(variant.id)),
            "import": imports.get(variant.id),
        })
    original_url = meta.metadata.original_url if meta.metadata else None
    return {
        "project": {
            "id": meta.id,
            "title": meta.title,
            "title_translation": meta.title_translation,
            "original_url": original_url,
            "created_at": meta.created_at.isoformat(),
            "claude_run_id": meta.claude_run_id,
            "progress": {"total": meta.progress.total_paragraphs, "approved": meta.progress.approved},
            "status": main_status,
        },
        "variants": variants,
        "rows": rows,
        "reading_mark": mark,
    }


@router.put("/projects/{project_id}/workbench/reading-mark")
async def set_reading_mark(project_id: str, body: ReadingMarkRequest, pm: ProjectManagerDep):
    """「看到这里」书签（一篇一个，存在服务器上，换设备也在）。"""
    _check_id(project_id)

    def save():
        meta = pm.get(project_id)  # 文章不存在时抛 FileNotFoundError
        if meta.variant_of:
            raise BadRequestException(detail="请在主项目上设置阅读标记", error_code="IS_VARIANT")
        path = _mark_path(pm, project_id)
        if body.key is None:
            path.unlink(missing_ok=True)
            return None
        rows = _build_rows(project_id, pm.get_sections(project_id), {})
        if body.key not in {row["key"] for row in rows}:
            raise BadRequestException(detail="阅读标记对应的段落不存在，请刷新文章后重试")
        record = {"key": body.key, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        # ProjectManager 原子写入，失败时保留已有书签。
        pm._write_json(path, record)
        return record

    try:
        mark = await run_blocking(save)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except OSError as error:
        raise ServiceUnavailableException(detail="阅读标记保存失败，请重试") from error
    return {"ok": True, "reading_mark": mark}


@router.put("/projects/{project_id}/workbench/text")
@limiter.limit("240/minute")
async def save_text(request: Request, project_id: str, body: SaveTextRequest, pm: ProjectManagerDep):
    """自动保存一段（或章节标题）的译文。编辑时保存很频繁，所以不走 20 次/分钟的确认接口。"""
    _check_id(project_id)
    text = body.text.strip()
    if not text:
        raise BadRequestException(detail="译文不能为空")

    def save():
        _check_target(pm, project_id, body.target)
        if body.paragraph_id is None:
            section = pm.get_section(body.target, body.section_id)
            if section is None:
                raise FileNotFoundError(body.section_id)
            for _ in range(3):
                _, saved = pm.update_section_title_translation_locked(
                    body.target, body.section_id, text, expected_title_translation=section.title_translation)
                if saved:
                    return
                section = pm.get_section(body.target, body.section_id)
            raise ConflictException(detail="章节标题正在被别处修改，请重试")
        pm.confirm_paragraph(body.target, body.section_id, body.paragraph_id, text)

    try:
        await run_blocking(save)
    except FileNotFoundError:
        raise NotFoundException(detail="Paragraph not found")
    return {"ok": True}


@router.get("/projects/{project_id}/workbench/changes")
async def get_changes(project_id: str, target: str, pm: ProjectManagerDep):
    """这个版本里人工改过的段落（初稿 → 现在），带逐字对比。"""
    _check_id(project_id)

    def load():
        _check_target(pm, project_id, target)
        return article_edits.with_segments(article_edits.collect_changes(pm.get_sections(target)))

    try:
        return await run_blocking(load)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")


@router.get("/workbench/human-edits.jsonl")
async def export_human_edits(pm: ProjectManagerDep):
    """所有文章、所有版本的人工改动（机翻初稿 → 现在），一行一段，用来批量分析人工改了什么。"""
    content = await run_blocking(lambda: "".join(article_edits.export_all(pm)))
    stamp = datetime.now().strftime("%Y%m%d")
    return Response(
        content,
        media_type="application/x-ndjson; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="human-edits-{stamp}.jsonl"'},
    )


@router.post("/projects/{project_id}/variants")
@limiter.limit("10/minute")
async def create_model_variant(request: Request, project_id: str, body: CreateVariantRequest, pm: ProjectManagerDep):
    """建一个孪生项目，之后由前端用指定模型启动它的后台四步法（translation-workflow）。"""
    _check_id(project_id)
    try:
        variant_id = await run_blocking(
            article_variants.create_variant, pm, project_id,
            kind="model", label=body.label, suffix=body.label, replace=False)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except ValueError as error:
        raise BadRequestException(detail=str(error))
    return {"variant_id": variant_id}


@router.post("/projects/{project_id}/variants/claude")
@limiter.limit("10/minute")
async def import_claude_variant(request: Request, project_id: str, body: ImportClaudeRequest, pm: ProjectManagerDep):
    _check_id(project_id)
    try:
        result = await run_blocking(
            article_variants.import_claude_translation, pm, project_id,
            zh_markdown=body.zh_markdown, en_markdown=body.en_markdown, run_id=body.run_id, agent=body.agent)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except ValueError as error:
        raise BadRequestException(detail=str(error))
    return result


@router.put("/projects/{project_id}/claude-run")
async def set_claude_run(project_id: str, body: ClaudeRunRequest, pm: ProjectManagerDep):
    _check_id(project_id)
    try:
        await run_blocking(lambda: pm.merge_meta_fields(project_id, fields={"claude_run_id": body.run_id}))
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    return {"ok": True, "claude_run_id": body.run_id}


@router.get("/projects/{project_id}/source-html")
async def get_source_html(project_id: str, pm: ProjectManagerDep):
    """原文 HTML，前端拿去交给 Claude（four-step-translate 只接 HTML）。"""
    _check_id(project_id)
    path = pm._project_dir(project_id) / "source.html"
    if not path.is_file():
        raise NotFoundException(detail="这个项目没有原文 HTML（可能是用 Markdown 建的）")
    return FileResponse(path, media_type="text/html", filename=f"{project_id}.html")
