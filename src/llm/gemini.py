"""
Translation Agent - Gemini LLM Provider

Google Gemini API implementation for translation and analysis.
Uses env-driven model aliases (flash/pro/preview) to resolve concrete model ids.
"""

import logging
import os
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional, Dict, Any, List

try:
    from google import genai
except Exception:
    genai = None

from .base import LLMProvider


logger = logging.getLogger(__name__)


# Model catalog. Concrete model ids come from env vars.
MODEL_CONFIG = {
    "flash": {
        "env_var": "GEMINI_FLASH_MODEL",
        "default": "gemini-flash-latest",
        "description": "快速模型，速度快成本低",
        "max_output_tokens": 65536,
        "supports_thinking": False,
    },
    "pro": {
        "env_var": "GEMINI_PRO_MODEL",
        "default": "gemini-3-pro-preview",
        "description": "标准专业模型，质量与成本平衡",
        "max_output_tokens": 65536,
        "supports_thinking": True,
    },
    "preview": {
        "env_var": "GEMINI_PREVIEW_MODEL",
        "default": "gemini-3.1-pro-preview",
        "description": "前沿预览模型，能力更强但可能更不稳定",
        "max_output_tokens": 65536,
        "supports_thinking": True,
    },
}

MODEL_ALIASES = {
    "default": "pro",
    "gemini": "pro",
    "reasoning": "pro",
    "flash": "flash",
    "pro": "pro",
    "preview": "preview",
}


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "pro",
        model_type: str = "pro",
    ):
        """
        初始化 Gemini Provider

        Args:
            api_key: Gemini API Key，如果不提供则从环境变量 GEMINI_API_KEY 获取
                     (GEMINI_BACKUP_API_KEY 作为兼容回退)
            model: 模型名称或别名（flash/pro/preview）
            model_type: 模型类型别名（flash/pro/preview，兼容 reasoning）
        """
        super().__init__()
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GEMINI_BACKUP_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )

        # Request-scoped model selector for async concurrency safety.
        self._active_model_selector: ContextVar[Optional[str]] = ContextVar(
            "gemini_active_model_selector",
            default=None,
        )
        self.model_catalog = self._load_model_catalog()
        self.model_type = self._normalize_model_selector(model_type) or "pro"

        # 代理配置支持
        self.proxy_config = self._get_proxy_config()
        if self.proxy_config:
            logger.info("[Gemini] 使用代理配置: %s", self.proxy_config)

        # Default model selector priority:
        # GEMINI_MODEL (legacy/global selector) > constructor model > model_type
        default_selector = (
            os.getenv("GEMINI_MODEL")
            or model
            or self.model_type
        )
        self.model_name = self.resolve_model_name(default_selector)

        # 备用模型（用于 high-demand 错误时回退）
        backup_selector = os.getenv("GEMINI_BACKUP_MODEL", "flash")
        self.backup_model = self.resolve_model_name(backup_selector)

        self.request_timeout = self._get_env_int("GEMINI_TIMEOUT", 120)
        self._client = None
        if not self._use_rest_transport():
            if genai is None:
                raise RuntimeError("google-genai is not installed. Run: pip install google-genai")
            self._client = self._create_client(self.api_key)

    def switch_model(self, model_type: str) -> None:
        """
        切换模型类型

        Args:
            model_type: 模型类型（flash/pro/preview，兼容 reasoning）
        """
        normalized = self._normalize_model_selector(model_type)
        if normalized not in MODEL_CONFIG:
            raise ValueError(
                f"Unknown model type: {model_type}. Available: {list(MODEL_CONFIG.keys())}"
            )

        self.model_type = normalized
        self.model_name = self.model_catalog[normalized]
        # Client is stateless for model choice; no need to recreate.

    def _load_model_catalog(self) -> Dict[str, str]:
        catalog: Dict[str, str] = {}
        for model_key, cfg in MODEL_CONFIG.items():
            env_var = cfg["env_var"]
            default = cfg["default"]
            catalog[model_key] = os.getenv(env_var, default)
        return catalog

    def _normalize_model_selector(self, selector: Optional[str]) -> Optional[str]:
        if selector is None:
            return None
        key = selector.strip().lower()
        if not key:
            return None
        return MODEL_ALIASES.get(key, key if key in MODEL_CONFIG else None)

    def resolve_model_name(self, selector: Optional[str]) -> str:
        normalized = self._normalize_model_selector(selector)
        if normalized and normalized in self.model_catalog:
            return self.model_catalog[normalized]
        if selector and selector.strip():
            # Allow passing a concrete model id directly for compatibility.
            return selector.strip()
        return self.model_catalog["pro"]

    @contextmanager
    def use_model(self, model_selector: Optional[str]):
        """Temporarily route all generation calls to a selected model alias/id."""
        if not model_selector:
            yield
            return
        token = self._active_model_selector.set(model_selector)
        try:
            yield
        finally:
            self._active_model_selector.reset(token)

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
        model_override: Optional[str] = None,
    ) -> str:
        model = model_override or self.model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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

    # ============ 错误分类方法 ============

    @staticmethod
    def _is_rate_limited(error_str: str) -> bool:
        return (
            "429" in error_str
            or "Too Many Requests" in error_str
            or "RESOURCE_EXHAUSTED" in error_str
            or "rate limit" in error_str.lower()
        )

    @staticmethod
    def _is_high_demand_unavailable(error_str: str) -> bool:
        text = error_str.lower()
        return (
            "currently experiencing high demand" in text
            or ('"status": "unavailable"' in text and "high demand" in text)
            or "status\":\"unavailable" in text
        )

    @staticmethod
    def _error_to_text(exc: Exception) -> str:
        text = str(exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            try:
                data = exc.response.json()
                err = data.get("error", {}) if isinstance(data, dict) else {}
                message = err.get("message")
                status = err.get("status")
                if message:
                    text = f"{text} | {message}"
                if status:
                    text = f"{text} | status={status}"
            except Exception:
                body = (exc.response.text or "").strip()
                if body:
                    text = f"{text} | body={body[:300]}"
        return text

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 5,
        model: Optional[str] = None,
        **_kwargs,
    ) -> str:
        """
        通用文本生成

        Args:
            prompt: 提示词
            response_format: 响应格式，"json" 表示期望 JSON 输出
            temperature: 温度参数
            max_retries: 最大重试次数

        Returns:
            str: 生成的文本
        """
        requested_selector = model or self._active_model_selector.get()
        current_model = self.resolve_model_name(requested_selector) if requested_selector else self.model_name
        switched_to_backup_model = False
        start_time = time.monotonic()

        logger.info(
            "[Gemini] generate start len=%s model=%s backup_model=%s timeout=%ss transport=%s",
            len(prompt),
            current_model,
            self.backup_model or "-",
            self.request_timeout,
            "rest" if self._use_rest_transport() else "sdk",
        )

        for attempt in range(max_retries):
            try:
                response_mime_type = "application/json" if response_format == "json" else None
                if self._use_rest_transport():
                    text = self._generate_with_rest(
                        prompt=prompt,
                        api_key=self.api_key,
                        timeout=self.request_timeout,
                        temperature=temperature,
                        response_mime_type=response_mime_type,
                        model_override=current_model,
                    )
                else:
                    if self._client is None:
                        raise RuntimeError("google-genai is not available.")

                    def _call():
                        config = {"temperature": temperature}
                        if response_mime_type:
                            config["response_mime_type"] = response_mime_type
                        resp = self._client.models.generate_content(
                            model=current_model,
                            contents=prompt,
                            config=config,
                        )
                        return resp.text

                    text = self._generate_with_timeout_fn(_call, self.request_timeout)

                duration = time.monotonic() - start_time
                logger.info(
                    "[Gemini] generate success in %.2fs (model=%s attempt=%s/%s)",
                    duration,
                    current_model,
                    attempt + 1,
                    max_retries,
                )
                return text.strip()
            except FutureTimeoutError:
                raise TimeoutError(f"Gemini request timed out after {self.request_timeout}s")
            except Exception as exc:
                error_text = self._error_to_text(exc)

                # 备用模型回退：high-demand 错误时切换模型
                if (
                    self.backup_model
                    and not switched_to_backup_model
                    and current_model != self.backup_model
                    and self._is_high_demand_unavailable(error_text)
                    and attempt < max_retries - 1
                ):
                    switched_to_backup_model = True
                    current_model = self.backup_model
                    logger.warning(
                        "[Gemini] model '%s' is overloaded; switch to backup model '%s' (%s/%s).",
                        self.model_name,
                        self.backup_model,
                        attempt + 1,
                        max_retries,
                    )
                    continue

                if attempt < max_retries - 1:
                    if self._is_rate_limited(error_text):
                        retry_delay = min(2 ** attempt, 16)
                        logger.warning(
                            "[Gemini] rate limited on '%s'; retry in %.1fs (%s/%s). err=%s",
                            current_model,
                            retry_delay,
                            attempt + 1,
                            max_retries,
                            error_text,
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.warning(
                            "[Gemini] request failed on '%s'; quick retry (%s/%s). err=%s",
                            current_model,
                            attempt + 1,
                            max_retries,
                            error_text,
                        )
                        time.sleep(0.3)
                    continue

                duration = time.monotonic() - start_time
                logger.error(
                    "[Gemini] generate failed in %.2fs after %s attempts (model=%s). err=%s",
                    duration,
                    max_retries,
                    current_model,
                    error_text,
                )
                raise

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        翻译文本

        Args:
            text: 要翻译的原文
            context: 上下文信息

        Returns:
            str: 翻译结果
        """
        context_data = dict(context or {})
        model_selector = context_data.pop("model", None)
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5, model=model_selector)

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
        learned_rules = context.get("learned_rules")
        instruction = context.get("instruction")
        previous_translation = context.get("previous_translation")

        # 使用Prompt构建器生成完整Prompt
        prompt = builder.build_prompt(
            source_text=text,
            glossary=glossary,
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
            article_title=article_title,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            learned_rules=learned_rules,
            instruction=instruction,
            previous_translation=previous_translation,
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
            logger.error("[Gemini] Batch translation failed: %s", e)
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
    model: str = "pro",
    model_type: str = "pro",
) -> GeminiProvider:
    """
    便捷函数：创建 Gemini Provider

    Args:
        api_key: API Key
        model: 模型名称
        model_type: 模型类型（flash/pro/preview，兼容 reasoning）

    Returns:
        GeminiProvider: Gemini Provider 实例
    """
    return GeminiProvider(
        api_key=api_key,
        model=model,
        model_type=model_type,
    )
