# HTML 转 Markdown 图床功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 HTML 转 Markdown 时自动下载外部图片到本地，改写 URL 为相对路径，支持微信公众号等平台发布。

**Architecture:** 修改 `src/html2md/images.py` 的 `_copy_image()` 函数，增加超时控制、日志记录和错误处理；修改 `src/core/project.py` 启用 `copy_images=True`；保持现有的图片检测和 URL 改写逻辑不变。

**Tech Stack:** Python 3.10+, urllib, logging, pathlib

---

## 文件结构

**修改的文件：**
- `src/html2md/images.py` - 增强图片下载逻辑，添加日志
- `src/core/project.py` - 启用图片下载功能
- `tests/test_html2md_images.py` - 新增测试文件

**不修改的文件：**
- `src/html2md/converter.py` - 保持不变
- `src/core/image_processor.py` - 保持不变（用于长文翻译）

---

## Task 1: 增强图片下载函数

**Files:**
- Modify: `src/html2md/images.py:65-80`
- Test: `tests/test_html2md_images.py` (新建)

- [ ] **Step 1: 编写测试 - 外部图片下载成功**

创建测试文件 `tests/test_html2md_images.py`:

```python
"""Tests for HTML to Markdown image processing."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.html2md.images import _copy_image, copy_and_rewrite_images


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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_html2md_images.py::TestCopyImage::test_download_external_image_success -v
```

预期输出：PASS（当前代码已支持基本下载）

- [ ] **Step 3: 编写测试 - 下载超时**

在 `tests/test_html2md_images.py` 中添加：

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_html2md_images.py::TestCopyImage::test_download_timeout -v
```

预期输出：PASS（当前代码已有 try-except）

- [ ] **Step 5: 编写测试 - HTTP 错误**

在 `tests/test_html2md_images.py` 中添加：

```python
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
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_html2md_images.py::TestCopyImage::test_download_http_error -v
```

预期输出：PASS

- [ ] **Step 7: 修改 _copy_image 函数增加超时和日志**

修改 `src/html2md/images.py:65-80`:

```python
def _copy_image(src: str, source_html_path: Path, target_path: Path) -> bool:
    import logging
    logger = logging.getLogger(__name__)
    
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith(("http://", "https://")):
        try:
            request = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 200:
                    content = response.read()
                    with target_path.open("wb") as output:
                        output.write(content)
                    logger.info(f"Downloaded image: {src} -> {target_path.name}")
                    return True
                else:
                    logger.warning(f"Failed to download image: {src}, HTTP {response.status}")
                    return False
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
```

- [ ] **Step 8: 运行所有测试验证通过**

```bash
pytest tests/test_html2md_images.py::TestCopyImage -v
```

预期输出：所有测试 PASS

- [ ] **Step 9: 提交更改**

```bash
git add src/html2md/images.py tests/test_html2md_images.py
git commit -m "feat(html2md): enhance image download with timeout and logging

- Increase timeout from 10s to 30s
- Add detailed logging for success and failure cases
- Add comprehensive error handling for HTTP errors
- Add unit tests for download scenarios

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 添加图片处理统计日志

**Files:**
- Modify: `src/html2md/images.py:23-62`
- Test: `tests/test_html2md_images.py`

- [ ] **Step 1: 编写测试 - 统计信息**

在 `tests/test_html2md_images.py` 中添加：

```python
class TestCopyAndRewriteImages:
    """Test copy_and_rewrite_images function."""

    def test_statistics_logging(self, tmp_path, caplog):
        """Test that statistics are logged correctly."""
        import logging
        caplog.set_level(logging.INFO)
        
        markdown = """
# Test

![](https://example.com/img1.jpg)
![](https://example.com/img2.jpg)
![](https://example.com/img3.jpg)
"""
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake image"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = copy_and_rewrite_images(
                markdown=markdown,
                source_html_path=Path("/fake/source.html"),
                output_dir=tmp_path,
                basename="test",
                copy_images=True,
            )
        
        # Check that statistics are logged
        assert "Image processing complete" in caplog.text
        assert "3/3 downloaded" in caplog.text or "downloaded: 3" in caplog.text
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_html2md_images.py::TestCopyAndRewriteImages::test_statistics_logging -v
```

预期输出：FAIL（统计日志尚未实现）

- [ ] **Step 3: 修改 copy_and_rewrite_images 添加统计**

修改 `src/html2md/images.py:23-62`:

