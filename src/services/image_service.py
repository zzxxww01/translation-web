"""
Image Processing Service - 图片处理服务

提供图片下载、本地化和图注翻译的完整服务
"""

from typing import List, Dict, Any, Optional
import asyncio

from ..core.models import Paragraph, Section
from ..core.image_processor import ImageProcessor, CaptionTranslator, ImageInfo
from ..llm.base import LLMProvider


class ImageProcessingService:
    """图片处理服务"""

    def __init__(
        self,
        project_id: str,
        llm_provider: Optional[LLMProvider] = None,
        base_dir: str = "projects",
    ):
        """
        初始化图片处理服务

        Args:
            project_id: 项目ID
            llm_provider: LLM Provider（用于图注翻译）
            base_dir: 项目基础目录
        """
        self.project_id = project_id
        self.processor = ImageProcessor(project_id, base_dir)
        self.caption_translator = (
            CaptionTranslator(llm_provider) if llm_provider else None
        )

    async def process_sections(
        self,
        sections: List[Section],
        download_images: bool = True,
        translate_captions: bool = True,
    ) -> Dict[str, Any]:
        """
        处理所有章节中的图片

        Args:
            sections: 章节列表
            download_images: 是否下载图片
            translate_captions: 是否翻译图注

        Returns:
            {
                "total_images": int,
                "downloaded": int,
                "failed": int,
                "images": {...}
            }
        """
        all_images = []

        # 1. 扫描所有段落，提取图片
        for section in sections:
            for paragraph in section.paragraphs:
                images = self.processor.extract_images_from_markdown(paragraph.source)
                all_images.extend(images)

        # 2. 下载图片（如果需要）
        if download_images and all_images:
            # 收集所有URL
            urls = list(set(img_info.original_url for _, img_info in all_images))

            # 并发下载
            tasks = [self.processor.download_image(url) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 更新段落中的图片URL
        for section in sections:
            for paragraph in section.paragraphs:
                if "![" in paragraph.source:
                    # 替换图片URL
                    updated_source = self.processor.replace_image_urls(paragraph.source)
                    paragraph.source = updated_source

                # 4. 检测并翻译图注（如果是下一段）
                if translate_captions and self.caption_translator:
                    if self.caption_translator.detect_caption(paragraph.source):
                        caption_translation = self.caption_translator.translate_caption(
                            paragraph.source
                        )
                        # 记录翻译
                        paragraph.add_translation(caption_translation, "auto_caption")
                        paragraph.confirm(caption_translation, "auto_caption")

        # 5. 统计
        downloaded = sum(
            1
            for img_info in self.processor.images.values()
            if img_info.download_status == "success"
        )
        failed = sum(
            1
            for img_info in self.processor.images.values()
            if img_info.download_status == "failed"
        )

        return {
            "total_images": len(self.processor.images),
            "downloaded": downloaded,
            "failed": failed,
            "images": self.processor.images,
        }

    def get_image_report(self) -> Dict[str, Any]:
        """
        获取图片处理报告

        Returns:
            {
                "total": int,
                "success": int,
                "failed": int,
                "details": [...]
            }
        """
        details = []
        for url, img_info in self.processor.images.items():
            details.append(
                {
                    "url": url,
                    "status": img_info.download_status,
                    "local_path": img_info.local_path,
                    "alt_text": img_info.alt_text,
                    "error": img_info.error_message,
                }
            )

        return {
            "total": len(self.processor.images),
            "success": sum(
                1
                for img in self.processor.images.values()
                if img.download_status == "success"
            ),
            "failed": sum(
                1
                for img in self.processor.images.values()
                if img.download_status == "failed"
            ),
            "details": details,
        }


# 同步版本（用于非async环境）
class SyncImageProcessingService:
    """同步版图片处理服务"""

    def __init__(
        self,
        project_id: str,
        llm_provider: Optional[LLMProvider] = None,
        base_dir: str = "projects",
    ):
        self.async_service = ImageProcessingService(project_id, llm_provider, base_dir)

    def process_sections(
        self,
        sections: List[Section],
        download_images: bool = True,
        translate_captions: bool = True,
    ) -> Dict[str, Any]:
        """同步处理章节中的图片"""
        # 在新的事件循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.async_service.process_sections(
                    sections, download_images, translate_captions
                )
            )
            return result
        finally:
            loop.close()

    def get_image_report(self) -> Dict[str, Any]:
        """获取图片处理报告"""
        return self.async_service.get_image_report()
