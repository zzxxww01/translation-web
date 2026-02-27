"""
Image Processor - 图片处理器

处理文档中的图片：下载、本地化、alt文本生成、图注翻译
"""

from typing import Optional, Dict, Any, List, Tuple
import os
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass
import aiohttp
import asyncio


@dataclass
class ImageInfo:
    """图片信息"""

    original_url: str
    local_path: Optional[str] = None
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    caption_translation: Optional[str] = None
    download_status: str = "pending"  # pending, success, failed
    error_message: Optional[str] = None


class ImageProcessor:
    """图片处理器"""

    def __init__(self, project_id: str, base_dir: str = "projects"):
        """
        初始化图片处理器

        Args:
            project_id: 项目ID
            base_dir: 项目基础目录
        """
        self.project_id = project_id
        self.base_dir = base_dir

        # 图片保存目录
        self.images_dir = os.path.join(base_dir, project_id, "images")
        os.makedirs(self.images_dir, exist_ok=True)

        # 图片计数器
        self.image_counter = 1

        # 图片缓存
        self.images: Dict[str, ImageInfo] = {}

    def extract_images_from_markdown(
        self, markdown: str
    ) -> List[Tuple[str, ImageInfo]]:
        """
        从Markdown中提取图片信息

        Args:
            markdown: Markdown文本

        Returns:
            [(完整匹配文本, ImageInfo), ...]
        """
        # Markdown图片模式: ![alt](url)
        pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"

        images = []
        for match in re.finditer(pattern, markdown):
            full_match = match.group(0)
            alt_text = match.group(1)
            url = match.group(2)

            # 检查是否已处理
            if url in self.images:
                image_info = self.images[url]
            else:
                image_info = ImageInfo(
                    original_url=url, alt_text=alt_text if alt_text else None
                )
                self.images[url] = image_info

            images.append((full_match, image_info))

        return images

    async def download_image(self, url: str) -> ImageInfo:
        """
        下载图片到本地

        Args:
            url: 图片URL

        Returns:
            更新后的ImageInfo
        """
        image_info = self.images.get(url)
        if not image_info:
            image_info = ImageInfo(original_url=url)
            self.images[url] = image_info

        try:
            # 生成本地文件名
            ext = self._get_file_extension(url)
            filename = f"image-{self.image_counter}{ext}"
            local_path = os.path.join(self.images_dir, filename)

            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content = await response.read()

                        # 保存到本地
                        with open(local_path, "wb") as f:
                            f.write(content)

                        # 更新信息
                        image_info.local_path = local_path
                        image_info.download_status = "success"

                        # 生成alt文本（如果没有）
                        if not image_info.alt_text:
                            image_info.alt_text = f"图{self.image_counter}"

                        self.image_counter += 1
                    else:
                        image_info.download_status = "failed"
                        image_info.error_message = f"HTTP {response.status}"

        except Exception as e:
            image_info.download_status = "failed"
            image_info.error_message = str(e)

        return image_info

    async def download_all_images(self, markdown: str) -> Dict[str, ImageInfo]:
        """
        批量下载所有图片

        Args:
            markdown: Markdown文本

        Returns:
            {url: ImageInfo, ...}
        """
        # 提取图片
        images = self.extract_images_from_markdown(markdown)

        # 并发下载
        tasks = [
            self.download_image(image_info.original_url) for _, image_info in images
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        return self.images

    def replace_image_urls(self, markdown: str) -> str:
        """
        替换Markdown中的图片URL为本地路径

        Args:
            markdown: 原始Markdown

        Returns:
            更新后的Markdown
        """
        result = markdown

        # 提取图片
        images = self.extract_images_from_markdown(markdown)

        # 从后往前替换（避免位置偏移）
        for full_match, image_info in reversed(images):
            if image_info.download_status == "success" and image_info.local_path:
                # 使用相对路径
                relative_path = f"./images/{os.path.basename(image_info.local_path)}"
                new_alt = image_info.alt_text or "图片"
                new_markdown = f"![{new_alt}]({relative_path})"
            elif image_info.download_status == "failed":
                # 下载失败，标记
                new_markdown = (
                    f"[图片加载失败: {image_info.error_message or '未知错误'}]"
                )
            else:
                # 保持原样
                continue

            # 替换
            result = result.replace(full_match, new_markdown, 1)

        return result

    def _get_file_extension(self, url: str) -> str:
        """获取文件扩展名"""
        # 从URL提取扩展名
        match = re.search(r"\.(jpg|jpeg|png|gif|webp|svg)(?:\?|$)", url, re.IGNORECASE)
        if match:
            return f".{match.group(1).lower()}"

        # 默认使用png
        return ".png"

    def _generate_hash(self, url: str) -> str:
        """生成URL的哈希值（用于文件名）"""
        return hashlib.md5(url.encode()).hexdigest()[:8]


class CaptionTranslator:
    """图注翻译器"""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def detect_caption(self, text: str) -> bool:
        """
        检测文本是否为图注

        简单规则：
        - 以"Source:", "Figure:", "图" 等开头
        - 紧跟在图片后面的短文本
        """
        text_lower = text.lower().strip()

        caption_indicators = [
            "source:",
            "figure:",
            "fig.",
            "图",
            "来源：",
        ]

        for indicator in caption_indicators:
            if text_lower.startswith(indicator):
                return True

        return False

    def translate_caption(self, caption: str, preserve_links: bool = True) -> str:
        """
        翻译图注

        Args:
            caption: 图注原文
            preserve_links: 是否保留链接

        Returns:
            翻译后的图注
        """
        # 简化实现：使用规则翻译
        # "Source:" → "来源："
        result = caption

        translations = {
            "Source:": "来源：",
            "source:": "来源：",
            "Figure:": "图：",
            "figure:": "图：",
            "Fig.": "图",
            "Repository": "仓库",
            "repository": "仓库",
            "Github": "Github",  # 保留
        }

        for en, zh in translations.items():
            result = result.replace(en, zh)

        return result


# 辅助函数
def process_images_in_paragraph(
    paragraph_text: str, processor: ImageProcessor
) -> Tuple[str, List[ImageInfo]]:
    """
    处理段落中的图片

    Args:
        paragraph_text: 段落文本
        processor: 图片处理器

    Returns:
        (更新后的文本, 图片信息列表)
    """
    # 提取图片
    images = processor.extract_images_from_markdown(paragraph_text)

    # 异步下载（在实际使用中需要在async函数中调用）
    # await processor.download_all_images(paragraph_text)

    # 替换URL
    updated_text = processor.replace_image_urls(paragraph_text)

    return updated_text, [img_info for _, img_info in images]
