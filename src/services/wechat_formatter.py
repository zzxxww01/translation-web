"""
微信公众号格式转换服务
"""

import atexit
import base64
import re
import weakref
from html import escape as html_escape
from typing import Optional
from pathlib import Path

try:
    from markdown_it import MarkdownIt
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound
except ImportError:
    MarkdownIt = None
    highlight = None
    get_lexer_by_name = None
    guess_lexer = None
    HtmlFormatter = None
    ClassNotFound = None

try:
    from premailer import transform as premailer_transform
except ImportError:
    premailer_transform = None

from bs4 import BeautifulSoup

from .wechat_themes import get_theme
from ..core.markdown_postprocess import normalize_math_fragment
from ..core.image_processor import ImageProcessor


def _sanitize_url_for_log(url: str) -> str:
    """
    清理 URL 用于日志记录，移除敏感参数

    防止泄露：
    - 认证 token（如 ?token=secret）
    - API 密钥
    - 会话 ID
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        # 只保留 scheme, netloc, path，移除查询参数和片段
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        # 解析失败，返回占位符
        return "[URL]"


def _sanitize_project_id(project_id: str) -> str:
    """
    清理 project_id，防止路径遍历攻击

    只允许字母、数字、下划线、连字符
    限制长度为 200 字符（内部使用，放宽限制）
    """
    if not project_id or not project_id.strip():
        return "default_project"

    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)

    # 验证清理后的值不为空或全下划线
    if not sanitized.strip('_'):
        return "default_project"

    # 限制长度
    if len(sanitized) > 200:
        sanitized = sanitized[:200]

    return sanitized


def _is_safe_url(url: str) -> bool:
    from ..core.url_safety import is_safe_url
    return is_safe_url(url)


def _is_safe_ip(ip_str: str) -> bool:
    from ..core.url_safety import is_safe_ip
    return is_safe_ip(ip_str)



def _repair_math_fragment(raw: str) -> str:
    """规范化带定界符的公式：定界符原样留下，只修中间的正文。"""
    for opening, closing in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if raw.startswith(opening) and raw.endswith(closing) and len(raw) > len(opening) + len(closing) - 1:
            body = raw[len(opening) : -len(closing)]
            return f"{opening}{normalize_math_fragment(body)}{closing}"
    if len(raw) >= 2 and raw.startswith("$") and raw.endswith("$"):
        return f"${normalize_math_fragment(raw[1:-1])}$"
    return normalize_math_fragment(raw)


class WechatFormatter:
    """微信公众号格式转换器"""

    def __init__(self, project_id: Optional[str] = None):
        from concurrent.futures import ThreadPoolExecutor

        raw_id = project_id or "wechat_temp"
        self.project_id = _sanitize_project_id(raw_id)  # 清理后再使用
        self.image_processor = ImageProcessor(self.project_id, base_dir="projects")

        # 实例级线程池，避免多用户并发时的竞态条件
        self._image_executor = ThreadPoolExecutor(max_workers=5)

        if MarkdownIt is None:
            raise ImportError("markdown-it-py is required. Install: pip install markdown-it-py")

        self.md = MarkdownIt("commonmark", {"html": True})
        self.md.enable(["table", "strikethrough"])
        self._executor_finalizer = weakref.finalize(
            self,
            self._shutdown_executor,
            self._image_executor,
        )

    def __del__(self):
        """清理线程池资源"""
        finalizer = getattr(self, "_executor_finalizer", None)
        if finalizer is not None and finalizer.alive:
            finalizer()

    @staticmethod
    def _shutdown_executor(executor) -> None:
        if executor is None:
            return
        try:
            executor.shutdown(wait=False)
        except Exception:
            logger = __import__("logging").getLogger(__name__)
            logger.debug("Failed to shut down WechatFormatter executor", exc_info=True)

    def format(
        self,
        markdown: str,
        theme: str = "default",
        upload_images: bool = True,
        image_to_base64: bool = False,
    ) -> dict:
        """
        转换 Markdown 为微信公众号格式

        Args:
            markdown: Markdown 文本
            theme: 主题名称
            upload_images: 是否上传图片到图床
            image_to_base64: 是否将图片转为 Base64（优先级低于 upload_images）

        Returns:
            {
                "html": "格式化后的 HTML（纯HTML，不含CSS）",
                "css": "主题CSS样式",
                "image_count": 图片数量,
                "image_urls": ["图片URL列表"]
            }
        """
        # 1. 获取主题CSS（先获取，后面要返回）
        theme_css = get_theme(theme)

        # 2. 先把数学公式摘出来。CommonMark 不认 `$$`，而公式里的下标 `_` 会被
        #    markdown-it 当成强调定界符成对吞掉：
        #      `\mathbf{v}_i, \qquad \alpha_{i\to t}` → `\mathbf{v}<em>i, \qquad \alpha</em>{i\to t}`
        #    公式因此既丢字符又多出 <em>。必须在 render 之前替换成惰性占位符。
        markdown, formulas = self._extract_math(markdown)

        # 3. 解析 Markdown
        html = self.md.render(markdown)

        # 4. 代码高亮
        html = self._highlight_code(html)

        # 5. 还原公式。放在代码高亮之后、微信兼容修复之前：高亮器不会碰它，
        #    而兼容修复里的 <code> 规则会因为我们已写了 white-space 而跳过。
        html = self._restore_math(html, formulas)

        # 6. 处理图片
        image_info = {"count": 0, "urls": []}
        if upload_images or image_to_base64:
            html, image_info = self._process_images(html, upload_images, image_to_base64)

        # 7. 微信兼容性修复
        html = self._apply_wechat_fixes(html)

        # 8. 安全:消毒 HTML,移除 XSS 向量。MarkdownIt 开启了 html:True 透传裸 HTML,
        #    若不消毒,用户 markdown 中的 <script>/<img onerror> 会在前端预览 iframe 内执行。
        html = self._sanitize_html(html)

        return {
            "html": html,
            "css": theme_css,
            "image_count": image_info["count"],
            "image_urls": image_info["urls"],
            # 前端据此提示：微信公众号不支持数学排版，公式按等宽原样呈现。
            "formula_count": len(formulas),
        }

    # 数学公式。块级在前，避免 `$$` 被行内规则拆成两个空公式。
    # 行内 `$...$` 用 Pandoc 规则：开定界符后非空白、闭定界符前非空白、闭定界符后
    # 不跟数字——否则「$100 到 $200」这类价格会被当成公式。
    _MATH_PATTERN = re.compile(
        r"(?P<block>\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])"
        r"|(?P<inline>\\\([\s\S]*?\\\)|\$(?![\s$])[^$\n]*[^\s$]\$(?![\d$]))"
    )
    # 占位符必须是纯小写字母数字：任何标点都可能被 CommonMark 解释掉。
    _MATH_TOKEN = "xxmathxx{index}xx"
    _MATH_TOKEN_RE = re.compile(r"xxmathxx(\d+)xx")

    _MATH_BLOCK_STYLE = (
        "margin:16px 0;padding:12px 14px;background:#f7f8fa;"
        "border-left:3px solid #d0d5dd;border-radius:4px;overflow-x:auto;"
    )
    _MATH_CODE_STYLE = (
        "font-family:Consolas,Menlo,'Liberation Mono',monospace;font-size:14px;"
        "line-height:1.7;color:#1f2328;white-space:pre-wrap;word-break:normal;"
        "background:transparent;padding:0;"
    )
    _MATH_INLINE_STYLE = (
        "font-family:Consolas,Menlo,'Liberation Mono',monospace;font-size:0.95em;"
        "padding:0 3px;background:#f2f4f7;border-radius:3px;"
        "white-space:pre-wrap;word-break:normal;"
    )

    def _extract_math(self, markdown: str) -> tuple[str, list[tuple[str, str]]]:
        """把公式换成惰性占位符，返回 (替换后的 markdown, [(kind, latex)])。"""
        if "$" not in markdown and "\\[" not in markdown and "\\(" not in markdown:
            return markdown, []

        formulas: list[tuple[str, str]] = []

        def _stash(match: re.Match[str]) -> str:
            raw = match.group("block") or match.group("inline") or ""
            kind = "block" if match.group("block") else "inline"
            # 就地修翻译带来的转义污染（`\backslash ` / `\_`）。导出链路有
            # postprocess_markdown 兜着，但排版这条路没有——用户粘进来的往往是
            # 早就生成好的译文，不在这里修，公式就会渲染成字面的 `\mathbfq\_l`。
            raw = _repair_math_fragment(raw)
            formulas.append((kind, raw))
            token = self._MATH_TOKEN.format(index=len(formulas) - 1)
            # 块级公式两侧留空行，确保 markdown-it 把它当成独立段落而不是并进上一段
            return f"\n\n{token}\n\n" if kind == "block" else token

        return self._MATH_PATTERN.sub(_stash, markdown), formulas

    @staticmethod
    def _strip_math_delimiters(raw: str) -> str:
        """剥掉 `$$` / `$` / `\\[ \\]` / `\\( \\)`，留下纯 LaTeX 供渲染器使用。"""
        text = raw.strip()
        for opening, closing in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)")):
            if text.startswith(opening) and text.endswith(closing):
                return text[len(opening) : -len(closing)].strip()
        if len(text) >= 2 and text.startswith("$") and text.endswith("$"):
            return text[1:-1].strip()
        return text

    def _restore_math(self, html: str, formulas: list[tuple[str, str]]) -> str:
        """把占位符换回公式节点。

        公众号没有 MathJax/KaTeX 运行环境，正文里也不执行 JS，所以公式只能在
        **发布前**变成图形。节点上带 ``data-latex``，由前端在预览与复制时用
        MathJax 渲染成独立 SVG（公众号正文支持以 DOM 形式内嵌 SVG）。

        节点内容保留等宽 LaTeX 原文作为**降级**：渲染器加载失败或某条公式语法
        有误时，用户至少拿到不丢字符、不被强调标记污染的原文，而不是空白。
        """
        if not formulas:
            return html

        def _block_html(latex: str) -> str:
            inner = html_escape(self._strip_math_delimiters(latex), quote=True)
            return (
                f'<section data-formula="block" data-latex="{inner}"'
                f' style="{self._MATH_BLOCK_STYLE}">'
                f'<code style="{self._MATH_CODE_STYLE}">{html_escape(latex)}</code>'
                f"</section>"
            )

        def _inline_html(latex: str) -> str:
            inner = html_escape(self._strip_math_delimiters(latex), quote=True)
            return (
                f'<code data-formula="inline" data-latex="{inner}"'
                f' style="{self._MATH_INLINE_STYLE}">{html_escape(latex)}</code>'
            )

        def _render(index_text: str) -> str:
            try:
                kind, latex = formulas[int(index_text)]
            except (ValueError, IndexError):
                return ""
            return _block_html(latex) if kind == "block" else _inline_html(latex)

        # 独占一段的占位符：连同外层 <p> 一起换掉，避免 <section> 嵌进 <p> 变成非法 HTML
        html = re.sub(
            r"<p>\s*xxmathxx(\d+)xx\s*</p>",
            lambda m: _render(m.group(1)),
            html,
        )
        return self._MATH_TOKEN_RE.sub(lambda m: _render(m.group(1)), html)

    def _highlight_code(self, html: str) -> str:
        """代码高亮"""
        import logging
        logger = logging.getLogger(__name__)
        if highlight is None or HtmlFormatter is None:
            return html

        soup = BeautifulSoup(html, "html.parser")

        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if not code:
                continue

            code_text = code.get_text()
            lang = code.get("class", [""])[0].replace("language-", "") if code.get("class") else ""

            try:
                if lang:
                    lexer = get_lexer_by_name(lang, stripall=True)
                else:
                    lexer = guess_lexer(code_text)

                # 浅色高亮 + 不输出背景：monokai 是深色主题，它自带的
                # `background:#272822` 会盖在主题的浅色 pre 上，公众号里就是
                # 一圈突兀的黑框，亮色代码字压在浅色底上还几乎看不清。
                # 背景交给主题 CSS（--md-code-bg）统一控制。
                formatter = HtmlFormatter(
                    style="default", noclasses=True, nowrap=False, nobackground=True
                )
                highlighted = highlight(code_text, lexer, formatter)

                # 替换 pre 标签内容
                new_pre = BeautifulSoup(highlighted, "html.parser")
                pre.replace_with(new_pre)

            except ClassNotFound:
                logger.debug(f"Lexer not found for language: {lang}")
                # 保持原样
            except Exception as e:
                logger.warning(f"Code highlighting failed: {e}")
                # 保持原样

        return str(soup)

    def _process_images(self, html: str, upload: bool, to_base64: bool) -> tuple[str, dict]:
        """处理图片（并发处理）"""
        import logging
        from concurrent.futures import as_completed

        logger = logging.getLogger(__name__)

        soup = BeautifulSoup(html, "html.parser")
        images = soup.find_all("img")

        logger.info(f"Found {len(images)} images, upload={upload}, to_base64={to_base64}")

        image_urls = []
        processed_count = 0
        failed_count = 0
        errors = []

        # 并发处理图片
        def process_single_image(img_tag):
            src = img_tag.get("src", "")
            if not src or src.startswith("data:"):
                return None, None

            try:
                if upload:
                    new_url = self._upload_to_local(src)
                    return img_tag, new_url if new_url else None
                elif to_base64:
                    base64_src = self._image_to_base64(src)
                    return img_tag, base64_src if base64_src else None
            except Exception as e:
                logger.error(f"Failed to process {_sanitize_url_for_log(src)}: {e}")
                return img_tag, None

            return img_tag, None

        # 使用类级线程池并发处理（最多5个并发）
        futures = {self._image_executor.submit(process_single_image, img): img for img in images}

        for future in as_completed(futures):
            try:
                img_tag, new_src = future.result()
                if img_tag and new_src:
                    img_tag["src"] = new_src
                    if upload:
                        image_urls.append(new_src)
                    processed_count += 1
                elif img_tag:
                    # 处理失败但没有抛出异常
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                errors.append(error_msg)
                logger.error(f"Image processing failed: {e}")

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count}/{len(images)} images")
            if errors:
                logger.debug(f"Error details: {errors[:3]}")  # 只记录前3个错误

        logger.info(f"Processed {processed_count}/{len(images)} images successfully")
        return str(soup), {"count": processed_count, "urls": image_urls, "failed": failed_count}

    def _upload_to_local(self, url: str) -> Optional[str]:
        """上传到自建图床（保存到本地projects目录）"""
        import hashlib
        import uuid
        from datetime import datetime
        import logging
        import shutil
        import os

        logger = logging.getLogger(__name__)
        logger.debug(f"Uploading to local: {_sanitize_url_for_log(url)}")

        # 允许的文件扩展名白名单
        ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

        local_path = None
        try:
            # 使用同步下载
            local_path = self._download_image_sync(url)
            if not local_path or not Path(local_path).exists():
                logger.warning(f"Download failed: {_sanitize_url_for_log(url)}")
                return None

            # 验证文件扩展名
            ext = Path(local_path).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                logger.warning(f"Invalid file extension: {ext}, defaulting to .jpg")
                ext = ".jpg"

            # 生成唯一文件名（使用 UUID 避免冲突）
            unique_id = uuid.uuid4().hex[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wechat_{timestamp}_{unique_id}{ext}"

            # 保存到projects/wechat_images目录
            target_dir = Path("projects") / self.project_id / "wechat_images"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / filename

            # 使用 resolve() 确保路径在预期目录内（防止路径遍历）
            target_path_resolved = target_path.resolve()
            target_dir_resolved = target_dir.resolve()
            if not target_path_resolved.is_relative_to(target_dir_resolved):
                raise ValueError("Invalid target path")

            # 复制文件
            shutil.copy2(local_path, target_path)
            logger.debug(f"Saved to: {target_path}")

            # 通过受限的项目图片 API 暴露；公网 Nginx 的 /projects 路径由 SPA
            # 接管，且直接开放整个项目目录会泄露 meta/运行工件。
            return f"/api/projects/{self.project_id}/assets/wechat_images/{filename}"

        except Exception as e:
            logger.error(f"Failed to upload image to local: {e}", exc_info=True)
            return None
        finally:
            # 清理临时文件
            if local_path:
                try:
                    os.unlink(local_path)
                    logger.debug(f"Cleaned up temp file: {local_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {local_path}: {e}")

    def _download_image_sync(self, url: str) -> Optional[str]:
        """同步下载图片（用于base64转换和图床上传）"""
        import logging
        import tempfile
        from ..core.public_resources import fetch_public_bytes, confined_local_path

        logger = logging.getLogger(__name__)
        temp_path = None
        try:
            limit = 10 * 1024 * 1024
            if url.startswith(("http://", "https://")):
                content, headers = fetch_public_bytes(url, timeout=20, max_bytes=limit)
                content_type = headers.get("content-type", "")
            else:
                root = Path("projects") / self.project_id
                # API asset URLs and relative project paths are accepted, never arbitrary host files.
                prefix = f"/api/projects/{self.project_id}/assets/"
                src = url[len(prefix):] if url.startswith(prefix) else url
                path = confined_local_path(src, root)
                if path is None or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}:
                    return None
                with path.open("rb") as file:
                    content = file.read(limit + 1)
                if len(content) > limit:
                    raise ValueError("Local image exceeds size limit")
                import mimetypes
                content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            ext = next((suffix for mime, suffix in (("png", ".png"), ("gif", ".gif"), ("webp", ".webp"))
                        if mime in content_type), ".jpg")
            # Always return an owned temporary copy: callers unlink this path in finally.
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as file:
                temp_path = file.name
                file.write(content)
            return temp_path
        except Exception:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
            logger.warning("Failed to read public/project image", exc_info=True)
            return None

    def _image_to_base64(self, url: str) -> Optional[str]:
        """将图片转为 Base64"""
        import logging
        import os

        logger = logging.getLogger(__name__)
        logger.debug(f"Converting image to base64: {_sanitize_url_for_log(url)}")

        local_path = None
        try:
            # 下载图片
            local_path = self._download_image_sync(url)

            if not local_path or not Path(local_path).exists():
                logger.warning(f"Download failed or file not exists: {local_path}")
                return None

            # 读取文件内容
            with open(local_path, "rb") as f:
                content = f.read()

            logger.debug(f"Read {len(content)} bytes from {local_path}")

            # 限制图片大小（防止内存溢出）
            MAX_SIZE = 2 * 1024 * 1024  # 2MB
            if len(content) > MAX_SIZE:
                logger.warning(f"Image too large for base64: {len(content)} bytes (max {MAX_SIZE})")
                return None

            # 检测图片类型
            if content[:4] == b"\x89PNG":
                mime = "image/png"
            elif content[:2] == b"\xff\xd8":
                mime = "image/jpeg"
            elif content[:4] == b"GIF8":
                mime = "image/gif"
            elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                mime = "image/png"

            b64 = base64.b64encode(content).decode()
            logger.debug(f"Successfully converted to base64, mime={mime}, length={len(b64)}")
            return f"data:{mime};base64,{b64}"

        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}", exc_info=True)
            return None
        finally:
            # 清理临时文件
            if local_path:
                try:
                    os.unlink(local_path)
                    logger.debug(f"Cleaned up temp file: {local_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {local_path}: {e}")

    def _apply_theme(self, html: str, theme_css: str) -> str:
        """应用主题样式（不内联化，返回HTML和CSS）"""
        # 直接返回HTML，不做内联化
        # 前端会在预览时用iframe隔离，复制时才内联化
        return html

    def _apply_wechat_fixes(self, html: str) -> str:
        """微信兼容性修复"""
        soup = BeautifulSoup(html, "html.parser")

        # 表格固定宽度
        for table in soup.find_all("table"):
            style = table.get("style", "")
            if "width" not in style:
                table["style"] = f"{style};width:100%;border-collapse:collapse;"

        # 代码块防溢出
        for code in soup.find_all("code"):
            if code.parent.name != "pre":
                style = code.get("style", "")
                if "white-space" not in style:
                    code["style"] = f"{style};white-space:pre-wrap;word-break:break-all;"

        # 标题外壳：把内容包进 span，让"收缩成居中标签"的效果落到 inline-block 上。
        # 主题原先用 `display:table` + `margin:auto` 实现收缩居中，但公众号不支持
        # table 显示类型——失效后标题退回块级，铺满整行变成一条大色块（用户实拍）。
        # inline-block 是公众号支持的，外层标题只负责 text-align:center。
        for heading in soup.find_all(["h1", "h2"]):
            children = [child for child in heading.children]
            if (
                len(children) == 1
                and getattr(children[0], "name", None) == "span"
                and "wx-heading-label" in (children[0].get("class") or [])
            ):
                continue  # 幂等：已经包过就不再套一层
            label = soup.new_tag("span")
            label["class"] = "wx-heading-label"
            for child in list(heading.contents):
                label.append(child.extract())
            heading.append(label)

        # 图片居中
        for img in soup.find_all("img"):
            style = img.get("style", "")
            if "display" not in style:
                img["style"] = f"{style};max-width:100%;height:auto;display:block;margin:1.5em auto;"

        return str(soup)

    def _sanitize_html(self, html: str) -> str:
        """安全:消毒 HTML,剥离 XSS 向量(危险标签 / on* 事件 / javascript: 等协议)。"""
        soup = BeautifulSoup(html, "html.parser")
        DANGEROUS_TAGS = {
            "script", "iframe", "object", "embed", "form", "input", "button",
            "link", "meta", "base", "style", "svg", "math", "applet",
            "frame", "frameset", "template",
        }
        for tag in soup.find_all(DANGEROUS_TAGS):
            tag.decompose()
        for tag in soup.find_all(True):
            for attr in list(tag.attrs):
                attr_lower = attr.lower()
                if attr_lower.startswith("on"):
                    del tag.attrs[attr]
                    continue
                if attr_lower in ("href", "src", "xlink:href", "action", "formaction"):
                    normalized = re.sub(r"\s+", "", str(tag.attrs[attr]).strip().lower())
                    if normalized.startswith(("javascript:", "vbscript:", "data:text/html")):
                        del tag.attrs[attr]
                elif attr_lower == "style":
                    value = str(tag.attrs[attr]).lower()
                    if "javascript:" in value or "expression(" in value or "behavior:" in value:
                        del tag.attrs[attr]
        return str(soup)

atexit.register(lambda: None)