```python
def copy_and_rewrite_images(
    markdown: str,
    source_html_path: Path,
    output_dir: Path,
    basename: str,
    copy_images: bool,
) -> str:
    import logging
    logger = logging.getLogger(__name__)
    
    if not copy_images:
        return markdown

    safe_basename = sanitize_basename(basename)
    images_dir_name = f"{safe_basename}_images"
    images_dir_path = output_dir / images_dir_name
    if images_dir_path.exists():
        shutil.rmtree(images_dir_path, ignore_errors=True)

    replacements: dict[str, str] = {}
    counter = 1
    total_images = 0
    failed_images = 0
    
    for match in IMAGE_PATTERN.finditer(markdown):
        src = _normalize_src(match.group("src"))
        if src in replacements:
            continue
        
        total_images += 1
        suffix = _detect_suffix(src) or ".jpg"
        target_name = f"img_{counter:03d}{suffix}"
        target_path = images_dir_path / target_name
        target_rel = f"./{images_dir_name}/{target_name}"
        copied = _copy_image(src, source_html_path, target_path)
        replacements[src] = target_rel if copied else src
        if copied:
            counter += 1
        else:
            failed_images += 1

    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        src = _normalize_src(match.group("src"))
        rewritten = replacements.get(src, src)
        title = match.group("title")
        title_part = f' "{title}"' if title else ""
        return f"![{alt}]({rewritten}{title_part})"

    result = IMAGE_PATTERN.sub(replace, markdown)
    
    # Log statistics
    if total_images > 0:
        success_count = counter - 1
        logger.info(
            f"Image processing complete: downloaded: {success_count}, "
            f"failed: {failed_images}, total: {total_images}"
        )
    
    return result
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_html2md_images.py::TestCopyAndRewriteImages::test_statistics_logging -v
```

预期输出：PASS

- [ ] **Step 5: 编写测试 - 部分失败场景**

在 `tests/test_html2md_images.py` 中添加：

```python
    def test_partial_failure_statistics(self, tmp_path, caplog):
        """Test statistics when some images fail to download."""
        import logging
        caplog.set_level(logging.INFO)
        
        markdown = """
![](https://example.com/good.jpg)
![](https://example.com/bad.jpg)
![](https://example.com/good2.jpg)
"""
        
        def mock_urlopen(request, timeout):
            url = request.full_url
            mock_response = Mock()
            if "bad" in url:
                raise Exception("Download failed")
            mock_response.status = 200
            mock_response.read.return_value = b"fake image"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response
        
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            result = copy_and_rewrite_images(
                markdown=markdown,
                source_html_path=Path("/fake/source.html"),
                output_dir=tmp_path,
                basename="test",
                copy_images=True,
            )
        
        # Check statistics
        assert "downloaded: 2" in caplog.text
        assert "failed: 1" in caplog.text
        assert "total: 3" in caplog.text
        
        # Check that failed image keeps original URL
        assert "https://example.com/bad.jpg" in result
        # Check that successful images are rewritten
        assert "./test_images/img_001.jpg" in result
        assert "./test_images/img_002.jpg" in result
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_html2md_images.py::TestCopyAndRewriteImages::test_partial_failure_statistics -v
```

预期输出：PASS

- [ ] **Step 7: 提交更改**

```bash
git add src/html2md/images.py tests/test_html2md_images.py
git commit -m "feat(html2md): add image processing statistics logging

- Log total, success, and failed image counts
- Preserve original URLs for failed downloads
- Add tests for partial failure scenarios

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 启用图片下载功能

**Files:**
- Modify: `src/core/project.py:870-874`
- Test: 手动测试（集成测试）

- [ ] **Step 1: 修改 ProjectManager.create() 启用图片下载**

修改 `src/core/project.py:870-874`:

```python
        if is_html_source:
            # HTML 链路：转 Markdown，下载外部图片到本地
            shutil.copy(source_path, project_dir / "source.html")
            source_file = "source.html"
            source_md, metadata = convert_html_to_markdown_text(
                html_path=html_path,
                output_dir=project_dir,
                copy_images=True,  # 启用图片下载
            )
```

- [ ] **Step 2: 提交更改**

```bash
git add src/core/project.py
git commit -m "feat(project): enable image download for HTML projects

- Set copy_images=True in convert_html_to_markdown_text
- External images will be downloaded to project images directory
- Failed downloads will preserve original URLs

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 集成测试与验证

**Files:**
- Test: 手动测试

- [ ] **Step 1: 准备测试 HTML 文件**

