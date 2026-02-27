"""
Translation Agent - Gemini LLM Provider

Google Gemini API implementation for translation and analysis.
Uses Gemini 3 model ids by default (gemini-3-pro-preview / gemini-3-flash-preview).
"""

import os
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Dict, Any, List

try:
    from google import genai
except Exception:
    genai = None

from .base import LLMProvider


# Model configurations
MODEL_CONFIG = {
    "reasoning": {
        "name": "gemini-3-pro-preview",
        "description": "推理模型，质量更高但更慢",
        "max_output_tokens": 65536,
        "supports_thinking": True,
    },
    "flash": {
        "name": "gemini-3-flash-preview",
        "description": "快速模型，速度快成本低",
        "max_output_tokens": 65536,
        "supports_thinking": False,
    },
}


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        backup_api_key: Optional[str] = None,
        model: str = "gemini-3-pro-preview",
        model_type: str = "reasoning",
    ):
        """
        初始化 Gemini Provider

        Args:
            api_key: Gemini API Key，如果不提供则从环境变量 GEMINI_API_KEY 获取
            backup_api_key: 备用 API Key，如果不提供则从环境变量 GEMINI_BACKUP_API_KEY 获取
            model: 模型名称
            model_type: 模型类型 ("reasoning" 或 "flash")
        """
        super().__init__()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.backup_api_key = backup_api_key or os.getenv("GEMINI_BACKUP_API_KEY")
        self.model_type = model_type

        # 状态标志：是否已经切换到备用 Key
        self._using_backup = False

        if not self.api_key and not self.backup_api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )

        # 初始配置：如果由于某种原因已经在备用模式（比如 factory 全局设置），则直接用 backups
        # 但通常每个实例独立。如果有 api_key，先用 api_key
        # 如果没有 api_key 但有 backup，直接用 backup
        current_key = self.api_key if self.api_key else self.backup_api_key
        # 如果只有 backup，标记为已使用 backup
        if not self.api_key and self.backup_api_key:
            self._using_backup = True

        # 代理配置支持
        self.proxy_config = self._get_proxy_config()
        if self.proxy_config:
            print(f"[Gemini] 使用代理配置: {self.proxy_config}")

        # 根据 model_type 选择模型
        if model_type in MODEL_CONFIG:
            self.model_name = MODEL_CONFIG[model_type]["name"]
        else:
            self.model_name = model

        self.request_timeout = self._get_env_int("GEMINI_TIMEOUT", 30)
        self._client = None
        if not self._use_rest_transport():
            if genai is None:
                raise RuntimeError("google-genai is not installed. Run: pip install google-genai")
            self._client = self._create_client(current_key)

    def switch_model(self, model_type: str) -> None:
        """
        切换模型类型

        Args:
            model_type: 模型类型 ("reasoning" 或 "flash")
        """
        if model_type not in MODEL_CONFIG:
            raise ValueError(
                f"Unknown model type: {model_type}. Available: {list(MODEL_CONFIG.keys())}"
            )

        self.model_type = model_type
        self.model_name = MODEL_CONFIG[model_type]["name"]
        # Client is stateless for model choice; no need to recreate.

    def _get_env_int(self, name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        if http_proxy or https_proxy:
            return {
                "http": http_proxy,
                "https": https_proxy or http_proxy,
            }
        return None

    def _use_rest_transport(self) -> bool:
        override = os.getenv("GEMINI_USE_REST")
        if override is not None:
            return override.strip().lower() in {"1", "true", "yes", "y"}
        return self.proxy_config is not None

    def _create_client(self, api_key: str):
        try:
            return genai.Client(api_key=api_key)
        except TypeError:
            os.environ["GEMINI_API_KEY"] = api_key
            return genai.Client()

    def _generate_with_timeout_fn(self, fn, timeout: int | None):
        if not timeout or timeout <= 0:
            return fn()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _generate_with_rest(
        self,
        prompt: str,
        api_key: str,
        timeout: int | None,
        temperature: float = 0.7,
        response_mime_type: Optional[str] = None,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        generation_config = {"temperature": temperature}
        if response_mime_type:
            generation_config["responseMimeType"] = response_mime_type
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        headers = {"x-goog-api-key": api_key}
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout if timeout and timeout > 0 else None,
            proxies=self.proxy_config,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini REST response: {data}") from exc

    def _check_connectivity(self, timeout=10):
        """检查网络连通性"""
        try:
            response = requests.get(
                "https://generativelanguage.googleapis.com/",
                timeout=timeout,
                proxies=self.proxy_config if self.proxy_config else None
            )
            return True
        except:
            return False

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: int = 30,
    ) -> str:
        """
        通用文本生成

        Args:
            prompt: 提示词
            response_format: 响应格式，"json" 表示期望 JSON 输出
            temperature: 温度参数
            max_retries: 最大重试次数
            retry_delay: 重试等待时间（秒），备用模式下不等待

        Returns:
            str: 生成的文本
        """
        for attempt in range(max_retries + 1):
            try:
                response_mime_type = "application/json" if response_format == "json" else None
                if self._use_rest_transport():
                    text = self._generate_with_rest(
                        prompt=prompt,
                        api_key=self.backup_api_key if self._using_backup else self.api_key,
                        timeout=self.request_timeout,
                        temperature=temperature,
                        response_mime_type=response_mime_type,
                    )
                else:
                    if self._client is None:
                        raise RuntimeError("google-genai is not available.")

                    def _call():
                        config = {"temperature": temperature}
                        if response_mime_type:
                            config["response_mime_type"] = response_mime_type
                        response = self._client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=config,
                        )
                        return response.text

                    text = self._generate_with_timeout_fn(_call, self.request_timeout)
                return text.strip()
            except Exception as e:
                error_str = str(e)

                # ==== Network Connectivity Check ====
                # 网络连通性检查 - 优先检查连接问题
                if "connect" in error_str.lower() or "timeout" in error_str.lower():
                    if not self._check_connectivity():
                        if not self._using_backup and self.backup_api_key:
                            print(f"[Gemini] 网络问题，切换到备用Key...")
                            self._using_backup = True
                            if not self._use_rest_transport():
                                self._client = self._create_client(self.backup_api_key)
                            continue
                        else:
                            raise ConnectionError(f"无法连接到Gemini API。请检查网络连接或配置代理。原始错误: {error_str}")

                # ==== Fallback Logic ====
                # 如果当前没有在使用 backup，且配置了 backup key，且发生了错误
                if not self._using_backup and self.backup_api_key:
                    print(f"[Gemini] 主 Key 失败: {e}. 切换到备用 Key (付费版)")
                    # 切换状态
                    self._using_backup = True
                    if not self._use_rest_transport():
                        self._client = self._create_client(self.backup_api_key)
                    # 立即重试，不等待
                    print("[Gemini] 使用备用 Key 立即重试...")
                    continue
                # ========================

                # 如果是最后一次尝试，直接抛出
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Generation failed after {max_retries} retries (Backup active: {self._using_backup}): {e}"
                    )

                # ==== 关键改进：备用模式下快速重试 ====
                if self._using_backup:
                    # 备用 key 是付费版，不应有配额限制
                    # 快速重试，不等待
                    print(
                        f"[Gemini] 备用 Key 请求失败，快速重试 ({attempt + 1}/{max_retries})..."
                    )
                    time.sleep(0.5)  # 仅短暂等待 0.5 秒
                    continue

                # ==== 主 Key 下的配额限制处理 ====
                if "429" in error_str or "quota" in error_str.lower():
                    # 动态等待时间：基础时间 * (重试次数 + 1)
                    wait_time = (attempt + 1) * retry_delay
                    print(f"主 Key 配额限制，等待 {wait_time} 秒后切换到备用 Key...")
                    time.sleep(wait_time)
                    # 强制切换到备用 key
                    if self.backup_api_key:
                        print(f"[Gemini] 主动切换到备用 Key")
                        self._using_backup = True
                        if not self._use_rest_transport():
                            self._client = self._create_client(self.backup_api_key)
                    continue

                # 其他错误，短暂等待后重试
                time.sleep(2)
                continue

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        翻译文本

        Args:
            text: 要翻译的原文
            context: 上下文信息

        Returns:
            str: 翻译结果
        """
        prompt = self._build_translation_prompt(text, context or {})
        return self.generate(prompt, temperature=0.5)

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本，提取术语和风格

        Args:
            text: 要分析的文本（通常是全文或摘要）

        Returns:
            Dict: 分析结果
        """
        prompt = self._build_analysis_prompt(text)

        try:
            response = self.generate(prompt, response_format="json")
            return self._parse_json_response(response)
        except json.JSONDecodeError:
            return {
                "terms": [],
                "style": {"tone": "professional", "formality": "formal", "notes": []},
            }
        except Exception as e:
            raise RuntimeError(f"Analysis failed: {e}")

    def check_consistency(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        检查译文一致性

        Args:
            paragraphs: 段落列表 [{"source": ..., "translation": ...}, ...]
            glossary: 术语表 {term: translation, ...}

        Returns:
            List[Dict]: 问题列表
        """
        prompt = self._build_consistency_prompt(paragraphs, glossary)

        try:
            response = self.generate(prompt, response_format="json")
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """构建翻译 prompt（增强版：使用新的Prompt构建器）"""
        # 使用新的Prompt构建器
        from ..prompts.prompt_builder import get_prompt_builder

        # 获取原始版Prompt构建器
        builder = get_prompt_builder(style="original")

        # 提取上下文信息
        glossary = context.get("glossary", [])
        previous_paragraphs = context.get("previous_paragraphs", [])
        next_preview = context.get("next_preview", [])
        article_title = context.get("article_title")
        current_section_title = context.get("current_section_title")
        heading_chain = context.get("heading_chain")

        # 使用Prompt构建器生成完整Prompt
        prompt = builder.build_prompt(
            source_text=text,
            glossary=glossary,
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
            article_title=article_title,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
        )

        return prompt

    def _build_analysis_prompt(self, text: str) -> str:
        """构建分析 prompt"""
        return self.prompt_manager.get("analysis", text=text[:8000])

    def _build_consistency_prompt(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> str:
        """构建一致性检查 prompt"""
        para_text = "\n\n".join(
            [
                f"[段落 {i+1}]\n原文：{p['source']}\n译文：{p['translation']}"
                for i, p in enumerate(paragraphs[:20])
            ]
        )

        glossary_text = "\n".join(
            [f"- {term} → {trans}" for term, trans in glossary.items()]
        )

        return self.prompt_manager.get(
            "consistency", para_text=para_text, glossary_text=glossary_text
        )

    def translate_section(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> List[Dict[str, str]]:
        """
        章节级批量翻译（粗粒度翻译模式）

        一次性翻译整个章节的所有段落，然后自动切分回原始段落。

        Args:
            section_text: 章节完整文本（所有段落用换行分隔）
            section_title: 章节标题
            context: 翻译上下文信息
            paragraph_ids: 段落ID列表，用于标识每个段落

        Returns:
            List[Dict[str, str]]: 翻译结果列表 [{"id": "p001", "translation": "..."}, ...]
        """
        # 构建批量翻译 prompt
        prompt = self._build_batch_translation_prompt(
            section_text, section_title, context, paragraph_ids
        )

        try:
            response = self.generate(prompt, response_format="json", temperature=0.5)
            result = self._parse_json_response(response)

            # 验证结果格式
            if isinstance(result, dict) and "translations" in result:
                return result["translations"]
            elif isinstance(result, list):
                return result
            else:
                # 如果返回格式不正确，尝试解析为单个翻译
                return [{"id": pid, "translation": ""} for pid in paragraph_ids]

        except Exception as e:
            print(f"[Gemini] Batch translation failed: {e}")
            # 返回空翻译列表
            return [{"id": pid, "translation": ""} for pid in paragraph_ids]

    def translate_title(
        self, title: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        翻译标题

        Args:
            title: 原文标题
            context: 上下文信息

        Returns:
            str: 翻译后的标题
        """
        prompt = f"""请将以下标题翻译成中文。要求：
1. 保持标题的简洁性
2. 准确传达原文含义
3. 符合中文标题的表达习惯

原文标题：{title}

请直接输出翻译后的标题，不要添加任何解释："""

        return self.generate(prompt, temperature=0.3)

    def translate_metadata(
        self, authors: List[str], date: Optional[str], subtitle: Optional[str]
    ) -> Dict[str, Any]:
        """
        翻译元信息（保留人名原文）

        Args:
            authors: 作者列表
            date: 发布日期
            subtitle: 副标题

        Returns:
            Dict: 翻译后的元信息
        """
        result = {
            "authors": authors,  # 人名保持原文
            "date": date,  # 日期保持原样
            "subtitle": None,
        }

        # 只翻译副标题
        if subtitle:
            prompt = f"""请将以下副标题翻译成中文：

原文：{subtitle}

请直接输出翻译，不要添加任何解释："""
            result["subtitle"] = self.generate(prompt, temperature=0.3)

        return result

    def _build_batch_translation_prompt(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> str:
        """构建批量翻译 prompt"""
        # 尝试使用专用的 batch_translation prompt，如果不存在则使用通用模板
        try:
            return self.prompt_manager.get(
                "batch_translation",
                section_title=section_title,
                section_text=section_text,
                paragraph_ids=json.dumps(paragraph_ids),
                article_theme=context.get("article_theme", ""),
                section_position=context.get("section_position", ""),
                previous_section=context.get("previous_section_title", ""),
                next_section=context.get("next_section_title", ""),
                glossary=self._format_glossary_for_prompt(context.get("glossary", [])),
                guidelines="\n".join(context.get("guidelines", [])),
            )
        except KeyError:
            # 如果 batch_translation prompt 不存在，使用简化版本
            glossary_text = self._format_glossary_for_prompt(
                context.get("glossary", [])
            )
            guidelines_text = "\n".join(
                [f"- {g}" for g in context.get("guidelines", [])]
            )

            return f"""你是一位顶级的中英文技术翻译专家。请将以下章节的所有段落翻译成中文。

## 章节信息
- 标题：{section_title}
- 在全文中的位置：{context.get("section_position", "未知")}
- 前一章节：{context.get("previous_section_title", "无")}
- 后一章节：{context.get("next_section_title", "无")}

## 文章主题
{context.get("article_theme", "技术类文章")}

## 术语参考
{glossary_text}

## 翻译指南
{guidelines_text}

## 待翻译内容
以下是章节中的所有段落，每个段落都有唯一ID：

{section_text}

## 输出要求
请以 JSON 格式返回翻译结果：
{{
    "translations": [
        {{"id": "段落ID", "translation": "翻译内容"}},
        ...
    ]
}}

段落ID列表：{json.dumps(paragraph_ids)}

请确保：
1. 每个段落都有对应的翻译
2. 保持段落之间的逻辑连贯性
3. 术语使用保持一致
4. 译文自然流畅，不要有机翻痕迹

请输出 JSON："""

    def _format_glossary_for_prompt(self, glossary: Any) -> str:
        """格式化术语表为 prompt 格式"""
        if not glossary:
            return "无"

        lines = []
        if isinstance(glossary, dict):
            for term, trans in glossary.items():
                lines.append(f"- {term} → {trans}")
        elif isinstance(glossary, list):
            for item in glossary[:20]:  # 限制数量
                if isinstance(item, dict):
                    original = item.get("original", item.get("term", ""))
                    translation = item.get("translation", "")
                    if original and translation:
                        lines.append(f"- {original} → {translation}")

        return "\n".join(lines) if lines else "无"

    def prescan_section_with_flash(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        使用 Flash 模型进行章节预扫描（方案 C 新增）

        自动切换到 Flash 模型执行预扫描，然后切回原模型

        Args:
            section_id: 章节 ID
            section_title: 章节标题
            section_content: 章节内容
            existing_terms: 已有术语表

        Returns:
            Dict: 预扫描结果
        """
        # 保存当前模型
        original_model_type = self.model_type
        original_model_name = self.model_name

        try:
            # 切换到 Flash 模型
            self.switch_model("flash")

            # 执行预扫描
            result = self.prescan_section(
                section_id=section_id,
                section_title=section_title,
                section_content=section_content,
                existing_terms=existing_terms
            )

            return result
        finally:
            # 恢复原模型
            self.model_type = original_model_type
            self.model_name = original_model_name


def create_gemini_provider(
    api_key: Optional[str] = None,
    backup_api_key: Optional[str] = None,
    model: str = "gemini-3-pro-preview",
    model_type: str = "reasoning",
) -> GeminiProvider:
    """
    便捷函数：创建 Gemini Provider

    Args:
        api_key: API Key
        backup_api_key: 备用 API Key
        model: 模型名称
        model_type: 模型类型 ("reasoning" 或 "flash")

    Returns:
        GeminiProvider: Gemini Provider 实例
    """
    return GeminiProvider(
        api_key=api_key,
        backup_api_key=backup_api_key,
        model=model,
        model_type=model_type,
    )
