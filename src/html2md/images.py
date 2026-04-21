from __future__ import annotations

import logging
import re
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from .utils import sanitize_basename

logger = logging.getLogger(__name__)


IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<src><[^>]+>|[^)"]+?)(?:\s+"(?P<title>[^"]*)")?\)'
)

# Substack CDN proxy URL pattern:
# https://substackcdn.com/image/fetch/$s_!TOKEN!,params.../https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2F...
# 通用匹配：提取最后一个 URL 编码的 https:// 地址
_SUBSTACK_CDN_PATTERN = re.compile(
    r"https?://substackcdn\.com/image/fetch/.+/(https?%3A%2F%2F.+)"
)


def copy_and_rewrite_images(
    markdown: str,
    source_html_path: Path,
    output_dir: Path,
    basename: str,
    copy_images: bool,
) -> str:
    if not copy_images:
        return markdown

    safe_basename = sanitize_basename(basename)
    images_dir_name = f"{safe_basename}_images"
    images_dir_path = output_dir / images_dir_name
    if images_dir_path.exists():
        shutil.rmtree(images_dir_path, ignore_errors=True)

    images = list(IMAGE_PATTERN.finditer(markdown))
    total_count = len(images)
    logger.info(f"开始处理 {total_count} 张图片")

    replacements: dict[str, str] = {}
    counter = 1
    success_count = 0
    failed_count = 0

    for match in images:
        src = _normalize_src(match.group("src"))
        if src in replacements:
            continue
        suffix = _detect_suffix(src) or ".jpg"
        target_name = f"img_{counter:03d}{suffix}"
        target_path = images_dir_path / target_name
        target_rel = f"./{images_dir_name}/{target_name}"
        copied = _copy_image(src, source_html_path, target_path)
        replacements[src] = target_rel if copied else src
        if copied:
            counter += 1
            success_count += 1
        else:
            failed_count += 1

    logger.info(
        f"图片处理完成: 总数={total_count}, 成功={success_count}, 失败={failed_count}"
    )

    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        src = _normalize_src(match.group("src"))
        rewritten = replacements.get(src, src)
        title = match.group("title")
        title_part = f' "{title}"' if title else ""
        return f"![{alt}]({rewritten}{title_part})"

    return IMAGE_PATTERN.sub(replace, markdown)


def _copy_image(src: str, source_html_path: Path, target_path: Path) -> bool:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith(("http://", "https://")):
        try:
            request = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
                with target_path.open("wb") as output:
                    output.write(content)
                logger.info(f"Downloaded image: {src} -> {target_path.name}")
                return True
        except Exception as e:
            logger.warning(f"Failed to download image: {src}, reason: {e}")
            return False

    source_path = (source_html_path.parent / src).resolve()
    if not source_path.exists():
        logger.warning(f"Local image not found: {src}")
        return False
    shutil.copy2(source_path, target_path)
    logger.info(f"Copied local image: {src} -> {target_path.name}")
    return True


def _detect_suffix(src: str) -> str:
    suffix = Path(urlparse(src).path).suffix
    return suffix if suffix and len(suffix) <= 5 else ""


def _resolve_substack_cdn_url(url: str) -> str:
    """Extract the direct S3 URL from a Substack CDN proxy URL.

    Substack wraps S3 image URLs in a CDN proxy with signature tokens that
    expire.  The embedded S3 URL is public and permanent.

    Example input:
      https://substackcdn.com/image/fetch/$s_!eHLl!,w_1456,.../https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F...png
    Output:
      https://substack-post-media.s3.amazonaws.com/public/images/...png
    """
    m = _SUBSTACK_CDN_PATTERN.match(url)
    if not m:
        return url
    return unquote(m.group(1))


def _normalize_src(src: str) -> str:
    src = src.strip()
    if src.startswith("<") and src.endswith(">"):
        src = src[1:-1].strip()
    return _resolve_substack_cdn_url(src)