创建测试文件 `test_article.html`:

```html
<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<article>
<h1>Test Article</h1>
<p>This is a test article with images.</p>
<img src="https://substackcdn.com/image/fetch/$s_!TEST!,w_1456/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ftest.png" alt="Test Image 1">
<p>Another paragraph.</p>
<img src="https://example.com/image2.jpg" alt="Test Image 2">
</article>
</body>
</html>
```

- [ ] **Step 2: 通过 API 创建项目**

启动服务：
```bash
python -m src.api.app
```

使用 curl 或前端上传 `test_article.html`：
```bash
curl -X POST "http://localhost:54321/projects/upload" \
  -F "name=test-image-hosting" \
  -F "file=@test_article.html"
```

- [ ] **Step 3: 验证图片下载**

检查项目目录：
```bash
ls projects/test-image-hosting/images/
```

预期输出：
```
img_001.png
img_002.jpg
```

- [ ] **Step 4: 验证 source.md 中的 URL**

```bash
cat projects/test-image-hosting/source.md | grep "!\["
```

预期输出：
```
![Test Image 1](./test-image-hosting_images/img_001.png)
![Test Image 2](./test-image-hosting_images/img_002.jpg)
```

- [ ] **Step 5: 验证前端显示**

访问 `http://localhost:54321`，打开项目，检查图片是否正常显示。

- [ ] **Step 6: 验证日志输出**

检查服务日志：
```bash
tail -f logs/app.log | grep "image"
```

预期看到：
```
INFO: Downloaded image: https://... -> img_001.png
INFO: Downloaded image: https://... -> img_002.jpg
INFO: Image processing complete: downloaded: 2, failed: 0, total: 2
```

- [ ] **Step 7: 测试失败场景**

创建包含无效图片 URL 的 HTML：
```html
<img src="https://invalid-domain-12345.com/notfound.jpg" alt="Invalid">
```

上传并验证：
- 项目创建成功
- 日志显示下载失败
- source.md 保留原始 URL

- [ ] **Step 8: 清理测试数据**

```bash
rm -rf projects/test-image-hosting
rm test_article.html
```

---

## Task 5: 文档更新

**Files:**
- Modify: `docs/长文翻译链路.md`
- Create: `docs/图片处理说明.md`

- [ ] **Step 1: 更新长文翻译链路文档**

在 `docs/长文翻译链路.md` 的第 670 行附近添加说明：

```markdown
3. `copy_and_rewrite_images()` 复制或改写图片路径，保证 Markdown 里的图片引用可用。

**图片处理逻辑**：
- 外部图片（http/https）：自动下载到项目 `images/` 目录，使用顺序编号命名
- Substack CDN：自动解析真实 S3 地址后下载
- 本地图片：复制到项目目录
- 下载失败：保留原始 URL，记录警告日志
- 超时设置：30秒
```

- [ ] **Step 2: 创建图片处理说明文档**

创建 `docs/图片处理说明.md`:

```markdown
# 图片处理说明

## 概述

Translation Agent 在 HTML 转 Markdown 时会自动下载外部图片到本地，以便后续发布到微信公众号等平台。

## 功能特性

### 自动下载
- HTML 转 Markdown 时自动检测并下载所有外部图片
- 支持 Substack CDN、直接图片 URL、本地文件等多种来源
- 图片存储在项目的 `images/` 目录下

### 命名规则
- 使用顺序编号：`img_001.jpg`, `img_002.png`
- 保留原始文件扩展名
- 无扩展名时默认使用 `.jpg`

### URL 改写
- Markdown 中的图片 URL 改写为相对路径：`./images/img_xxx.ext`
- 前端访问时自动转换为：`/projects/{project_id}/images/img_xxx.ext`
- 导出时保持相对路径，适配微信公众号等平台

### 容错处理
- 单个图片下载失败不影响项目创建
- 失败的图片保留原始 URL
- 详细的日志记录便于排查问题

## 使用方式

### 通过 Web 界面
1. 上传 HTML 文件
2. 系统自动下载图片
3. 查看项目，图片已本地化

### 通过 API
```bash
curl -X POST "http://localhost:54321/projects/upload" \
  -F "name=my-project" \
  -F "file=@article.html"
