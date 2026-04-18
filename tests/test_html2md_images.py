"""Tests for HTML to Markdown image processing."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.html2md.images import _copy_image, copy_and_rewrite_images


@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    with patch("src.html2md.images.logger") as mock:
        yield mock


class TestCopyImage:
    """Test _copy_image function."""

    def test_download_external_image_success(self, tmp_path):
        """Test downloading external image successfully."""
        target_path = tmp_path / "test.jpg"

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake image data"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = _copy_image(
                "https://example.com/image.jpg",
                Path("/fake/source.html"),
                target_path
            )

        assert result is True
        assert target_path.exists()
        assert target_path.read_bytes() == b"fake image data"

    def test_download_timeout(self, tmp_path):
        """Test download timeout handling."""
        target_path = tmp_path / "test.jpg"

        with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
            result = _copy_image(
                "https://example.com/slow.jpg",
                Path("/fake/source.html"),
                target_path
            )

        assert result is False
        assert not target_path.exists()

    def test_download_http_error(self, tmp_path):
        """Test HTTP error handling (404, 500, etc)."""
        target_path = tmp_path / "test.jpg"

        from urllib.error import HTTPError

        with patch("urllib.request.urlopen", side_effect=HTTPError(
            "https://example.com/notfound.jpg", 404, "Not Found", {}, None
        )):
            result = _copy_image(
                "https://example.com/notfound.jpg",
                Path("/fake/source.html"),
                target_path
            )

        assert result is False
        assert not target_path.exists()


class TestCopyAndRewriteImagesStatistics:
    """Test statistics logging in copy_and_rewrite_images function."""

    def test_logs_statistics_all_success(self, tmp_path, mock_logger):
        """Test statistics logging when all images succeed."""
        markdown = """
# Test
![alt1](https://example.com/img1.jpg)
![alt2](https://example.com/img2.jpg)
![alt3](https://example.com/img3.jpg)
"""
        source_html = tmp_path / "source.html"
        source_html.write_text("test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_response = Mock()
        mock_response.read.return_value = b"fake image"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            copy_and_rewrite_images(markdown, source_html, output_dir, "test", True)

        mock_logger.info.assert_any_call("开始处理 3 张图片")
        mock_logger.info.assert_any_call("图片处理完成: 总数=3, 成功=3, 失败=0")

    def test_logs_statistics_partial_failure(self, tmp_path, mock_logger):
        """Test statistics logging when some images fail."""
        markdown = """
![alt1](https://example.com/img1.jpg)
![alt2](https://example.com/img2.jpg)
![alt3](https://example.com/img3.jpg)
"""
        source_html = tmp_path / "source.html"
        source_html.write_text("test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        call_count = 0

        def mock_urlopen(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise TimeoutError("timeout")
            mock_response = Mock()
            mock_response.read.return_value = b"fake image"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            copy_and_rewrite_images(markdown, source_html, output_dir, "test", True)

        mock_logger.info.assert_any_call("开始处理 3 张图片")
        mock_logger.info.assert_any_call("图片处理完成: 总数=3, 成功=2, 失败=1")

    def test_logs_statistics_all_failure(self, tmp_path, mock_logger):
        """Test statistics logging when all images fail."""
        markdown = """
![alt1](https://example.com/img1.jpg)
![alt2](https://example.com/img2.jpg)
"""
        source_html = tmp_path / "source.html"
        source_html.write_text("test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
            copy_and_rewrite_images(markdown, source_html, output_dir, "test", True)

        mock_logger.info.assert_any_call("开始处理 2 张图片")
        mock_logger.info.assert_any_call("图片处理完成: 总数=2, 成功=0, 失败=2")

    def test_logs_statistics_no_images(self, tmp_path, mock_logger):
        """Test statistics logging when there are no images."""
        markdown = "# Test\n\nNo images here."
        source_html = tmp_path / "source.html"
        source_html.write_text("test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        copy_and_rewrite_images(markdown, source_html, output_dir, "test", True)

        mock_logger.info.assert_any_call("开始处理 0 张图片")
        mock_logger.info.assert_any_call("图片处理完成: 总数=0, 成功=0, 失败=0")

    def test_logs_statistics_duplicate_images(self, tmp_path, mock_logger):
        """Test statistics logging with duplicate image URLs."""
        markdown = """
![alt1](https://example.com/img1.jpg)
![alt2](https://example.com/img1.jpg)
![alt3](https://example.com/img2.jpg)
"""
        source_html = tmp_path / "source.html"
        source_html.write_text("test")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_response = Mock()
        mock_response.read.return_value = b"fake image"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            copy_and_rewrite_images(markdown, source_html, output_dir, "test", True)

        mock_logger.info.assert_any_call("开始处理 3 张图片")
        mock_logger.info.assert_any_call("图片处理完成: 总数=3, 成功=2, 失败=0")
