"""Image processing and caption translation helpers."""

from __future__ import annotations

import asyncio
import html
import re
import threading
from typing import Any, Dict, List, Optional

from ..core.format_tokens import (
    apply_translation_payload,
    build_dehydrated_link_payload,
    build_translation_input,
    build_translation_payload,
    format_token_context,
)
from ..core.image_processor import CaptionTranslator, ImageProcessor
from ..core.models import ElementType, Paragraph, Section
from ..llm.base import LLMProvider


IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<src><[^>]+>|[^)"]+?)(?:\s+"(?P<title>[^"]*)")?\)$'
)


class ImageProcessingService:
    """Download images, localize URLs, and translate captions."""

    def __init__(
        self,
        project_id: str,
        llm_provider: Optional[LLMProvider] = None,
        base_dir: str = "projects",
    ):
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
        """Process all images and captions across the given sections."""
        all_images = []

        for section in sections:
            for paragraph in section.paragraphs:
                markdown_source = self._image_markdown_source(paragraph)
                if not markdown_source:
                    continue
                images = self.processor.extract_images_from_markdown(markdown_source)
                all_images.extend(images)

        if download_images and all_images:
            urls = list({img_info.original_url for _, img_info in all_images})
            tasks = [self.processor.download_image(url) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        for section in sections:
            for paragraph in section.paragraphs:
                markdown_source = self._image_markdown_source(paragraph)
                if markdown_source:
                    updated_markdown = self.processor.replace_image_urls(markdown_source)
                    self._apply_image_markdown(paragraph, updated_markdown)

                if (
                    translate_captions
                    and self.caption_translator
                    and self.caption_translator.detect_caption(paragraph.source)
                ):
                    self._translate_caption(paragraph)

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

    def _image_markdown_source(self, paragraph: Paragraph) -> str:
        block_type = paragraph.parent_block_type or paragraph.element_type
        if block_type == ElementType.IMAGE:
            return paragraph.parent_block_markdown or f"![image]({paragraph.source})"
        if "![" in paragraph.source:
            return paragraph.source
        return ""

    def _apply_image_markdown(self, paragraph: Paragraph, markdown_text: str) -> None:
        block_type = paragraph.parent_block_type or paragraph.element_type
        if block_type != ElementType.IMAGE:
            paragraph.source = markdown_text
            return

        match = IMAGE_PATTERN.match(markdown_text.strip())
        if not match:
            paragraph.parent_block_markdown = markdown_text
            paragraph.source = markdown_text
            return

        src = match.group("src").strip()
        if src.startswith("<") and src.endswith(">"):
            src = src[1:-1].strip()
        alt = (match.group("alt") or "").strip()
        title = (match.group("title") or "").strip()

        paragraph.source = src
        paragraph.parent_block_markdown = markdown_text.strip()
        paragraph.source_html = self._build_image_html(src, alt, title)
        paragraph.parent_source_html = paragraph.source_html

    def _build_image_html(self, src: str, alt: str, title: str) -> str:
        attrs = [f'src="{html.escape(src, quote=True)}"']
        if alt:
            attrs.append(f'alt="{html.escape(alt, quote=True)}"')
        if title:
            attrs.append(f'title="{html.escape(title, quote=True)}"')
        return f"<img {' '.join(attrs)} />"

    def _translate_caption(self, paragraph: Paragraph) -> None:
        if self.caption_translator is None:
            return

        if paragraph.inline_elements and getattr(self.caption_translator, "llm", None):
            dehydrated_payload = build_dehydrated_link_payload(paragraph)
            if dehydrated_payload is not None:
                payload = dehydrated_payload
            else:
                prepared = build_translation_input(paragraph)
                translated = self.caption_translator.llm.translate(
                    prepared.tokenized_text or prepared.text,
                    context={
                        "instruction": (
                            "Translate this image caption into concise Chinese. "
                            "Preserve hidden format tokens exactly."
                        ),
                        "format_tokens": format_token_context(paragraph),
                    },
                )
                payload = build_translation_payload(
                    paragraph,
                    translated,
                    token_repairer=self._repair_format_tokens,
                )
            apply_translation_payload(paragraph, payload, "auto_caption")
            paragraph.confirm(
                payload.text,
                "auto_caption",
                tokenized_text=payload.tokenized_text,
                format_issues=payload.format_issues,
            )
            return

        caption_translation = self.caption_translator.translate_caption(paragraph.source)
        paragraph.add_translation(caption_translation, "auto_caption")
        paragraph.confirm(caption_translation, "auto_caption")

    def _repair_format_tokens(
        self,
        paragraph: Paragraph,
        translated_tokenized_text: str,
        issues: List[str],
    ) -> Optional[str]:
        llm = getattr(self.caption_translator, "llm", None)
        if llm is None or not paragraph.inline_elements:
            return None

        prepared = build_translation_input(paragraph)
        return llm.repair_format_tokens(
            source_text=prepared.tokenized_text or prepared.text,
            translated_text=translated_tokenized_text,
            format_tokens=format_token_context(paragraph),
            issues=issues,
            model="flash",
        )

    def get_image_report(self) -> Dict[str, Any]:
        """Return one summary of image download results."""
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


class SyncImageProcessingService:
    """Synchronous wrapper for image processing."""

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
        coroutine = self.async_service.process_sections(
            sections,
            download_images,
            translate_captions,
        )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result: Dict[str, Any] = {}
        error: Optional[BaseException] = None

        def _runner() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(coroutine)
            except BaseException as exc:  # pragma: no cover - thread bridge
                error = exc

        worker = threading.Thread(target=_runner, daemon=True)
        worker.start()
        worker.join()
        if error is not None:
            raise error
        return result

    def get_image_report(self) -> Dict[str, Any]:
        return self.async_service.get_image_report()
