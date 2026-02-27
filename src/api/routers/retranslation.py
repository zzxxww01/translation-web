"""
API Router - 重新翻译相关端点
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ...services.retranslation_service import (
    RetranslationService,
    RetranslationOption,
    RetranslationResult,
    compute_text_diff,
)
from ...llm.gemini import GeminiProvider
from ...core.models import Paragraph

router = APIRouter(prefix="/retranslation", tags=["retranslation"])


# ========== Request/Response Models ==========


class RetranslateRequest(BaseModel):
    """重新翻译请求"""

    project_id: str
    paragraph_id: str
    source_text: str
    current_translation: str
    option: str = "rewrite"  # "rewrite", "concise", "professional"
    custom_instruction: Optional[str] = None
    glossary: Optional[List[Dict[str, Any]]] = None


class RetranslateResponse(BaseModel):
    """重新翻译响应"""

    paragraph_id: str
    original_translation: str
    new_translation: str
    diff_data: Dict[str, Any]
    instruction_used: str


class DiffRequest(BaseModel):
    """计算差异请求"""

    text1: str
    text2: str


class DiffResponse(BaseModel):
    """差异响应"""

    operations: List[Dict[str, str]]
    change_percentage: float


# ========== API Endpoints ==========


@router.post("/retranslate")
async def retranslate_paragraph(request: RetranslateRequest) -> RetranslateResponse:
    """
    重新翻译段落

    提供重写、简洁、专业三种预设选项，支持自定义补充说明
    """
    try:
        # 验证选项
        try:
            option_enum = RetranslationOption(request.option)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid option: {request.option}. Must be one of: rewrite, concise, professional",
            )

        # 创建服务
        llm_provider = GeminiProvider(model_type="reasoning")
        service = RetranslationService(llm_provider)

        # 构建上下文
        context = {}
        if request.glossary:
            context["glossary"] = request.glossary

        # 执行重新翻译
        result = service.retranslate(
            source_text=request.source_text,
            current_translation=request.current_translation,
            option=option_enum,
            custom_instruction=request.custom_instruction,
            context=context,
        )

        return RetranslateResponse(
            paragraph_id=request.paragraph_id,
            original_translation=result.original_translation,
            new_translation=result.new_translation,
            diff_data=result.diff_data,
            instruction_used=result.instruction_used,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compute-diff")
async def compute_diff(request: DiffRequest) -> DiffResponse:
    """
    计算两个文本的差异

    用于前端实时显示差异高亮
    """
    try:
        diff_data = compute_text_diff(request.text1, request.text2)

        return DiffResponse(
            operations=diff_data["operations"],
            change_percentage=diff_data["change_percentage"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options")
async def get_retranslation_options() -> Dict[str, Any]:
    """
    获取所有重新翻译选项及其描述
    """
    return {
        "options": [
            {
                "value": "rewrite",
                "label": "重写（增加流畅性和可读性）",
                "description": "重新组织语言，让译文更自然流畅",
                "is_default": True,
            },
            {
                "value": "concise",
                "label": "更简洁",
                "description": "删除冗余词汇，使表达更精炼",
                "is_default": False,
            },
            {
                "value": "professional",
                "label": "更专业",
                "description": "采用学术化或技术化的语言风格",
                "is_default": False,
            },
        ],
        "supports_custom_instruction": True,
    }
