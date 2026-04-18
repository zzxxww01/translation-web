"""Integration tests for HTML to Markdown image download and localization."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.html2md.images import copy_and_rewrite_images


@pytest.fixture
def sample_markdown():
    """Sample markdown with multiple image references."""
    return """# Test Article

Here is an image:
![Alt text 1](https://example.com/image1.jpg)

And another one:
![Alt text 2](https://example.com/image2.png "Image Title")

Duplicate reference:
![Alt text 3](https://example.com/image1.jpg)

Local image:
![Local](./local.jpg)
"""


@pytest.fixture
def mock_image_content():
    """Mock image content for different formats."""
    return {
        "https://example.com/image1.jpg": b"\xff\xd8\xff\xe0JPEG_DATA",
        "https://example.com/image2.png": b"\x89PNG\r\n\x1a\nPNG_DATA",
    }


def test_copy_and_rewrite_images_full_flow(
    tmp_path: Path, sample_markdown: str, mock_image_content: dict, caplog
):
    """Test complete image download and rewrite flow."""
    caplog.set_level(logging.INFO)

    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def mock_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url in mock_image_content:
            mock_response = Mock()
            mock_response.read.return_value = mock_image_content[url]
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response
        raise Exception(f"URL not mocked: {url}")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=sample_markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Verify image directory was created
    images_dir = output_dir / "test-article_images"
    assert images_dir.exists()
    assert images_dir.is_dir()

    # Verify images were downloaded with correct naming
    img1 = images_dir / "img_001.jpg"
    img2 = images_dir / "img_002.png"
    assert img1.exists()
    assert img2.exists()

    # Verify image content
    assert img1.read_bytes() == mock_image_content["https://example.com/image1.jpg"]
    assert img2.read_bytes() == mock_image_content["https://example.com/image2.png"]

    # Verify markdown was rewritten correctly
    assert "![Alt text 1](./test-article_images/img_001.jpg)" in result
    assert '![Alt text 2](./test-article_images/img_002.png "Image Title")' in result
    # Duplicate should reference the same file
    assert "![Alt text 3](./test-article_images/img_001.jpg)" in result
    # Failed local image should keep original path
    assert "![Local](./local.jpg)" in result

    # Verify logging output
    assert "开始处理 4 张图片" in caplog.text
    assert "Downloaded image: https://example.com/image1.jpg -> img_001.jpg" in caplog.text
    assert "Downloaded image: https://example.com/image2.png -> img_002.png" in caplog.text
    assert "图片处理完成: 总数=4, 成功=2, 失败=1" in caplog.text


def test_copy_images_disabled(tmp_path: Path, sample_markdown: str):
    """Test that copy_images=False returns markdown unchanged."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = copy_and_rewrite_images(
        markdown=sample_markdown,
        source_html_path=source_html,
        output_dir=output_dir,
        basename="test-article",
        copy_images=False,
    )

    assert result == sample_markdown
    assert not (output_dir / "test-article_images").exists()


def test_image_directory_cleanup(tmp_path: Path, mock_image_content: dict):
    """Test that existing image directory is cleaned up before processing."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create pre-existing image directory with old files
    images_dir = output_dir / "test-article_images"
    images_dir.mkdir()
    old_file = images_dir / "old_image.jpg"
    old_file.write_bytes(b"OLD_DATA")

    markdown = "![Test](https://example.com/image1.jpg)"

    def mock_urlopen(request, timeout):
        mock_response = Mock()
        mock_response.read.return_value = mock_image_content["https://example.com/image1.jpg"]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Old file should be removed
    assert not old_file.exists()
    # New file should exist
    assert (images_dir / "img_001.jpg").exists()


def test_download_failure_handling(tmp_path: Path, caplog):
    """Test handling of failed image downloads."""
    caplog.set_level(logging.WARNING)

    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    markdown = """![Success](https://example.com/good.jpg)
![Failure](https://example.com/bad.jpg)"""

    def mock_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "good.jpg" in url:
            mock_response = Mock()
            mock_response.read.return_value = b"GOOD_DATA"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response
        raise Exception("Network error")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Successful download should be rewritten
    assert "![Success](./test-article_images/img_001.jpg)" in result
    # Failed download should keep original URL
    assert "![Failure](https://example.com/bad.jpg)" in result

    # Verify warning was logged
    assert "Failed to download image: https://example.com/bad.jpg" in caplog.text


def test_local_image_copy(tmp_path: Path, caplog):
    """Test copying local images from source directory."""
    caplog.set_level(logging.INFO)

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_html = source_dir / "article.html"
    source_html.write_text("<html></html>")

    # Create local image
    local_image = source_dir / "local.png"
    local_image.write_bytes(b"LOCAL_IMAGE_DATA")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    markdown = "![Local](./local.png)"

    result = copy_and_rewrite_images(
        markdown=markdown,
        source_html_path=source_html,
        output_dir=output_dir,
        basename="test-article",
        copy_images=True,
    )

    # Verify local image was copied
    copied_image = output_dir / "test-article_images" / "img_001.png"
    assert copied_image.exists()
    assert copied_image.read_bytes() == b"LOCAL_IMAGE_DATA"

    # Verify markdown was rewritten
    assert "![Local](./test-article_images/img_001.png)" in result

    # Verify log message
    assert "Copied local image: ./local.png -> img_001.png" in caplog.text


def test_image_format_detection(tmp_path: Path, mock_image_content: dict):
    """Test that image formats are correctly detected from URLs."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    markdown = """![JPG](https://example.com/photo.jpg)
![PNG](https://example.com/graphic.png)
![No extension](https://example.com/image)"""

    def mock_urlopen(request, timeout):
        mock_response = Mock()
        mock_response.read.return_value = b"IMAGE_DATA"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    images_dir = output_dir / "test-article_images"
    # JPG extension preserved
    assert (images_dir / "img_001.jpg").exists()
    # PNG extension preserved
    assert (images_dir / "img_002.png").exists()
    # No extension defaults to .jpg
    assert (images_dir / "img_003.jpg").exists()


def test_duplicate_image_deduplication(tmp_path: Path, mock_image_content: dict):
    """Test that duplicate image URLs are only downloaded once."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    markdown = """![First](https://example.com/image1.jpg)
![Second](https://example.com/image2.png)
![Duplicate 1](https://example.com/image1.jpg)
![Duplicate 2](https://example.com/image1.jpg)"""

    download_count = 0

    def mock_urlopen(request, timeout):
        nonlocal download_count
        download_count += 1
        url = request.full_url if hasattr(request, "full_url") else str(request)
        mock_response = Mock()
        mock_response.read.return_value = mock_image_content.get(url, b"DATA")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Should only download 2 unique images
    assert download_count == 2

    images_dir = output_dir / "test-article_images"
    # Only 2 files should exist
    assert len(list(images_dir.glob("*.jpg"))) == 1
    assert len(list(images_dir.glob("*.png"))) == 1

    # All references to the same URL should point to the same local file
    assert result.count("./test-article_images/img_001.jpg") == 3
    assert result.count("./test-article_images/img_002.png") == 1


def test_basename_sanitization(tmp_path: Path, mock_image_content: dict):
    """Test that special characters in basename are sanitized."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    markdown = "![Test](https://example.com/image1.jpg)"

    def mock_urlopen(request, timeout):
        mock_response = Mock()
        mock_response.read.return_value = mock_image_content["https://example.com/image1.jpg"]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test/article:with*special?chars",
            copy_images=True,
        )

    # Directory name should be sanitized
    sanitized_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    assert len(sanitized_dirs) == 1
    # Should not contain special characters
    dir_name = sanitized_dirs[0].name
    assert "/" not in dir_name
    assert ":" not in dir_name
    assert "*" not in dir_name
    assert "?" not in dir_name


def test_substack_cdn_url_resolution(tmp_path: Path):
    """Test that Substack CDN proxy URLs are resolved to direct S3 URLs."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Substack CDN proxy URL with encoded S3 URL
    substack_url = (
        "https://substackcdn.com/image/fetch/"
        "w_1456,c_limit,f_webp,q_auto:good,fl_progressive:steep/"
        "https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ftest.png"
    )
    direct_s3_url = "https://substack-post-media.s3.amazonaws.com/public/images/test.png"

    markdown = f"![Substack Image]({substack_url})"

    def mock_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        # Should receive the direct S3 URL, not the CDN proxy URL
        assert url == direct_s3_url
        mock_response = Mock()
        mock_response.read.return_value = b"SUBSTACK_IMAGE_DATA"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Image should be downloaded and rewritten
    assert "![Substack Image](./test-article_images/img_001.png)" in result
    assert (output_dir / "test-article_images" / "img_001.png").exists()


def test_angle_bracket_wrapped_urls(tmp_path: Path, mock_image_content: dict):
    """Test that URLs wrapped in angle brackets are handled correctly."""
    source_html = tmp_path / "article.html"
    source_html.write_text("<html></html>")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Markdown with angle-bracket wrapped URL
    markdown = "![Test](<https://example.com/image1.jpg>)"

    def mock_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        # Should receive the unwrapped URL
        assert url == "https://example.com/image1.jpg"
        mock_response = Mock()
        mock_response.read.return_value = mock_image_content["https://example.com/image1.jpg"]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = copy_and_rewrite_images(
            markdown=markdown,
            source_html_path=source_html,
            output_dir=output_dir,
            basename="test-article",
            copy_images=True,
        )

    # Image should be downloaded and rewritten
    assert "![Test](./test-article_images/img_001.jpg)" in result
    assert (output_dir / "test-article_images" / "img_001.jpg").exists()
