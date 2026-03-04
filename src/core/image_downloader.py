"""
Image Downloader — handle image downloading and local-copy logic for the parser.

Extracted from parser.py to follow the Single Responsibility Principle.
"""

import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, unquote

import requests


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

            if not self.images_dir:
                return None

            images_dir = Path(self.images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名（使用 URL hash）
            url_hash = hashlib.md5(src.encode()).hexdigest()[:12]
            parsed = urlparse(src)
            ext = Path(parsed.path).suffix or ".jpg"
            filename = f"{url_hash}{ext}"
            local_path = images_dir / filename

            if local_path.exists():
                return self._relative_image_path(filename)

            response = requests.get(
                src,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            with open(local_path, "wb") as f:
                f.write(response.content)

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
        if not src:
            return None
        if src.startswith("data:"):
            return None

        # Windows absolute paths (e.g. C:\...)
        if re.match(r"^[A-Za-z]:[\\\/]", src):
            candidate = Path(src)
            return candidate if candidate.exists() else None

        parsed = urlparse(src)
        if parsed.scheme in ("http", "https"):
            return None

        path_str = src
        if parsed.scheme == "file":
            path_str = unquote(parsed.path)
            if os.name == "nt" and re.match(r"^/[A-Za-z]:", path_str):
                path_str = path_str.lstrip("/")
        elif parsed.scheme != "":
            return None
        else:
            path_str = unquote(parsed.path or src)

        path_str = path_str.split("?", 1)[0].split("#", 1)[0]
        candidate = Path(path_str)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None

        if self.source_dir:
            candidate = (self.source_dir / path_str).resolve()
            if candidate.exists():
                return candidate
        return None

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
            shutil.copy2(src_path, local_path)

        return self._relative_image_path(filename)
