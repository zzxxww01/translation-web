"""
Translation Agent - Gemini LLM Provider

Google Gemini API implementation for translation and analysis.
Uses env-driven model aliases (flash/pro/preview) to resolve concrete model ids.
"""

import logging
import os
import json
import time
import importlib
import warnings
from dataclasses import dataclass
from contextlib import contextmanager
from contextvars import ContextVar
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Lock
from typing import Optional, Dict, Any, List
from types import ModuleType

from src.config import settings

from .base import LLMProvider


logger = logging.getLogger(__name__)
_genai_module: ModuleType | None = None
_client_env_lock = Lock()


def _load_genai_module() -> ModuleType | None:
    """Import google.genai lazily and suppress its known Python 3.14 deprecation warning."""
    global _genai_module
    if _genai_module is not None:
        return _genai_module

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"'.*_UnionGenericAlias' is deprecated and slated for removal in Python 3\.17",
                category=DeprecationWarning,
                module=r"google\.genai\.types",
            )
            _genai_module = importlib.import_module("google.genai")
    except ModuleNotFoundError:
        return None

    return _genai_module


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


@dataclass(frozen=True)
class GeminiAttempt:
    api_key: str
    key_role: str
    model_name: str
    uses_backup_model: bool


class GeminiProvider(LLMProvider):
    """Google Gemini API Provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        backup_api_key: Optional[str] = None,
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
        self.api_keys = self._load_api_keys(
            primary_key=api_key,
            backup_key=backup_api_key,
        )
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.backup_api_key = self.api_keys[1] if len(self.api_keys) > 1 else ""

        if not self.api_keys:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY or GEMINI_BACKUP_API_KEY environment variable, or pass api_key."
            )

        # Request-scoped model selector for async concurrency safety.
        self._active_model_selector: ContextVar[Optional[str]] = ContextVar(
            "gemini_active_model_selector",
            default=None,
        )
        self._client_cache: Dict[str, Any] = {}
        self._client_cache_lock = Lock()
        self.model_catalog = self._load_model_catalog()
        self.model_type = self._normalize_model_selector(model_type) or "pro"

        # 代理配置支持
        self.proxy_config = self._get_proxy_config()
        if self.proxy_config:
            logger.info("[Gemini] 使用代理配置: %s", self.proxy_config)

        # Default model selector priority:
        # GEMINI_MODEL (legacy/global selector) > constructor model > model_type
        default_selector = (
            settings.gemini_model
            or model
            or self.model_type
        )
        self.model_name = self.resolve_model_name(default_selector)

        # 备用模型（用于 high-demand 错误时回退）
        backup_selector = settings.gemini_backup_model or os.getenv("GEMINI_BACKUP_MODEL", "flash")
        self.backup_model = self.resolve_model_name(backup_selector)

        self.request_timeout = settings.gemini_timeout
        self.max_attempts = settings.gemini_max_retries or settings.gemini_retry_count or 5
        self.retry_delay = settings.gemini_retry_delay or 0.5
        if not self._use_rest_transport():
            genai_module = _load_genai_module()
            if genai_module is None:
                raise RuntimeError("google-genai is not installed. Run: pip install google-genai")
            self._client_cache[self.api_key] = self._create_client(genai_module, self.api_key)

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
        return {
            "flash": settings.gemini_flash_model,
            "pro": settings.gemini_pro_model,
            "preview": settings.gemini_preview_model,
        }

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

    def _load_api_keys(
        self,
        primary_key: Optional[str] = None,
        backup_key: Optional[str] = None,
    ) -> List[str]:
        keys: List[str] = []
        if primary_key or backup_key:
            candidates = [primary_key, backup_key]
        else:
            candidates = [
                settings.gemini_api_key,
                settings.gemini_backup_api_key,
                os.getenv("GEMINI_API_KEY"),
                os.getenv("GEMINI_BACKUP_API_KEY"),
            ]

        for candidate in candidates:
            if not candidate:
                continue
            normalized = candidate.strip()
            if normalized and normalized not in keys:
                keys.append(normalized)
        return keys

    def _get_env_int(self, name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _get_env_float(self, name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
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

    def _create_client(self, genai_module: ModuleType, api_key: str):
        try:
            return genai_module.Client(api_key=api_key)
        except TypeError:
            with _client_env_lock:
                previous = os.environ.get("GEMINI_API_KEY")
                os.environ["GEMINI_API_KEY"] = api_key
                try:
                    return genai_module.Client()
                finally:
                    if previous is None:
                        os.environ.pop("GEMINI_API_KEY", None)
                    else:
                        os.environ["GEMINI_API_KEY"] = previous

    def _get_client(self, api_key: str):
        client = self._client_cache.get(api_key)
        if client is not None:
            return client

        with self._client_cache_lock:
            client = self._client_cache.get(api_key)
            if client is not None:
                return client

            genai_module = _load_genai_module()
            if genai_module is None:
                raise RuntimeError("google-genai is not installed. Run: pip install google-genai")

            client = self._create_client(genai_module, api_key)
            self._client_cache[api_key] = client
            return client

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

    @staticmethod
    def _is_auth_error(error_str: str) -> bool:
        text = error_str.lower()
        return (
            "401" in text
            or "403" in text
            or "api key not valid" in text
            or "invalid api key" in text
            or "permission denied" in text
            or "unauthenticated" in text
            or "forbidden" in text
        )

    @staticmethod
    def _is_retryable_error(error_str: str) -> bool:
        text = error_str.lower()
        return (
            GeminiProvider._is_auth_error(error_str)
            or GeminiProvider._is_rate_limited(error_str)
            or GeminiProvider._is_high_demand_unavailable(error_str)
            or "quota" in text
            or "500" in text
            or "502" in text
            or "503" in text
            or "504" in text
            or "deadline exceeded" in text
            or "timed out" in text
            or "timeout" in text
            or "connection aborted" in text
            or "connection reset" in text
            or "temporarily unavailable" in text
            or "internal server error" in text
            or "service unavailable" in text
            or "bad gateway" in text
        )

    @staticmethod
    def _is_non_retryable_error(error_str: str) -> bool:
        text = error_str.lower()
        return (
            "invalid argument" in text
            or "request contains an invalid argument" in text
            or "unsupported response mime type" in text
            or "candidate was blocked" in text
            or "safety" in text and "blocked" in text
            or "prompt is too long" in text
            or "too many tokens" in text
            or "context length" in text
        )

    def _build_attempt_plan(self, primary_model: str) -> List[GeminiAttempt]:
        models = [primary_model]
        if self.backup_model and self.backup_model != primary_model:
            models.append(self.backup_model)

        attempts: List[GeminiAttempt] = []
        for model_name in models:
            for index, api_key in enumerate(self.api_keys):
                key_role = "primary" if index == 0 else ("backup" if index == 1 else f"backup{index}")
                attempts.append(
                    GeminiAttempt(
                        api_key=api_key,
                        key_role=key_role,
                        model_name=model_name,
                        uses_backup_model=model_name != primary_model,
                    )
                )
        return attempts

    def _retry_delay_for_error(self, error_str: str, retry_index: int) -> float:
        if self._is_rate_limited(error_str):
            return min(self.retry_delay * (2 ** retry_index), 16.0)
        return max(self.retry_delay, 0.2)

    def _generate_once(
        self,
        prompt: str,
        attempt: GeminiAttempt,
        temperature: float,
        response_mime_type: Optional[str],
    ) -> str:
        if self._use_rest_transport():
            return self._generate_with_rest(
                prompt=prompt,
                api_key=attempt.api_key,
                timeout=self.request_timeout,
                temperature=temperature,
                response_mime_type=response_mime_type,
                model_override=attempt.model_name,
            )

        client = self._get_client(attempt.api_key)

        def _call():
            config = {"temperature": temperature}
            if response_mime_type:
                config["response_mime_type"] = response_mime_type
            resp = client.models.generate_content(
                model=attempt.model_name,
                contents=prompt,
                config=config,
            )
            return resp.text

        return self._generate_with_timeout_fn(_call, self.request_timeout)

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: Optional[int] = None,
        model: Optional[str] = None,
        **_kwargs,
    ) -> str:
        """
        ?????????

        Args:
            prompt: ?????            response_format: ????????json" ?????? JSON ???
            temperature: ??????
            max_retries: ??????????
        Returns:
            str: ????????        """
        requested_selector = model or self._active_model_selector.get()
        primary_model = self.resolve_model_name(requested_selector) if requested_selector else self.model_name
        attempt_plan = self._build_attempt_plan(primary_model)
        max_attempts = max(max_retries or self.max_attempts, len(attempt_plan))
        start_time = time.monotonic()

        logger.info(
            "[Gemini] generate start len=%s model=%s backup_model=%s keys=%s timeout=%ss transport=%s",
            len(prompt),
            primary_model,
            self.backup_model or "-",
            len(self.api_keys),
            self.request_timeout,
            "rest" if self._use_rest_transport() else "sdk",
        )

        extra_retry_index = 0
        last_exception: Exception | None = None
        response_mime_type = "application/json" if response_format == "json" else None

        for attempt_index in range(max_attempts):
            plan_index = min(attempt_index, len(attempt_plan) - 1)
            attempt = attempt_plan[plan_index]
            try:
                text = self._generate_once(
                    prompt=prompt,
                    attempt=attempt,
                    temperature=temperature,
                    response_mime_type=response_mime_type,
                )
                duration = time.monotonic() - start_time
                logger.info(
                    "[Gemini] generate success in %.2fs (model=%s key=%s attempt=%s/%s)",
                    duration,
                    attempt.model_name,
                    attempt.key_role,
                    attempt_index + 1,
                    max_attempts,
                )
                return text.strip()
            except Exception as exc:
                if isinstance(exc, FutureTimeoutError):
                    exc = TimeoutError(f"Gemini request timed out after {self.request_timeout}s")

                error_text = self._error_to_text(exc)
                last_exception = exc

                if self._is_non_retryable_error(error_text):
                    duration = time.monotonic() - start_time
                    logger.error(
                        "[Gemini] generate aborted in %.2fs on non-retryable error (model=%s key=%s). err=%s",
                        duration,
                        attempt.model_name,
                        attempt.key_role,
                        error_text,
                    )
                    raise exc

                has_fresh_attempt = plan_index < len(attempt_plan) - 1
                if has_fresh_attempt and self._is_retryable_error(error_text):
                    next_attempt = attempt_plan[plan_index + 1]
                    logger.warning(
                        "[Gemini] attempt failed on model=%s key=%s; switching to model=%s key=%s (%s/%s). err=%s",
                        attempt.model_name,
                        attempt.key_role,
                        next_attempt.model_name,
                        next_attempt.key_role,
                        attempt_index + 1,
                        max_attempts,
                        error_text,
                    )
                    continue

                if attempt_index < max_attempts - 1 and self._is_retryable_error(error_text):
                    retry_delay = self._retry_delay_for_error(error_text, extra_retry_index)
                    extra_retry_index += 1
                    logger.warning(
                        "[Gemini] request failed on final route model=%s key=%s; retry in %.1fs (%s/%s). err=%s",
                        attempt.model_name,
                        attempt.key_role,
                        retry_delay,
                        attempt_index + 1,
                        max_attempts,
                        error_text,
                    )
                    time.sleep(retry_delay)
                    continue

                duration = time.monotonic() - start_time
                logger.error(
                    "[Gemini] generate failed in %.2fs after %s attempts (model=%s key=%s). err=%s",
                    duration,
                    attempt_index + 1,
                    attempt.model_name,
                    attempt.key_role,
                    error_text,
                )
                raise exc

        if last_exception is not None:
            raise last_exception

        raise RuntimeError("Gemini generate failed without an exception.")

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
        article_theme = context.get("article_theme")
        article_structure = context.get("article_structure")
        current_section_title = context.get("current_section_title")
        heading_chain = context.get("heading_chain")
        target_audience = context.get("target_audience")
        translation_voice = context.get("translation_voice")
        article_challenges = context.get("article_challenges")
        style_guide = context.get("style_guide")
        section_context = context.get("section_context")
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
            article_theme=article_theme,
            article_structure=article_structure,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            target_audience=target_audience,
            translation_voice=translation_voice,
            article_challenges=article_challenges,
            style_guide=style_guide,
            section_context=section_context,
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
        enhanced_guidelines = list(context.get("guidelines", []))
        section_role = context.get("section_role")
        if section_role:
            enhanced_guidelines.insert(0, f"本章角色：{section_role}")
        translation_voice = context.get("translation_voice")
        if translation_voice:
            enhanced_guidelines.insert(1, f"目标语气：{translation_voice}")
        target_audience = context.get("target_audience")
        if target_audience:
            enhanced_guidelines.insert(2, f"目标读者：{target_audience}")
        translation_notes = context.get("translation_notes") or []
        for note in reversed(translation_notes[:4]):
            enhanced_guidelines.insert(3, f"本章注意：{note}")

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
                target_audience=context.get("target_audience", ""),
                translation_voice=context.get("translation_voice", ""),
                article_challenges=self._format_challenges_for_prompt(
                    context.get("article_challenges", [])
                ),
                glossary=self._format_glossary_for_prompt(context.get("glossary", [])),
                guidelines="\n".join(enhanced_guidelines),
            )
        except KeyError:
            # 如果 batch_translation prompt 不存在，使用简化版本
            glossary_text = self._format_glossary_for_prompt(
                context.get("glossary", [])
            )
            guidelines_text = "\n".join(
                [f"- {g}" for g in enhanced_guidelines]
            )

            return f"""你是一位顶级的中英文技术翻译专家。请将以下章节的所有段落翻译成中文。

