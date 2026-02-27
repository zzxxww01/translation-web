"""
Conversations Router - 对话管理 API

管理 Slack 对话历史。
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.conversation import ConversationConfig

from ..dependencies import ConversationManagerDep
from ..middleware import NotFoundException, BadRequestException


router = APIRouter(prefix="", tags=["conversations"])


# ============ Models ============


class CreateConversationRequest(BaseModel):
    id: str
    name: str
    style: str = "casual"
    system_prompt: str = ""
    is_pinned: bool = False


class UpdateConversationRequest(BaseModel):
    name: Optional[str] = None
    is_pinned: Optional[bool] = None


class ConversationResponse(BaseModel):
    id: str
    name: str
    style: str
    system_prompt: str = ""
    is_pinned: bool = False
    history_count: int
    created_at: str
    updated_at: str = ""


class AddMessageRequest(BaseModel):
    role: str  # "them" | "me"
    content_en: str
    content_cn: str = ""


class UpdateMessageRequest(BaseModel):
    role: Optional[str] = None
    content_en: Optional[str] = None
    content_cn: Optional[str] = None


def _to_conversation_response(
    config: ConversationConfig,
    history_count: int,
) -> ConversationResponse:
    """Convert conversation config to API response model."""
    return ConversationResponse(
        id=config.id,
        name=config.name,
        style=config.style,
        system_prompt=config.system_prompt,
        is_pinned=config.is_pinned,
        history_count=history_count,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


# ============ API Endpoints ============


@router.get("/conversations")
async def list_conversations(cm: ConversationManagerDep):
    """获取所有对话"""
    configs = cm.list_all()
    return [
        _to_conversation_response(c, cm.get_history_count(c.id))
        for c in configs
    ]


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    cm: ConversationManagerDep,
):
    """创建新对话"""
    existing = cm.get(request.id)
    if existing:
        raise BadRequestException(detail=f"对话 '{request.id}' 已存在")

    config = cm.create(
        request.id,
        request.name,
        request.style,
        system_prompt=request.system_prompt,
        is_pinned=request.is_pinned,
    )
    return _to_conversation_response(config, 0)


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, cm: ConversationManagerDep):
    """获取对话详情（包含历史）"""
    conv = cm.get(conv_id)
    if not conv:
        raise NotFoundException(detail=f"对话 '{conv_id}' 不存在")

    return {
        "id": conv.config.id,
        "name": conv.config.name,
        "style": conv.config.style,
        "system_prompt": conv.config.system_prompt,
        "history": [msg.model_dump() for msg in conv.history],
        "created_at": conv.config.created_at,
    }


@router.put("/conversations/{conv_id}")
async def update_conversation(
    conv_id: str,
    request: UpdateConversationRequest,
    cm: ConversationManagerDep,
):
    """更新对话（重命名/置顶）"""
    config = cm.get(conv_id)
    if not config:
        raise NotFoundException(detail=f"对话 '{conv_id}' 不存在")

    updated = cm.update_config(
        conv_id,
        **{
            k: v
            for k, v in {"name": request.name, "is_pinned": request.is_pinned}.items()
            if v is not None
        },
    )
    if not updated:
        raise BadRequestException(detail="更新失败")

    return _to_conversation_response(updated, cm.get_history_count(conv_id))


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, cm: ConversationManagerDep):
    """删除对话"""
    if cm.delete(conv_id):
        return {"message": f"对话 '{conv_id}' 已删除"}
    raise NotFoundException(detail=f"对话 '{conv_id}' 不存在")


@router.post("/conversations/{conv_id}/messages")
async def add_message(
    conv_id: str,
    request: AddMessageRequest,
    cm: ConversationManagerDep,
):
    """添加消息到对话历史"""
    msg = cm.add_message(conv_id, request.role, request.content_en, request.content_cn)
    if not msg:
        raise NotFoundException(detail=f"对话 '{conv_id}' 不存在")
    return msg.model_dump()


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, cm: ConversationManagerDep):
    """获取对话历史"""
    history = cm.get_history(conv_id)
    return [msg.model_dump() for msg in history]


@router.put("/conversations/{conv_id}/messages/{index}")
async def update_message(
    conv_id: str,
    index: int,
    request: UpdateMessageRequest,
    cm: ConversationManagerDep,
):
    """更新消息"""
    msg = cm.update_message(
        conv_id,
        index,
        role=request.role,
        content_en=request.content_en,
        content_cn=request.content_cn,
    )
    if not msg:
        raise NotFoundException(detail="消息不存在或更新失败")
    return msg.model_dump()
