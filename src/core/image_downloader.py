"""
Image Downloader — handle image downloading and local-copy logic for the parser.

Extracted from parser.py to follow the Single Responsibility Principle.
"""

import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

from .url_safety import is_safe_url
from .public_resources import fetch_public_bytes, confined_local_path, atomic_write_resource, MAX_RESOURCE_BYTES


class ImageDownloader:
    """Download or copy images to a local directory."""

    def __init__(
        self,
        images_dir: Optional[str] = None,
        source_dir: Optional[Path] = None,
        base_url: Optional[str] = None,
    ):
        self.images_dir = images_dir
        self.source_dir = source_dir
        self.base_url = base_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, src: str) -> Optional[str]:
        """
        下载图片到本地

        Args:
            src: 图片 URL 或本地路径

        Returns:
            本地相对路径，失败返回 None
        """
        try:
            local_src_path = self._resolve_local_image_path(src)
            if local_src_path:
                return self._copy_local_image(local_src_path, src)

            # 解析相对 URL
            if self.base_url and not src.startswith(("http://", "https://", "data:")):
                src = urljoin(self.base_url, src)

            if src.startswith("data:"):
                return None

            if not src.startswith(("http://", "https://")):
                return None

            # 安全:SSRF 防护。src 来自被翻译文档(外部可控),阻止指向内网/回环/
            # 云元数据(如 169.254.169.254)等地址。请求前解析并校验所有 IP,线程安全。
            if not is_safe_url(src):
                print(f"[ImageDownloader] Blocked unsafe image URL: {src}")
                return None

            if not self.images_dir:
                return None

            images_dir = Path(self.images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名（使用 URL hash）
            url_hash = hashlib.md5(src.encode()).hexdigest()[:12]
            parsed = urlparse(src)
            ext = Path(parsed.path).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}:
                ext = ".jpg"
            filename = f"{url_hash}{ext}"
            local_path = images_dir / filename

            if local_path.exists():
                return self._relative_image_path(filename)

            content, _ = fetch_public_bytes(src, timeout=30, max_bytes=MAX_RESOURCE_BYTES)
            atomic_write_resource(local_path, content)

            return self._relative_image_path(filename)

        except Exception as e:
            print(f"[ImageDownloader] Failed to download image {src}: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _relative_image_path(self, filename: str) -> str:
        """Build a relative path for images inside the output directory."""
        images_dir_name = Path(self.images_dir).name if self.images_dir else "images"
        return f"./{images_dir_name}/{filename}"

    def _resolve_local_image_path(self, src: str) -> Optional[Path]:
        """Resolve local image path from src for file-based HTML."""
        return confined_local_path(src, self.source_dir)

    def _copy_local_image(self, src_path: Path, src: str) -> Optional[str]:
        """Copy local image into images_dir and return relative path."""
        if not self.images_dir:
            return None

        images_dir = Path(self.images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        ext = src_path.suffix or ".jpg"
        url_hash = hashlib.md5(src.encode()).hexdigest()[:12]
        filename = f"{url_hash}{ext}"
        local_path = images_dir / filename

        if not local_path.exists():
            with src_path.open("rb") as file:
                content = file.read(MAX_RESOURCE_BYTES + 1)
            if len(content) > MAX_RESOURCE_BYTES:
                raise ValueError("Local image exceeds size limit")
            atomic_write_resource(local_path, content)

        return self._relative_image_path(filename)
