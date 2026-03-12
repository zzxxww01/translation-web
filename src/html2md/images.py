from __future__ import annotations

import re
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .utils import sanitize_basename


IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<src><[^>]+>|[^)"]+?)(?:\s+"(?P<title>[^"]*)")?\)'
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

    replacements: dict[str, str] = {}
    counter = 1
    for match in IMAGE_PATTERN.finditer(markdown):
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
            with urllib.request.urlopen(request, timeout=10) as response, target_path.open("wb") as output:
                output.write(response.read())
            return True
        except Exception:
            return False

    source_path = (source_html_path.parent / src).resolve()
    if not source_path.exists():
        return False
    shutil.copy2(source_path, target_path)
    return True


def _detect_suffix(src: str) -> str:
    suffix = Path(urlparse(src).path).suffix
    return suffix if suffix and len(suffix) <= 5 else ""


def _normalize_src(src: str) -> str:
    src = src.strip()
    return src[1:-1].strip() if src.startswith("<") and src.endswith(">") else src
