from __future__ import annotations

from pathlib import Path

from src.core.models import ArticleMetadata as ProjectArticleMetadata

from .extractor import extract_article
from .images import copy_and_rewrite_images
from .markdown import render_markdown


def convert_html_to_markdown_text(
    html_path: str | Path,
    output_dir: str | Path | None = None,
    copy_images: bool = True,
) -> tuple[str, ProjectArticleMetadata]:
    html_path = Path(html_path).resolve()
    target_dir = Path(output_dir).resolve() if output_dir else html_path.parent.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    metadata, body = extract_article(html_path)
    markdown = render_markdown(str(body), metadata)
    markdown = copy_and_rewrite_images(
        markdown=markdown,
        source_html_path=html_path,
        output_dir=target_dir,
        basename=html_path.stem,
        copy_images=copy_images,
    )
    project_metadata = ProjectArticleMetadata(
        authors=[author.name for author in metadata.authors],
        published_date=metadata.date_text or None,
        subtitle=metadata.subtitle or None,
        publication=metadata.publication or None,
        original_url=metadata.canonical_url or None,
        cover_image=metadata.cover_image or None,
    )
    return markdown, project_metadata


def convert_html_to_markdown(
    html_path: str | Path,
    output_dir: str | Path | None = None,
    copy_images: bool = True,
) -> Path:
    html_path = Path(html_path).resolve()
    target_dir = Path(output_dir).resolve() if output_dir else html_path.parent.resolve()
    markdown, _ = convert_html_to_markdown_text(
        html_path=html_path,
        output_dir=target_dir,
        copy_images=copy_images,
    )
    output_path = target_dir / f"{html_path.stem}_auto_extracted.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
