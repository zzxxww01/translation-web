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
    限制长度为 64 字符
    """
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
    return sanitized[:64]


def _is_safe_url(url: str) -> bool:
    """
    检查 URL 是否安全（防止 SSRF 攻击）

    阻止访问：
    - 内网地址（192.168.x.x, 10.x.x.x, 172.16-31.x.x）
    - 本地地址（localhost, 127.0.0.1, ::1）
    - 非 HTTP/HTTPS 协议
    """
    from urllib.parse import urlparse
    import ipaddress

    try:
        parsed = urlparse(url)

        # 只允许 http/https
        if parsed.scheme not in ('http', 'https'):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # 禁止 localhost
        if hostname.lower() in ('localhost', '127.0.0.1', '::1'):
            return False

        # 尝试解析为 IP 地址
        try:
            ip = ipaddress.ip_address(hostname)
            # 禁止私有 IP 和保留 IP
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            # 不是 IP 地址，是域名，允许通过
            pass

        return True
    except Exception:
        return False


def _is_safe_ip(ip_str: str) -> bool:
    """
    检查 IP 地址是否安全（防止 DNS Rebinding）

    在实际连接时调用，防止 DNS 在检查后被修改
    """
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_str)
        # 禁止私有 IP、回环地址、链路本地地址
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
        return True
    except ValueError:
        return False


class WechatFormatter:
    """微信公众号格式转换器"""

    # 类级线程池，所有实例共享
    from concurrent.futures import ThreadPoolExecutor
    _image_executor = ThreadPoolExecutor(max_workers=5)

    def __init__(self, project_id: Optional[str] = None):
        raw_id = project_id or "wechat_temp"
        self.project_id = _sanitize_project_id(raw_id)  # 清理后再使用
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
                "html": "格式化后的 HTML（纯HTML，不含CSS）",
                "css": "主题CSS样式",
                "image_count": 图片数量,
                "image_urls": ["图片URL列表"]
            }
        """
        # 1. 获取主题CSS（先获取，后面要返回）
        theme_css = get_theme(theme)

        # 2. 解析 Markdown
        html = self.md.render(markdown)

        # 3. 代码高亮
        html = self._highlight_code(html)

        # 4. 处理图片
        image_info = {"count": 0, "urls": []}
        if upload_images or image_to_base64:
            html, image_info = self._process_images(html, upload_images, image_to_base64)

        # 5. 微信兼容性修复
        html = self._apply_wechat_fixes(html)

        return {
            "html": html,
            "css": theme_css,
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
            if not str(target_path_resolved).startswith(str(target_dir_resolved)):
                raise ValueError("Invalid target path")

            # 复制文件
            shutil.copy2(local_path, target_path)
            logger.debug(f"Saved to: {target_path}")

            # 返回可访问的URL（通过FastAPI的/projects路由）
            return f"/projects/{self.project_id}/wechat_images/{filename}"

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
        import requests
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.connection import create_connection
        from pathlib import Path
        from urllib.parse import unquote
        import socket

        logger = logging.getLogger(__name__)

        try:
            # 如果是本地文件，直接返回路径
            if not url.startswith(("http://", "https://")):
                decoded_path = unquote(url)
                if Path(decoded_path).exists():
                    logger.debug(f"Using local file: {decoded_path}")
                    return decoded_path
                logger.warning(f"Local file not found: {decoded_path}")
                return None

            # 安全检查：防止 SSRF 攻击
            if not _is_safe_url(url):
                logger.error(f"Unsafe URL blocked: {_sanitize_url_for_log(url)}")
                return None

            # 创建自定义连接函数，在连接时验证 IP（防止 DNS Rebinding）
            original_create_connection = create_connection
            def safe_create_connection(address, *args, **kwargs):
                host, port = address
                # 解析域名获取 IP
                ip = socket.gethostbyname(host)
                # 验证 IP 是否安全
                if not _is_safe_ip(ip):
                    raise ValueError(f"Unsafe IP address: {ip}")
                # 使用原始函数创建连接
                return original_create_connection((ip, port), *args, **kwargs)

            # 临时替换连接函数
            requests.packages.urllib3.util.connection.create_connection = safe_create_connection

            try:
                # 下载远程图片
                logger.debug(f"Downloading image: {_sanitize_url_for_log(url)}")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                # 使用 certifi 提供的可信证书，防止环境变量绕过
                import certifi

                # 使用更短的超时时间，启用 SSL 验证，流式下载
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=(5, 15),
                    verify=certifi.where(),  # 使用固定的证书包
                    stream=True
                )
                response.raise_for_status()
            finally:
                # 恢复原始连接函数
                requests.packages.urllib3.util.connection.create_connection = original_create_connection

            # 检测文件扩展名
            content_type = response.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                ext = ".jpg"

            # 保存到临时文件（使用 delete=False，但在调用方的 finally 中手动清理）
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_path = temp_file.name

            try:
                # 流式下载并限制大小（10MB）
                MAX_IMAGE_SIZE = 10 * 1024 * 1024
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded > MAX_IMAGE_SIZE:
                            temp_file.close()
                            try:
                                import os
                                os.unlink(temp_path)
                            except:
                                pass
                            raise ValueError(f"Image too large: {downloaded} bytes (max {MAX_IMAGE_SIZE})")
                        temp_file.write(chunk)

                temp_file.close()
                logger.debug(f"Downloaded to: {temp_path}, size: {downloaded} bytes")
                return temp_path
            except Exception as e:
                # 如果写入失败，立即清理
                try:
                    import os
                    os.unlink(temp_path)
                except:
                    pass
                raise e

        except Exception as e:
            logger.warning(f"Failed to download image: {e}")
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

        # 图片居中
        for img in soup.find_all("img"):
            style = img.get("style", "")
            if "display" not in style:
                img["style"] = f"{style};max-width:100%;height:auto;display:block;margin:1.5em auto;"

        return str(soup)


# 注册清理函数，确保线程池在程序退出时正确关闭
# 使用 wait=False 避免在 FastAPI worker 被 SIGKILL 时挂起
import atexit
atexit.register(lambda: WechatFormatter._image_executor.shutdown(wait=False))
