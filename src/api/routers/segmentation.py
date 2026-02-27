"""
Segmentation strategy endpoints.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ...core.models import Section
from ...core.segmentation import SegmentationStrategy
from ..middleware import BadRequestException


router = APIRouter(prefix="/segmentation", tags=["segmentation"])


class SegmentationConfig(BaseModel):
    """分段配置"""

    translation_block_size: int = 2000
    confirmation_min_size: int = 150
    confirmation_max_size: int = 400


class ConfirmationUnitResponse(BaseModel):
    """确认单元响应"""

    id: str
    merged_paragraph_ids: List[str]
    source: str
    translation: str
    is_merged: bool


class CreateConfirmationUnitsRequest(BaseModel):
    """创建确认单元请求"""

    project_id: str
    sections: List[Dict[str, Any]]
    config: Optional[SegmentationConfig] = None


class CreateConfirmationUnitsResponse(BaseModel):
    """创建确认单元响应"""

    confirmation_units: List[ConfirmationUnitResponse]
    stats: Dict[str, int]


@router.post("/confirmation-units")
async def create_confirmation_units(
    request: CreateConfirmationUnitsRequest,
) -> CreateConfirmationUnitsResponse:
    """
    创建确认单元。

    将已翻译段落按策略合并为确认单元，供用户逐个确认。
    """
    try:
        config = request.config or SegmentationConfig()
        strategy = SegmentationStrategy(
            translation_block_size=config.translation_block_size,
            confirmation_min_size=config.confirmation_min_size,
            confirmation_max_size=config.confirmation_max_size,
        )
        sections = [Section(**item) for item in request.sections]
    except Exception as e:
        raise BadRequestException(detail=f"参数错误: {e}")

    all_paragraphs = [para for section in sections for para in section.paragraphs]
    units = strategy.create_confirmation_units(all_paragraphs)

    unit_responses = [
        ConfirmationUnitResponse(
            id=unit.id,
            merged_paragraph_ids=unit.merged_paragraph_ids,
            source=unit.source,
            translation=unit.translation,
            is_merged=unit.is_merged,
        )
        for unit in units
    ]

    stats = {
        "total_units": len(units),
        "merged_units": sum(1 for unit in units if unit.is_merged),
        "total_paragraphs": sum(len(unit.merged_paragraph_ids) for unit in units),
    }
    return CreateConfirmationUnitsResponse(
        confirmation_units=unit_responses,
        stats=stats,
    )


@router.get("/strategy/default")
async def get_default_strategy() -> SegmentationConfig:
    """获取默认分段策略配置。"""
    return SegmentationConfig()


@router.put("/strategy/test")
async def test_segmentation_strategy(
    config: SegmentationConfig,
    sample_text: str,
) -> Dict[str, Any]:
    """测试分段策略，返回粗略分段预估。"""
    if not sample_text.strip():
        raise BadRequestException(detail="sample_text 不能为空")

    block_size = max(config.translation_block_size, 1)
    estimated_blocks = (len(sample_text) + block_size - 1) // block_size
    return {
        "config": config.model_dump(),
        "sample_length": len(sample_text),
        "estimated_blocks": estimated_blocks,
        "note": "这是按字符长度的粗略估算，实际分段以段落边界为准。",
    }
