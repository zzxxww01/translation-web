"""
微信公众号格式转换服务
"""

import base64
import re
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
from ..core.image_processor import ImageProcessor


class WechatFormatter:
    """微信公众号格式转换器"""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or "wechat_temp"
        self.image_processor = ImageProcessor(self.project_id, base_dir="projects")

        if MarkdownIt is None:
            raise ImportError("markdown-it-py is required. Install: pip install markdown-it-py")

        self.md = MarkdownIt("commonmark", {"html": True})
        self.md.enable(["table", "strikethrough"])

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
                "html": "格式化后的 HTML",
                "image_count": 图片数量,
                "image_urls": ["图片URL列表"]
            }
        """
        # 1. 解析 Markdown
        html = self.md.render(markdown)

        # 2. 代码高亮
        html = self._highlight_code(html)

        # 3. 处理图片
        image_info = {"count": 0, "urls": []}
        if upload_images or image_to_base64:
            html, image_info = self._process_images(html, upload_images, image_to_base64)

        # 4. 应用主题样式
        theme_css = get_theme(theme)
        html = self._apply_theme(html, theme_css)

        # 5. 微信兼容性修复
        html = self._apply_wechat_fixes(html)

        return {
            "html": html,
            "image_count": image_info["count"],
            "image_urls": image_info["urls"],
        }

    def _highlight_code(self, html: str) -> str:
        """代码高亮"""
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

                formatter = HtmlFormatter(style="monokai", noclasses=True, nowrap=False)
                highlighted = highlight(code_text, lexer, formatter)

                # 替换 pre 标签内容
                new_pre = BeautifulSoup(highlighted, "html.parser")
                pre.replace_with(new_pre)

            except (ClassNotFound, Exception):
                # 高亮失败，保持原样
                pass

        return str(soup)

    def _process_images(self, html: str, upload: bool, to_base64: bool) -> tuple[str, dict]:
        """处理图片"""
        soup = BeautifulSoup(html, "html.parser")
        images = soup.find_all("img")

        image_urls = []
        processed_count = 0

        for img in images:
            src = img.get("src", "")
            if not src or src.startswith("data:"):
                continue

            try:
                if upload:
                    # TODO: 实现图床上传逻辑
                    # 这里暂时保持原链接
                    image_urls.append(src)
                    processed_count += 1
                elif to_base64:
                    # 转 Base64
                    base64_src = self._image_to_base64(src)
                    if base64_src:
                        img["src"] = base64_src
                        processed_count += 1
            except Exception as e:
                # 处理失败，保持原链接
                pass

        return str(soup), {"count": processed_count, "urls": image_urls}

    def _image_to_base64(self, url: str) -> Optional[str]:
        """将图片转为 Base64"""
        try:
            import urllib.request

            if url.startswith(("http://", "https://")):
                request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=10) as response:
                    content = response.read()
            else:
                # 本地文件
                with open(url, "rb") as f:
                    content = f.read()

            # 检测图片类型
            if content[:4] == b"\x89PNG":
                mime = "image/png"
            elif content[:2] == b"\xff\xd8":
                mime = "image/jpeg"
            elif content[:4] == b"GIF8":
                mime = "image/gif"
            else:
                mime = "image/png"

            b64 = base64.b64encode(content).decode()
            return f"data:{mime};base64,{b64}"

        except Exception:
            return None

    def _apply_theme(self, html: str, theme_css: str) -> str:
        """应用主题样式（CSS 内联化）"""
        if not theme_css:
            return html

        # 包裹在 div 中
        full_html = f"<style>{theme_css}</style><div class='wechat-content'>{html}</div>"

        # 使用 premailer 内联化
        if premailer_transform:
            try:
                inlined = premailer_transform(full_html)
                # 提取 body 内容
                soup = BeautifulSoup(inlined, "html.parser")
                body = soup.find("body")
                return str(body) if body else inlined
            except Exception:
                pass

        # 降级：直接返回带 style 标签的 HTML
        return full_html

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

        # 图片居中
        for img in soup.find_all("img"):
            style = img.get("style", "")
            if "display" not in style:
                img["style"] = f"{style};max-width:100%;height:auto;display:block;margin:1.5em auto;"

        return str(soup)
