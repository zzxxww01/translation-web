# HTML 转 Markdown 图床功能设计

**日期**: 2026-04-18  
**状态**: 待实现  
**作者**: Claude Code

## 背景

当前系统在 HTML 转 Markdown 时保留了原始的外部图片 URL（如 Substack CDN）。这些外部图片在微信公众号等平台无法正常显示，因为：
1. Substack 对微信服务器进行了屏蔽
2. 外部图片链接可能失效或访问受限

需要在 HTML 转 Markdown 时自动下载外部图片到本地，并改写 URL 为相对路径，以便后续发布到微信公众号等平台。

## 需求

### 功能需求
1. HTML 转 Markdown 时自动下载所有外部图片
2. 图片存储在项目的 `images/` 目录下
3. 使用顺序编号命名：`img_001.jpg`, `img_002.png`
4. Markdown 中的图片 URL 改写为相对路径：`./images/img_xxx.ext`
5. 下载失败时保留原始 URL，不中断项目创建

### 非功能需求
1. 支持多种图片来源（Substack CDN、直接 URL、本地文件）
2. 容错处理，单个图片失败不影响整体
3. 不影响现有的长文翻译图片处理流程
4. 不影响 Markdown 直接输入的流程

## 技术方案

### 方案选择

**选定方案**：在 html2md 层直接集成图床

**理由**：
- 改动最小，只需修改 `src/html2md/images.py`
- 与现有的 `ImageProcessor`（用于长文翻译）解耦
- HTML 转换和长文翻译是两个独立流程，分开处理合理
- 快速上线，风险可控

**备选方案**：
- 方案二：统一使用 `ImageProcessor`（改动较大，需重构）
- 方案三：新建独立图床服务模块（过度设计）

### 架构设计

**数据流**：
```
HTML 文件 
  → extract_article() 提取正文
  → render_markdown() 转 Markdown（图片 URL 保持原样）
  → copy_and_rewrite_images() 下载外部图片 + 改写 URL
  → 最终 Markdown（图片已本地化）
```

**核心改动点**：
- 修改 `src/html2md/images.py` 的 `copy_and_rewrite_images()` 函数
- 修改 `src/core/project.py` 的 `ProjectManager.create()` 调用参数

**与现有代码的关系**：
- 不影响 `ImageProcessor`（用于长文翻译流程）
- 不影响 `ProjectManager.create()` 的主流程
- 图片存储位置与现有一致：`projects/{project_id}/images/`
- 前端访问路径与现有一致：`/projects/{project_id}/images/{filename}`

## 详细设计

### 图片检测与分类

**检测方式**：
通过正则表达式 `IMAGE_PATTERN` 匹配 Markdown 图片语法：
```python
IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<src><[^>]+>|[^)"]+?)(?:\s+"(?P<title>[^"]*)")?\)'
)
```

只处理 `![alt](url)` 格式，不会误判普通链接 `[text](url)`。

**URL 分类处理**：
1. **外部 URL**（`http://` 或 `https://` 开头）：
   - Substack CDN：先用 `_resolve_substack_cdn_url()` 解析真实 S3 地址
   - 其他外部图片：直接下载
2. **相对路径**（如 `./images/pic.jpg`）：保持现有逻辑，复制本地文件
3. **绝对路径**：保持现有逻辑

### 核心函数改造

#### 1. 修改 `_copy_image()` 函数

**当前逻辑**：
```python
def _copy_image(src: str, source_html_path: Path, target_path: Path) -> bool:
    # 1. 如果是 http/https，下载（已有）
    # 2. 否则当作本地文件复制（已有）
```

**新增功能**：
- 增加超时控制（30秒）
- 增加 User-Agent 头（避免反爬）
- 下载成功后保存到 `target_path`
- 返回 `True` 表示成功，`False` 表示失败

**实现要点**：
```python
def _copy_image(src: str, source_html_path: Path, target_path: Path) -> bool:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    if src.startswith(("http://", "https://")):
        try:
            request = urllib.request.Request(
                src, 
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 200:
                    with target_path.open("wb") as output:
                        output.write(response.read())
                    return True
        except Exception as e:
            # 记录错误日志
            return False
    
    # 本地文件复制逻辑（保持不变）
    source_path = (source_html_path.parent / src).resolve()
    if not source_path.exists():
        return False
    shutil.copy2(source_path, target_path)
    return True
```

#### 2. 修改 `copy_and_rewrite_images()` 函数

**当前参数**：
```python
def copy_and_rewrite_images(
    markdown: str,
    source_html_path: Path,
    output_dir: Path,
    basename: str,
    copy_images: bool,
) -> str:
```

