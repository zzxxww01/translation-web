"""
微信公众号格式化 API 路由
"""

from fastapi import APIRouter
from pydantic import BaseModel

from ..middleware import BadRequestException, ServiceUnavailableException
from src.services.wechat_formatter import WechatFormatter
from src.services.wechat_themes import list_themes


router = APIRouter()


class WechatFormatRequest(BaseModel):
    """微信格式化请求"""

    markdown: str
    theme: str = "default"
    upload_images: bool = False
    image_to_base64: bool = False


class WechatFormatResponse(BaseModel):
    """微信格式化响应"""

    html: str
    image_count: int
    image_urls: list[str]


class WechatThemesResponse(BaseModel):
    """主题列表响应"""

    themes: list[str]


@router.post("/wechat/format", response_model=WechatFormatResponse)
async def format_for_wechat(request: WechatFormatRequest):
    """
    将 Markdown 转换为微信公众号格式

    - **markdown**: Markdown 文本
    - **theme**: 主题名称（default, tech, minimal）
    - **upload_images**: 是否上传图片到图床
    - **image_to_base64**: 是否将图片转为 Base64
    """
    if not request.markdown.strip():
        raise BadRequestException(detail="Markdown content cannot be empty")

    try:
        formatter = WechatFormatter()
        result = formatter.format(
            markdown=request.markdown,
            theme=request.theme,
            upload_images=request.upload_images,
            image_to_base64=request.image_to_base64,
        )

        return WechatFormatResponse(
            html=result["html"],
            image_count=result["image_count"],
            image_urls=result["image_urls"],
        )

    except ImportError as e:
        raise ServiceUnavailableException(
            detail=f"Missing required dependency: {str(e)}"
        )
    except Exception as e:
        raise ServiceUnavailableException(detail=f"Format failed: {str(e)}")


@router.get("/wechat/themes", response_model=WechatThemesResponse)
async def get_wechat_themes():
    """获取所有可用主题"""
    themes = list_themes()
    return WechatThemesResponse(themes=themes)
