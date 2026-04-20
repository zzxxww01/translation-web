"""
微信公众号格式化 API 路由
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator
import asyncio
from functools import partial

from ..middleware import BadRequestException, ServiceUnavailableException
from ..middleware.rate_limit import limiter
from src.services.wechat_formatter import WechatFormatter
from src.services.wechat_themes import list_themes


router = APIRouter()
logger = logging.getLogger(__name__)

# 允许的主题白名单
ALLOWED_THEMES = {"default", "grace", "simple"}

# 内容大小限制（10MB）
MAX_MARKDOWN_SIZE = 10 * 1024 * 1024


class WechatFormatRequest(BaseModel):
    """微信格式化请求"""

    markdown: str = Field(..., max_length=MAX_MARKDOWN_SIZE)
    theme: str = "default"
    upload_images: bool = False
    image_to_base64: bool = False

    @field_validator('markdown')
    @classmethod
    def validate_markdown_size(cls, v: str) -> str:
        if len(v.encode('utf-8')) > MAX_MARKDOWN_SIZE:
            raise ValueError(f"Markdown content exceeds {MAX_MARKDOWN_SIZE} bytes")
        if not v.strip():
            raise ValueError("Markdown content cannot be empty")
        return v

    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if v not in ALLOWED_THEMES:
            raise ValueError(f"Invalid theme. Allowed: {', '.join(sorted(ALLOWED_THEMES))}")
        return v


class WechatFormatResponse(BaseModel):
    """微信格式化响应"""

    html: str
    css: str
    image_count: int
    image_urls: list[str]


class ThemeInfo(BaseModel):
    """主题信息"""

    id: str
    name: str
    description: str


class WechatThemesResponse(BaseModel):
    """主题列表响应"""

    themes: list[ThemeInfo]


@router.post("/wechat/format", response_model=WechatFormatResponse)
@limiter.limit("100/minute")
async def format_for_wechat(request: Request, body: WechatFormatRequest):
    """
    将 Markdown 转换为微信公众号格式

    - **markdown**: Markdown 文本（最大 10MB）
    - **theme**: 主题名称（default, grace, simple）
    - **upload_images**: 是否上传图片到图床
    - **image_to_base64**: 是否将图片转为 Base64

    注意：建议在生产环境配置速率限制中间件
    """
    if not body.markdown.strip():
        raise BadRequestException(detail="Markdown content cannot be empty")

    try:
        formatter = WechatFormatter()

        # 在线程池中执行阻塞操作，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                formatter.format,
                markdown=body.markdown,
                theme=body.theme,
                upload_images=body.upload_images,
                image_to_base64=body.image_to_base64,
            )
        )

        return WechatFormatResponse(
            html=result["html"],
            css=result["css"],
            image_count=result["image_count"],
            image_urls=result["image_urls"],
        )

    except ImportError as e:
        logger.error(f"Missing dependency: {e}", exc_info=True)
        raise ServiceUnavailableException(
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Format failed: {e}", exc_info=True)
        raise ServiceUnavailableException(detail="Failed to format markdown")


@router.get("/wechat/themes", response_model=WechatThemesResponse)
async def get_wechat_themes():
    """获取所有可用主题"""
    # 主题元数据映射
    theme_metadata = {
        "default": {"name": "经典", "description": "专业稳重的经典风格"},
        "grace": {"name": "优雅", "description": "精致美观的优雅风格"},
        "simple": {"name": "简洁", "description": "清爽简约的极简风格"},
    }

    # 直接扫描文件系统
    from pathlib import Path
    themes_dir = Path(__file__).parent.parent.parent / "prompts" / "wechat_themes"
    theme_files = [f.stem for f in themes_dir.glob("*.css") if f.stem != "base"]

    # 构建主题对象列表
    themes = [
        ThemeInfo(
            id=theme_id,
            name=theme_metadata.get(theme_id, {}).get("name", theme_id),
            description=theme_metadata.get(theme_id, {}).get("description", ""),
        )
        for theme_id in sorted(theme_files)
    ]

    return {"themes": themes}