```

## 配置参数

### 超时时间
- 默认：30秒
- 位置：`src/html2md/images.py:_copy_image()`

### User-Agent
- 默认：`Mozilla/5.0`
- 避免被反爬虫机制拦截

## 日志说明

### 成功日志
```
INFO: Downloaded image: https://example.com/img.jpg -> img_001.jpg
INFO: Image processing complete: downloaded: 5, failed: 0, total: 5
```

### 失败日志
```
WARNING: Failed to download image: https://example.com/bad.jpg, reason: HTTP Error 404
INFO: Image processing complete: downloaded: 4, failed: 1, total: 5
```

## 限制与注意事项

### 不支持的场景
- 需要认证的图片 URL
- 动态生成的图片（如验证码）
- 超大图片（>50MB）可能下载失败

### 存储空间
- 大量图片会占用磁盘空间
- 建议定期清理不需要的项目

### 网络依赖
- 图片下载依赖网络连接
- 网络问题可能导致下载失败
- 失败时会保留原始 URL

## 故障排查

### 图片下载失败
1. 检查网络连接
2. 查看日志中的错误信息
3. 验证图片 URL 是否有效
4. 检查是否需要特殊认证

### 图片显示异常
1. 检查 `images/` 目录是否存在
2. 验证图片文件是否完整
3. 检查前端路径转换是否正确

## 未来扩展

- 第三方图床集成（七牛云、阿里云 OSS）
- 图片压缩优化
- 图片去重
- 批量重新下载
```

- [ ] **Step 3: 提交文档更改**

```bash
git add docs/长文翻译链路.md docs/图片处理说明.md
git commit -m "docs: add image processing documentation

- Update translation pipeline docs with image download details
- Add comprehensive image processing guide
- Document configuration, logging, and troubleshooting

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 回归测试

**Files:**
- Test: 现有功能验证

- [ ] **Step 1: 测试 Markdown 直接输入**

创建测试 Markdown 文件：
```markdown
# Test

![](https://example.com/image.jpg)
```

通过 API 上传，验证：
- 项目创建成功
- 图片 URL 保持不变（Markdown 输入不触发图片下载）

- [ ] **Step 2: 测试长文翻译图片处理**

使用现有项目测试长文翻译流程：
```bash
# 选择一个已有项目
# 验证图片翻译、图注处理等功能正常
```

- [ ] **Step 3: 测试 copy_images=False 场景**

临时修改代码测试：
```python
copy_images=False
```

验证：
- 图片 URL 保持原样
- 不创建 images 目录

恢复代码：
```python
copy_images=True
```

- [ ] **Step 4: 运行所有单元测试**

```bash
pytest tests/test_html2md_images.py -v
```

预期输出：所有测试 PASS

- [ ] **Step 5: 运行集成测试**

```bash
pytest tests/ -k "html2md or project" -v
```

预期输出：所有测试 PASS

---

## 验收标准

### 功能验收
- [ ] HTML 转 Markdown 时自动下载外部图片
- [ ] 图片存储在 `projects/{project_id}/images/` 目录
- [ ] 使用顺序编号命名：`img_001.jpg`, `img_002.png`
- [ ] Markdown 中 URL 改写为 `./images/img_xxx.ext`
- [ ] 下载失败时保留原始 URL
- [ ] 前端正常显示图片
- [ ] 导出 Markdown 包含正确的相对路径

### 质量验收
- [ ] 所有单元测试通过
- [ ] 日志记录完整（成功、失败、统计）
- [ ] 错误处理健壮（超时、HTTP 错误、网络异常）
- [ ] 不影响现有功能（Markdown 输入、长文翻译）
- [ ] 代码符合项目规范

### 文档验收
- [ ] 更新长文翻译链路文档
- [ ] 创建图片处理说明文档
- [ ] 提交信息清晰完整

---

## 风险与缓解

### 风险1：图片下载时间过长
**影响**：项目创建速度变慢
**缓解**：
- 设置 30 秒超时
- 失败时不阻塞流程
- 考虑后续优化：异步下载、进度提示

### 风险2：存储空间占用
**影响**：磁盘空间不足
**缓解**：
- 文档中提醒用户定期清理
- 后续考虑：图片压缩、去重

### 风险3：网络依赖
**影响**：无网络时功能受限
**缓解**：
- 失败时保留原始 URL
- 详细日志便于排查
- 文档中说明限制

---

## 后续优化

1. **异步下载**：使用 asyncio 并发下载多张图片
2. **进度提示**：前端显示下载进度
3. **图片压缩**：自动压缩大图
4. **图片去重**：通过 hash 检测重复
5. **第三方图床**：支持七牛云、阿里云 OSS
6. **批量重新下载**：提供 API 重新下载失败的图片