**新增功能**：
- 当 `copy_images=True` 时，下载所有外部图片
- 使用顺序编号：`img_001.jpg`, `img_002.png`
- 失败时保留原始 URL，不中断处理
- 返回改写后的 Markdown

**实现要点**：
```python
def copy_and_rewrite_images(...) -> str:
    if not copy_images:
        return markdown
    
    # 创建图片目录
    images_dir_path = output_dir / f"{safe_basename}_images"
    if images_dir_path.exists():
        shutil.rmtree(images_dir_path, ignore_errors=True)
    
    replacements: dict[str, str] = {}
    counter = 1
    
    for match in IMAGE_PATTERN.finditer(markdown):
        src = _normalize_src(match.group("src"))
        if src in replacements:
            continue
        
        # 检测文件扩展名
        suffix = _detect_suffix(src) or ".jpg"
        target_name = f"img_{counter:03d}{suffix}"
        target_path = images_dir_path / target_name
        target_rel = f"./{images_dir_name}/{target_name}"
        
        # 下载或复制图片
        copied = _copy_image(src, source_html_path, target_path)
        
        # 成功则使用新路径，失败则保留原始 URL
        replacements[src] = target_rel if copied else src
        if copied:
            counter += 1
    
    # 替换 Markdown 中的 URL
    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        src = _normalize_src(match.group("src"))
        rewritten = replacements.get(src, src)
        title = match.group("title")
        title_part = f' "{title}"' if title else ""
        return f"![{alt}]({rewritten}{title_part})"
    
    return IMAGE_PATTERN.sub(replace, markdown)
```

#### 3. 修改调用入口

在 `src/core/project.py` 的 `ProjectManager.create()` 中：

**当前代码**（第 870-874 行）：
```python
source_md, metadata = convert_html_to_markdown_text(
    html_path=html_path,
    output_dir=project_dir,
    copy_images=False,  # 当前为 False
)
```

**修改为**：
```python
source_md, metadata = convert_html_to_markdown_text(
    html_path=html_path,
    output_dir=project_dir,
    copy_images=True,  # 改为 True，启用图片下载
)
```

### 错误处理

**错误处理策略**：

1. **单个图片失败**：
   - 记录警告日志
   - 保留原始 URL 在 Markdown 中
   - 继续处理其他图片
   - 项目创建成功

2. **常见错误类型**：
   - 网络超时（timeout=30秒）
   - HTTP 错误（404, 403, 500等）
   - 文件格式不支持
   - 磁盘空间不足

3. **日志记录**：
   ```python
   # 成功
   logger.info(f"Downloaded image {counter}: {url} -> {filename}")
   
   # 失败
   logger.warning(f"Failed to download image: {url}, reason: {error}, keeping original URL")
   
   # 统计
   logger.info(f"Image processing complete: {success}/{total} downloaded, {failed} failed")
   ```

**图片下载配置**：
- 超时时间：30秒
- User-Agent：`Mozilla/5.0`（避免被反爬）
- 重试次数：1次（避免阻塞太久）
- 支持的格式：`.jpg, .jpeg, .png, .gif, .webp, .svg`

### API 与前端集成

**API 层面**：

无需新增 API 端点，现有流程自动支持：
- `POST /projects/upload`：上传 HTML 时自动下载图片
- `POST /projects`：从本地 HTML 创建项目时自动下载图片
- `GET /projects/{project_id}/images/{filename}`：前端访问图片（已有）

**前端显示**：

现有代码已支持项目图片路径转换（`src/api/routers/projects_management.py:247-260`）：
```python
def _normalize_image_source(paragraph) -> str:
    if paragraph.element_type != ElementType.IMAGE:
        return paragraph.source
    return _project_asset_url(project_id, paragraph.source) or paragraph.source
```

图片 URL 自动转换：
- 存储：`./images/img_001.jpg`（相对路径）
- 前端：`/projects/{project_id}/images/img_001.jpg`（绝对路径）

**导出功能**：

导出 Markdown 时保持相对路径 `./images/img_001.jpg`，适配微信公众号等平台：
- 用户可以将整个项目目录（包含 images 文件夹）一起导出
- 或者手动上传图片到微信公众号素材库

## 测试计划

### 测试场景

**1. 正常场景**：
- Substack 文章（多张 CDN 图片）
- 其他网站文章（直接图片 URL）
- 混合图片（外部 + 本地）

**2. 边界场景**：
- 图片 URL 无扩展名
- 图片下载失败（404, 超时）
- 重复图片 URL
- 空 alt 文本

**3. 验证点**：
- 图片文件正确保存到 `projects/{project_id}/images/`
- Markdown 中 URL 正确改写为 `./images/img_xxx.ext`
- 前端能正常显示图片
- 导出的 Markdown 包含正确的相对路径
- 失败的图片保留原始 URL

