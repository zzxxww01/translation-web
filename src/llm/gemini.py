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
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Lock
from typing import Optional, Dict, Any, List
from types import ModuleType

from src.config import settings
from src.core.longform_context import (
    build_article_challenge_payload,
    build_section_guideline_lines,
    limit_format_tokens,
)
from src.core.glossary_prompt import render_glossary_prompt_block

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
        "description": "Fast model with lower cost",
        "max_output_tokens": 65536,
        "supports_thinking": False,
    },
    "pro": {
        "env_var": "GEMINI_PRO_MODEL",
        "default": "gemini-3-pro-preview",
        "description": "Balanced quality and cost",
        "max_output_tokens": 65536,
        "supports_thinking": True,
    },
    "preview": {
        "env_var": "GEMINI_PREVIEW_MODEL",
        "default": "gemini-3.1-pro-preview",
        "description": "Preview model with stronger capability but less stability",
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
        鍒濆鍖?Gemini Provider

        Args:
            api_key: Gemini API Key锛屽鏋滀笉鎻愪緵鍒欎粠鐜鍙橀噺 GEMINI_API_KEY 鑾峰彇
                     (GEMINI_BACKUP_API_KEY 浣滀负鍏煎鍥為€€)
            model: 妯″瀷鍚嶇О鎴栧埆鍚嶏紙flash/pro/preview锛?
            model_type: 妯″瀷绫诲瀷鍒悕锛坒lash/pro/preview锛屽吋瀹?reasoning锛?
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

        self._client_cache: Dict[str, Any] = {}
        self._client_cache_lock = Lock()
        self.model_catalog = self._load_model_catalog()
        self.model_type = self._normalize_model_selector(model_type) or "pro"

        # Proxy configuration support.
        self.proxy_config = self._get_proxy_config()
        if self.proxy_config:
            logger.info("[Gemini] Using proxy config: %s", self.proxy_config)

        # Default model selector priority:
        # GEMINI_MODEL (legacy/global selector) > constructor model > model_type
        default_selector = settings.gemini_model or model or self.model_type
        self.model_name = self.resolve_model_name(default_selector)

        # Backup model used when the primary model is temporarily unavailable.
        backup_selector = settings.gemini_backup_model or os.getenv(
            "GEMINI_BACKUP_MODEL", "flash"
        )
        self.backup_model = self.resolve_model_name(backup_selector)

        self.request_timeout = settings.gemini_timeout
        self.max_attempts = (
            settings.gemini_max_retries or settings.gemini_retry_count or 5
        )
        self.retry_delay = settings.gemini_retry_delay or 0.5
        if not self._use_rest_transport():
            genai_module = _load_genai_module()
            if genai_module is None:
                raise RuntimeError(
                    "google-genai is not installed. Run: pip install google-genai"
                )
            self._client_cache[self.api_key] = self._create_client(
                genai_module, self.api_key
            )

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
                raise RuntimeError(
                    "google-genai is not installed. Run: pip install google-genai"
                )

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

    # ============ 閿欒鍒嗙被鏂规硶 ============

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
            or 'status":"unavailable' in text
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
            or "connecterror" in text
            or "connection error" in text
            or "connection aborted" in text
            or "connection reset" in text
            or "max retries exceeded with url" in text
            or "sslerror" in text
            or "ssleoferror" in text
            or "unexpected eof while reading" in text
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
            or "safety" in text
            and "blocked" in text
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
                key_role = (
                    "primary"
                    if index == 0
                    else ("backup" if index == 1 else f"backup{index}")
                )
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
            return min(self.retry_delay * (2**retry_index), 16.0)
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
        鐢熸垚鏂囨湰

        Args:
            prompt: 鎻愮ず璇?
            response_format: 鍝嶅簲鏍煎紡锛?json" 琛ㄧず鏈熸湜 JSON 杈撳嚭
            temperature: 娓╁害鍙傛暟
            max_retries: 鏈€澶ч噸璇曟鏁?
            model: 鍙€夋ā鍨嬭鐩栵紙浠呬緵鍐呴儴鏂规硶鎸囧畾锛屽 prescan 浣跨敤 flash锛?
        Returns:
            str: 鐢熸垚鐨勬枃鏈?
        """
        primary_model = self.resolve_model_name(model) if model else self.model_name
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
                    exc = TimeoutError(
                        f"Gemini request timed out after {self.request_timeout}s"
                    )

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

                if attempt_index < max_attempts - 1 and self._is_retryable_error(
                    error_text
                ):
                    retry_delay = self._retry_delay_for_error(
                        error_text, extra_retry_index
                    )
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
        缈昏瘧鏂囨湰

        Args:
            text: 瑕佺炕璇戠殑鍘熸枃
            context: 涓婁笅鏂囦俊鎭?

        Returns:
            str: 缈昏瘧缁撴灉
        """
        context_data = dict(context or {})
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5)

    def retranslate(
        self,
        source_text: str,
        current_translation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Retranslate one paragraph with the dedicated longform retranslation prompt."""
        context_data = dict(context or {})
        prompt = self._build_retranslation_prompt(
            source_text,
            current_translation,
            context_data,
        )
        return self.generate(prompt, temperature=0.4)

    def repair_format_tokens(
        self,
        source_text: str,
        translated_text: str,
        format_tokens: List[Dict[str, Any]],
        issues: Optional[List[str]] = None,
        model: str = "flash",
    ) -> Optional[str]:
        """Run a lightweight repair pass to restore hidden token wrappers."""
        preview_tokens = limit_format_tokens(format_tokens)
        if not preview_tokens:
            return None

        token_lines: List[str] = []
        for token in preview_tokens:
            if not isinstance(token, dict):
                continue
            token_id = str(token.get("id", "")).strip()
            token_type = str(token.get("type", "")).strip()
            token_text = str(token.get("text", "")).strip()
            if token_id:
                token_lines.append(f"- {token_id} ({token_type}): {token_text}")

        issue_lines = [f"- {item}" for item in (issues or []) if str(item).strip()]
        issue_block = "\n".join(issue_lines) if issue_lines else "- (not provided)"
        token_block = "\n".join(token_lines) if token_lines else "- (empty)"

        prompt = "\n".join(
            [
                "You are a token repair engine for long-form translation.",
                "Task: repair hidden backend tokens only.",
                "",
                "Rules:",
                "1. Keep meaning and wording unchanged as much as possible.",
                "2. Restore missing or malformed `[[[TYPE_N|...]]]` wrappers.",
                "3. Keep token ids exactly from the token list.",
                "4. Do not add extra commentary.",
                "5. Output ONLY the repaired translation text.",
                "",
                "Expected tokens:",
                token_block,
                "",
                "Validation issues:",
                issue_block,
                "",
                "Source (tokenized):",
                source_text,
                "",
                "Broken translation:",
                translated_text,
            ]
        )

        repaired = self.generate(prompt, temperature=0.1, model=model).strip()
        if repaired.startswith("```"):
            lines = repaired.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            repaired = "\n".join(lines).strip()
        return repaired or None

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        鍒嗘瀽鏂囨湰锛屾彁鍙栨湳璇拰椋庢牸

        Args:
            text: 瑕佸垎鏋愮殑鏂囨湰锛堥€氬父鏄叏鏂囨垨鎽樿锛?

        Returns:
            Dict: 鍒嗘瀽缁撴灉
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
        妫€鏌ヨ瘧鏂囦竴鑷存€?

        Args:
            paragraphs: 娈佃惤鍒楄〃 [{"source": ..., "translation": ...}, ...]
            glossary: 鏈琛?{term: translation, ...}

        Returns:
            List[Dict]: 闂鍒楄〃
        """
        prompt = self._build_consistency_prompt(paragraphs, glossary)

        try:
            response = self.generate(prompt, response_format="json")
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Build the paragraph translation prompt via the shared prompt builder."""
        from ..prompts.prompt_builder import get_prompt_builder

        prompt_style = self._resolve_translation_prompt_style()
        builder = get_prompt_builder(style=prompt_style)

        # Extract runtime context for the paragraph prompt builder.
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
        format_tokens = context.get("format_tokens", [])
        term_usage = context.get("term_usage")

        # Delegate prompt assembly to the long-form prompt builder.
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
            format_tokens=format_tokens,
            term_usage=term_usage,
        )

        return prompt

    def _build_retranslation_prompt(
        self,
        source_text: str,
        current_translation: str,
        context: Dict[str, Any],
    ) -> str:
        """Build the paragraph retranslation prompt via the shared prompt builder."""
        from ..prompts.prompt_builder import get_prompt_builder

        builder = get_prompt_builder(style=self._resolve_translation_prompt_style())
        return builder.build_retranslation_prompt(
            source_text=source_text,
            current_translation=current_translation,
            glossary=context.get("glossary", []),
            previous_paragraphs=context.get("previous_paragraphs", []),
            next_preview=context.get("next_preview", []),
            article_title=context.get("article_title"),
            article_theme=context.get("article_theme"),
            article_structure=context.get("article_structure"),
            current_section_title=context.get("current_section_title"),
            heading_chain=context.get("heading_chain"),
            target_audience=context.get("target_audience"),
            translation_voice=context.get("translation_voice"),
            article_challenges=context.get("article_challenges"),
            style_guide=context.get("style_guide"),
            section_context=context.get("section_context"),
            learned_rules=context.get("learned_rules"),
            instruction=context.get("instruction"),
            format_tokens=context.get("format_tokens", []),
            term_usage=context.get("term_usage"),
        )

    def _resolve_translation_prompt_style(self) -> str:
        style = settings.translation_prompt_style.strip().lower()
        if style not in {"original", "simplified"}:
            return "original"
        return style

    def _build_analysis_prompt(self, text: str) -> str:
        """Build the analysis prompt."""
        return self.prompt_manager.get("analysis", text=text[:8000])

    def _build_consistency_prompt(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> str:
        """Build the consistency review prompt."""
        para_text = "\n\n".join(
            [
                f"[段落 {i+1}]\n原文：{p['source']}\n译文：{p['translation']}"
                for i, p in enumerate(paragraphs[:20])
            ]
        )

        glossary_text = "\n".join(
            [f"- {term} -> {trans}" for term, trans in glossary.items()]
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
        """Translate one full section in batch mode and return paragraph-aligned results."""
        prompt = self._build_batch_translation_prompt(
            section_text, section_title, context, paragraph_ids
        )

        try:
            response = self.generate(prompt, response_format="json", temperature=0.5)
            result = self._parse_json_response(response)
        except Exception as exc:
            logger.error("[Gemini] Batch translation failed: %s", exc)
            raise

        if isinstance(result, dict) and "translations" in result:
            return result["translations"]
        if isinstance(result, list):
            return result

        raise ValueError(
            "Batch translation response does not satisfy the JSON contract."
        )

    def translate_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
        subtitle: Optional[str] = None,
    ) -> Dict[str, str]:
        """Translate article title and optional subtitle in one call.

        Returns:
            dict with keys "title" and optionally "subtitle".
        """
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("structure_summary"):
                context_lines.append(
                    f"- Structure summary: {context['structure_summary']}"
                )
            if context.get("target_audience"):
                context_lines.append(f"- Target audience: {context['target_audience']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/title_translate.v2",
            context_block="\n".join(context_lines) if context_lines else "- None",
            title=title,
            subtitle=subtitle or "(无)",
        )
        raw = self.generate(prompt, temperature=0.3)

        result: Dict[str, str] = {}
        for line in raw.strip().splitlines():
            line = line.strip()
            if line.startswith("标题:") or line.startswith("标题："):
                result["title"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("副标题:") or line.startswith("副标题："):
                val = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                if val:
                    result["subtitle"] = val

        if not result.get("title"):
            result["title"] = raw.strip().splitlines()[0].strip()

        return result

    def translate_section_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Translate a section title with section-aware context."""
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("context"):
                context_lines.append(f"- Context: {context['context']}")
            if context.get("previous_section_title"):
                context_lines.append(
                    f"- Previous section: {context['previous_section_title']}"
                )
            if context.get("next_section_title"):
                context_lines.append(f"- Next section: {context['next_section_title']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/section_title_translate.v2",
            context_block="\n".join(context_lines) if context_lines else "- None",
            title=title,
        )
        return self.generate(prompt, temperature=0.3)

    def translate_all_section_titles(
        self,
        sections: List[Dict[str, Any]],
        article_theme: str = "",
    ) -> Dict[str, str]:
        """Translate all section titles in a single JSON API call.

        Builds one prompt listing all section titles and their neighbours,
        requests a JSON response ``{"translations": {"<id>": "<中文标题>"}}``,
        and returns the mapping.  If parsing fails or a section is missing,
        callers should fall back to ``translate_section_title`` per-entry.
        """
        if not sections:
            return {}

        chapter_lines: List[str] = []
        for i, sec in enumerate(sections, 1):
            sec_id = sec.get("id", f"s{i:02d}")
            title = sec.get("title", "")
            prev_t = sec.get("prev", "")
            next_t = sec.get("next", "")
            parts = [f'{i}. id={sec_id}, title="{title}"']
            if prev_t:
                parts.append(f'prev="{prev_t}"')
            if next_t:
                parts.append(f'next="{next_t}"')
            chapter_lines.append(", ".join(parts))

        theme_line = f"文章主题：{article_theme}" if article_theme else ""
        prompt = "\n".join(
            filter(
                None,
                [
                    "你是一位资深中英双语编辑，尤其擅长硬核科技长文领域。"
                    "请将下面所有章节标题翻译为简洁、自然、契合文章上下文的中文。",
                    "",
                    theme_line,
                    "",
                    "## 章节列表（id, 原标题, 前后章节供参考）",
                    "\n".join(chapter_lines),
                    "",
                    "## 输出规则",
                    '以 JSON 返回，格式：{"translations": {"<id>": "<中文标题>", ...}}',
                    "只输出 JSON，不要解释，不要额外文字。",
                ],
            )
        )

        try:
            raw = self.generate(prompt, response_format="json", temperature=0.3)
            result = self._parse_json_response(raw)
            translations = result.get("translations", {})
            if isinstance(translations, dict):
                logger.info(
                    "[Gemini] Batch section title translation: %d/%d titles returned",
                    len(translations),
                    len(sections),
                )
                return {str(k): str(v) for k, v in translations.items()}
        except Exception as exc:
            logger.warning(
                "[Gemini] Batch section title translation failed, will use per-title fallback: %s",
                exc,
            )

        # Fallback: delegate to base class (loops over translate_section_title)
        return super().translate_all_section_titles(
            sections, article_theme=article_theme
        )

    def _build_batch_translation_prompt(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> str:
        """Build the batch translation prompt."""
        format_token_rules = self._format_token_rules_for_prompt(
            context.get("format_tokens", []),
            context.get("format_token_count", 0),
        )
        enhanced_guidelines = build_section_guideline_lines(
            context.get("guidelines", []),
            section_role=context.get("section_role", ""),
            translation_voice=context.get("translation_voice", ""),
            target_audience=context.get("target_audience", ""),
            translation_notes=context.get("translation_notes"),
            format_token_rules=format_token_rules,
        )

        return self.prompt_manager.get(
            "longform/translation/section_batch_translate.v2",
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

    def _format_glossary_for_prompt(self, glossary: Any) -> str:
        """Render glossary context into prompt-friendly text."""
        return render_glossary_prompt_block(
            glossary,
            include_title=False,
            empty_text="无",
        )

    def _format_token_rules_for_prompt(self, tokens: Any, token_count: int = 0) -> str:
        """Render one compact rule block for hidden formatting tokens."""
        preview_tokens = limit_format_tokens(tokens)
        if not preview_tokens and not token_count:
            return ""

        lines = [
            "Hidden token rule: `[[[TYPE_N|...]]]` is a backend control token, not Markdown.",
            "Keep the wrapper, token type, and token id exactly unchanged.",
            "Only translate the text after `|`.",
            "Do not delete, duplicate, renumber, or move tokens to another paragraph.",
        ]
        preview_items = []
        for item in preview_tokens:
            if not isinstance(item, dict):
                continue
            token_id = item.get("id", "")
            token_text = item.get("text", "")
            token_type = item.get("type", "")
            if token_id and token_text:
                preview_items.append(f"{token_id}({token_type}): {token_text}")
        if preview_items:
            lines.append("Tokens in this request: " + "; ".join(preview_items))
        elif token_count:
            lines.append(f"This request contains {token_count} hidden format tokens.")
        return " ".join(lines)

    def _format_challenges_for_prompt(self, challenges: Any) -> str:
        """Render article translation risks into prompt-friendly text."""
        normalized_challenges = build_article_challenge_payload(challenges)
        if not normalized_challenges:
            return "None"

        lines = []
        for item in normalized_challenges:
            location = item.get("location", "")
            issue = item.get("issue", "")
            suggestion = item.get("suggestion", "")
            line = str(issue).strip()
            if location:
                line = f"[{location}] {line}"
            if suggestion:
                line = f"{line}; suggestion: {suggestion}"
            if line:
                lines.append(f"- {line}")

        return "\n".join(lines) if lines else "None"

    def prescan_section_with_flash(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: Dict[str, str],
    ) -> Dict[str, Any]:
        """Run section prescan with the Flash model."""
        return self.prescan_section(
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms,
            model="flash",
        )


def create_gemini_provider(
    api_key: Optional[str] = None,
    backup_api_key: Optional[str] = None,
    model: str = "pro",
    model_type: str = "pro",
) -> GeminiProvider:
    """Convenience helper to create a Gemini provider."""
    return GeminiProvider(
        api_key=api_key,
        backup_api_key=backup_api_key,
        model=model,
        model_type=model_type,
    )
