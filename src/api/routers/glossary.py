"""
全局术语库路由
提供术语库的增删改查功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from src.core.glossary import GlossaryManager
from src.core.models import GlossaryTerm, TranslationStrategy

router = APIRouter(prefix="/glossary", tags=["术语库"])

# 全局术语库管理器
_gm = GlossaryManager(global_path="glossary", projects_path="projects")
DEFAULT_DOMAIN = "semiconductor"


class TermRequest(BaseModel):
    """术语请求"""
    original: str
    translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None


class TermResponse(BaseModel):
    """术语响应"""
    original: str
    translation: Optional[str] = None
    strategy: str
    note: Optional[str] = None


class GlossaryResponse(BaseModel):
    """术语库响应"""
    version: int
    terms: List[TermResponse]


@router.get("", response_model=GlossaryResponse)
async def get_global_glossary():
    """获取全局术语库"""
    glossary = _gm.load_global(DEFAULT_DOMAIN)
    return GlossaryResponse(
        version=glossary.version,
        terms=[
            TermResponse(
                original=term.original,
                translation=term.translation,
                strategy=term.strategy.value,
                note=term.note
            )
            for term in glossary.terms
        ]
    )


@router.post("", response_model=dict)
async def add_global_term(request: TermRequest):
    """添加全局术语"""
    glossary = _gm.load_global(DEFAULT_DOMAIN)

    # 检查是否已存在
    existing = glossary.get_term(request.original)
    if existing:
        raise HTTPException(status_code=400, detail=f"术语 '{request.original}' 已存在")

    # 添加术语
    term = GlossaryTerm(
        original=request.original,
        translation=request.translation,
        strategy=request.strategy,
        note=request.note
    )
    glossary.add_term(term)
    _gm.save_global(glossary, DEFAULT_DOMAIN)

    return {
        "message": "术语添加成功",
        "term": {
            "original": term.original,
            "translation": term.translation,
            "strategy": term.strategy.value,
            "note": term.note
        }
    }


@router.put("/terms/{original}")
async def update_global_term(
    original: str,
    translation: Optional[str] = Query(None),
    strategy: Optional[TranslationStrategy] = Query(None),
    note: Optional[str] = Query(None)
):
    """更新全局术语"""
    glossary = _gm.load_global(DEFAULT_DOMAIN)

    # 查找术语
    existing = glossary.get_term(original)
    if not existing:
        raise HTTPException(status_code=404, detail=f"术语 '{original}' 不存在")

    # 更新字段
    if translation is not None:
        existing.translation = translation
    if strategy is not None:
        existing.strategy = strategy
    if note is not None:
        existing.note = note

    _gm.save_global(glossary, DEFAULT_DOMAIN)

    return {
        "message": "术语更新成功",
        "term": {
            "original": existing.original,
            "translation": existing.translation,
            "strategy": existing.strategy.value,
            "note": existing.note
        }
    }


@router.delete("/terms/{original}")
async def delete_global_term(original: str):
    """删除全局术语"""
    glossary = _gm.load_global(DEFAULT_DOMAIN)

    # 查找术语
    existing = glossary.get_term(original)
    if not existing:
        raise HTTPException(status_code=404, detail=f"术语 '{original}' 不存在")

    # 删除术语
    glossary.terms = [t for t in glossary.terms if t.original != original]
    _gm.save_global(glossary, DEFAULT_DOMAIN)

    return {
        "message": "术语删除成功",
        "original": original
    }