### 回归测试

- 确保不影响现有的 Markdown 输入流程
- 确保不影响长文翻译的图片处理（`ImageProcessor`）
- 确保 `copy_images=False` 时行为不变

## 实现计划

### 阶段一：核心功能实现
1. 修改 `src/html2md/images.py` 的 `_copy_image()` 函数
2. 修改 `src/html2md/images.py` 的 `copy_and_rewrite_images()` 函数
3. 修改 `src/core/project.py` 的调用参数

### 阶段二：错误处理与日志
1. 添加详细的错误日志
2. 添加统计信息输出
3. 处理各种异常情况

### 阶段三：测试与验证
1. 单元测试
2. 集成测试
3. 回归测试

## 风险与限制

### 风险
1. **网络依赖**：图片下载依赖网络，可能因网络问题失败
2. **存储空间**：大量图片会占用磁盘空间
3. **下载时间**：图片较多时可能影响项目创建速度

### 限制
1. 不支持需要认证的图片 URL
2. 不支持动态生成的图片（如验证码）
3. 超大图片（>50MB）可能下载失败

### 缓解措施
1. 设置合理的超时时间（30秒）
2. 失败时保留原始 URL，不中断流程
3. 记录详细日志，便于排查问题

## 未来扩展

1. **第三方图床集成**：支持配置七牛云、阿里云 OSS 等
2. **图片压缩**：自动压缩大图，节省空间和带宽
3. **图片去重**：通过 hash 检测重复图片
4. **批量重新下载**：提供 API 重新下载失败的图片
5. **图片 CDN**：为自建图床添加 CDN 加速

## 参考资料

- 现有代码：`src/html2md/images.py`
- 现有代码：`src/core/project.py`
- 现有代码：`src/core/image_processor.py`
- 项目文档：`docs/长文翻译链路.md`

## 实现状态

**实现日期**: 2026-04-18  
**状态**: 已完成

### 已实现功能

1. 修改 `_copy_image()` 函数，支持外部图片下载
   - 添加 30 秒超时控制
   - 添加 User-Agent 头避免反爬
   - 增强错误处理和日志记录

2. 修改 `copy_and_rewrite_images()` 函数
   - 支持外部图片自动下载
   - 使用顺序编号命名（`img_001.jpg`）
   - 失败时保留原始 URL，不中断流程

3. 启用项目创建时的图片下载
   - 修改 `ProjectManager.create()` 调用参数
   - 将 `copy_images` 设置为 `True`

4. 完善错误处理机制
   - 单个图片失败不影响整体流程
   - 详细的错误日志记录
   - 网络超时、HTTP 错误等异常处理

5. 添加图片处理统计日志
   - 记录成功/失败/跳过的图片数量
   - 便于监控和问题排查

6. 完整的测试覆盖
   - 单元测试：8 个
   - 集成测试：10 个

### 关键提交记录

- `9140049`: feat(html2md): enhance image download with timeout and logging
- `e9475aa`: refactor(html2md): optimize logging and simplify HTTP status check
- `1e35a33`: feat(project): enable image downloading for HTML sources
- `7a85a94`: test(html2md): add comprehensive integration tests
- 最新提交: feat(html2md): add image processing statistics logging

### 测试覆盖

**单元测试** (`tests/test_html2md_images.py`): 8 个
- `_copy_image()` 函数测试：3 个
  - 外部 URL 下载
  - 本地文件复制
  - 错误处理
- 统计日志测试：5 个
  - 成功下载统计
  - 失败处理统计
  - 跳过图片统计
  - 混合场景统计
  - 空图片列表处理

**集成测试** (`tests/test_html2md_integration.py`): 10 个
- 完整流程测试（HTML → Markdown + 图片下载）
- 失败处理测试（404、超时、保留原始 URL）
- 图片格式检测测试（无扩展名、Content-Type 检测）
- 图片去重测试（重复 URL 只下载一次）
- CDN URL 处理测试（Substack CDN 解析）
- 边界场景测试（空 alt、特殊字符等）

### 已知限制

1. **超时时间固定**: 当前设置为 30 秒，未来可考虑配置化
2. **支持的图片格式**: 仅支持常见格式（jpg, png, gif, webp, svg）
3. **认证限制**: 不支持需要认证的图片 URL
4. **文件大小**: 超大图片（>50MB）可能因超时失败

### 未来改进方向

1. 可配置的超时时间和重试策略
2. 支持更多图片格式（bmp, tiff 等）
3. 图片压缩和优化（减少存储空间）
4. 第三方图床集成（七牛云、阿里云 OSS）
5. 图片 hash 去重（跨项目复用）