## 章节信息
- 标题：{section_title}
- 在全文中的位置：{context.get("section_position", "未知")}
- 前一章节：{context.get("previous_section_title", "无")}
- 后一章节：{context.get("next_section_title", "无")}

## 文章主题
{context.get("article_theme", "技术类文章")}

## 目标读者
{context.get("target_audience", "关注科技产业的中文读者")}

## 术语参考
{glossary_text}

## 高风险提示
{self._format_challenges_for_prompt(context.get("article_challenges", []))}

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
                    strategy = item.get("strategy", "")
                    note = item.get("note") or item.get("context_meaning", "")
                    first_occurrence_note = item.get("first_occurrence_note", False)
                    if original and (translation or strategy == "preserve"):
                        extras = []
                        if strategy == "preserve":
                            extras.append("保留英文")
                        elif strategy == "first_annotate" or first_occurrence_note:
                            extras.append("首次建议中文加英文括注")
                        if note:
                            extras.append(str(note))
                        suffix = f"（{'；'.join(extras)}）" if extras else ""
                        rendered_translation = translation or "保留英文"
                        lines.append(f"- {original} → {rendered_translation}{suffix}")

        return "\n".join(lines) if lines else "无"

    def _format_challenges_for_prompt(self, challenges: Any) -> str:
        """格式化翻译难点为 prompt 文本。"""
        if not challenges:
            return "无"

        lines = []
        if isinstance(challenges, list):
            for item in challenges[:6]:
                if isinstance(item, dict):
                    location = item.get("location", "")
                    issue = item.get("issue", "")
                    suggestion = item.get("suggestion", "")
                    line = str(issue).strip()
                    if location:
                        line = f"[{location}] {line}"
                    if suggestion:
                        line = f"{line}；建议：{suggestion}"
                    if line:
                        lines.append(f"- {line}")
                else:
                    text = str(item).strip()
                    if text:
                        lines.append(f"- {text}")

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
        backup_api_key=backup_api_key,
        model=model,
        model_type=model_type,
    )
