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
from contextlib import contextmanager
from dataclasses import dataclass
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Lock, RLock
from typing import Optional, Dict, Any, List
from types import ModuleType

from src.settings import settings

from .base import LLMProvider
from .errors import (
    LLMConnectionError,
    LLMProxyConfigurationError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
    NormalizedLLMError,
    normalize_llm_transport_error,
)
from .config_loader import get_config_loader
from .network_policy import build_network_policy
from .network_policy import RuntimeNetworkPolicy
from .usage_metrics import llm_usage_metrics


logger = logging.getLogger(__name__)
_genai_module: ModuleType | None = None


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


def _resolve_default_network_policy() -> RuntimeNetworkPolicy | None:
    try:
        provider = get_config_loader().get_primary_provider_by_type("gemini")
    except Exception:
        return None

    if provider is None or provider.network is None:
        return None

    try:
        return build_network_policy("gemini", provider.network)
    except ValueError as exc:
        raise LLMProxyConfigurationError(str(exc)) from exc


def _get_primary_gemini_provider():
    try:
        return get_config_loader().get_primary_provider_by_type("gemini")
    except Exception:
        return None


def _resolve_effective_network_policy(
    requested_policy: Any | None,
) -> RuntimeNetworkPolicy | Any | None:
    configured_policy = _resolve_default_network_policy()
    if configured_policy is None:
        return requested_policy

    if requested_policy is None:
        return configured_policy

    requested_mode = str(getattr(requested_policy, "proxy_mode", "") or "").strip().lower()
    configured_mode = str(configured_policy.proxy_mode).strip().lower()
    if configured_mode == "required" and requested_mode and requested_mode != "required":
        raise LLMProxyConfigurationError(
            "Gemini proxy_mode=required is enforced by YAML and cannot be overridden."
        )
    return requested_policy


def _resolve_default_runtime_settings(
    model_selector: Optional[str],
) -> tuple[Optional[int], Optional[int], Optional[float]]:
    provider = _get_primary_gemini_provider()
    if provider is None:
        return None, None, None

    selected_model = None
    normalized_selector = (model_selector or "").strip().lower()
    normalized_alias = MODEL_ALIASES.get(normalized_selector, normalized_selector)

    for candidate in provider.models:
        candidate_alias = candidate.alias.strip().lower()
        candidate_real_model = candidate.real_model.strip().lower()
        if normalized_selector and (
            normalized_selector == candidate_alias
            or normalized_selector == candidate_real_model
            or candidate_alias.endswith(normalized_alias)
        ):
            selected_model = candidate
            break

    if selected_model is None and provider.models:
        selected_model = sorted(provider.models, key=lambda item: item.priority)[0]

    model_timeout = None
    if selected_model is not None and isinstance(selected_model.config, dict):
        model_timeout = selected_model.config.get("timeout")

    return (
        model_timeout,
        provider.retry_config.max_retries,
        provider.retry_config.base_delay,
    )


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
        request_timeout: Optional[int] = None,
        max_attempts: Optional[int] = None,
        retry_delay: Optional[float] = None,
        network_policy: Any | None = None,
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
        self.network_policy = _resolve_effective_network_policy(network_policy)

        if not self.api_keys:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY or GEMINI_BACKUP_API_KEY environment variable, or pass api_key."
            )

        self._client_cache: Dict[str, Any] = {}
        self._client_cache_lock = Lock()
        self.model_catalog = self._load_model_catalog()
        self.model_type = self._normalize_model_selector(model_type) or "pro"

        # Proxy configuration support.
        self.proxy_config = self._resolve_proxy_config()
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

        default_selector = settings.gemini_model or model or self.model_type
        config_timeout, config_max_attempts, config_retry_delay = (
            _resolve_default_runtime_settings(default_selector)
        )

        self.request_timeout = (
            request_timeout
            if request_timeout is not None
            else (config_timeout if config_timeout is not None else settings.gemini_timeout)
        )
        self.max_attempts = (
            max_attempts
            if max_attempts is not None
            else (
                config_max_attempts
                if config_max_attempts is not None
                else (settings.gemini_max_retries or settings.gemini_retry_count or 5)
            )
        )
        self.retry_delay = (
            retry_delay
            if retry_delay is not None
            else (
                config_retry_delay
                if config_retry_delay is not None
                else (settings.gemini_retry_delay or 0.5)
            )
        )
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

    def _network_proxy_mode(self) -> str:
        if self.network_policy is None:
            return "env"
        proxy_mode = getattr(self.network_policy, "proxy_mode", "env")
        return str(proxy_mode).strip().lower() or "env"

    def _resolve_proxy_config(self) -> Optional[Dict[str, str]]:
        proxy_mode = self._network_proxy_mode()
        if proxy_mode == "required":
            proxies = getattr(self.network_policy, "proxies", None)
            if not proxies:
                raise LLMProxyConfigurationError(
                    "Gemini proxy_mode=required but no proxy configuration was provided."
                )
            return dict(proxies)
        if proxy_mode == "disabled":
            return None
        return self._get_proxy_config()

    _proxy_env_lock = RLock()

    def _proxy_env_overrides(self) -> Dict[str, str]:
        if not self.proxy_config:
            return {}

        overrides: Dict[str, str] = {}
        http_proxy = self.proxy_config.get("http")
        https_proxy = self.proxy_config.get("https") or http_proxy
        no_proxy = getattr(self.network_policy, "no_proxy", None)

        if http_proxy:
            overrides["HTTP_PROXY"] = http_proxy
            overrides["http_proxy"] = http_proxy
        if https_proxy:
            overrides["HTTPS_PROXY"] = https_proxy
            overrides["https_proxy"] = https_proxy
        if no_proxy:
            overrides["NO_PROXY"] = no_proxy
            overrides["no_proxy"] = no_proxy
        return overrides

    @contextmanager
    def _temporary_proxy_env(self):
        overrides = self._proxy_env_overrides()
        proxy_mode = self._network_proxy_mode()
        clear_keys = []
        if proxy_mode == "disabled":
            clear_keys = [
                "HTTP_PROXY",
                "http_proxy",
                "HTTPS_PROXY",
                "https_proxy",
                "ALL_PROXY",
                "all_proxy",
            ]
        if not overrides and not clear_keys:
            yield
            return

        managed_keys = set(overrides) | set(clear_keys)
        previous = {key: os.environ.get(key) for key in managed_keys}
        with self._proxy_env_lock:
            try:
                for key in clear_keys:
                    os.environ.pop(key, None)
                for key, value in overrides.items():
                    os.environ[key] = value
                yield
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def _select_transport_label(self) -> str:
        env_override = os.getenv("GEMINI_USE_REST", "").strip().lower()
        if env_override in {"1", "true", "yes", "on"}:
            return "rest"
        return "sdk"

    def _use_rest_transport(self) -> bool:
        return self._select_transport_label() == "rest"

    def _normalize_generation_exception(
        self, exc: Exception, *, timeout: int | None
    ) -> Exception:
        if isinstance(exc, FutureTimeoutError):
            timeout_s = timeout if timeout is not None else self.request_timeout
            return LLMTimeoutError(f"Gemini request timed out after {timeout_s}s")
        normalized = normalize_llm_transport_error(exc, provider_name="Gemini")
        if normalized is not None:
            return normalized.error
        if exc.__class__.__module__.startswith("google.genai"):
            text = str(exc).strip()
            lower = text.lower()
            if any(
                phrase in lower
                for phrase in [
                    "response",
                    "payload",
                    "parse",
                    "parsed",
                    "malformed",
                    "unexpected",
                    "decode",
                    "schema",
                    "serialization",
                    "deserialization",
                    "function invocation",
                    "unknown function",
                    "unsupported function",
                ]
            ):
                return LLMUpstreamUnavailableError(
                    f"Gemini SDK response handling failed: {text}"
                )
            return LLMConnectionError(f"Gemini SDK transport failed: {text}")
        return exc

    def _create_client(self, genai_module: ModuleType, api_key: str):
        with self._temporary_proxy_env():
            try:
                return genai_module.Client(api_key=api_key)
            except TypeError:
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

    # Shared thread pool for timeout-guarded LLM calls
    _timeout_executor = ThreadPoolExecutor(max_workers=4)

    def _generate_with_timeout_fn(self, fn, timeout: int | None):
        if not timeout or timeout <= 0:
            return fn()
        future = self._timeout_executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise

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
        request_timeout: float | tuple[float, float] | None = None
        if timeout and timeout > 0:
            # Keep connect timeout short so proxy/TLS issues fail fast,
            # while preserving a longer read timeout for valid long responses.
            connect_timeout = min(max(float(timeout) * 0.2, 5.0), 15.0)
            request_timeout = (connect_timeout, float(timeout))

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=request_timeout,
            proxies=self.proxy_config,
        )
        if response.status_code >= 400:
            self._raise_rest_http_error(response, model)
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini REST response: {data}") from exc

    # ============ 閿欒鍒嗙被鏂规硶 ============

    @staticmethod
    def _raise_rest_http_error(response: requests.Response, model: str) -> None:
        detail_parts = [f"Gemini REST {response.status_code} for model={model}"]
        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            err = payload.get("error", {})
            if isinstance(err, dict):
                status = str(err.get("status", "")).strip()
                message = str(err.get("message", "")).strip()
                details = err.get("details")
                if status:
                    detail_parts.append(f"status={status}")
                if message:
                    detail_parts.append(message)
                if details:
                    detail_parts.append(f"details={json.dumps(details, ensure_ascii=False)[:500]}")

        body = (response.text or "").strip()
        if body and not isinstance(payload, dict):
            detail_parts.append(f"body={body[:500]}")

        error = requests.HTTPError(" | ".join(detail_parts))
        error.response = response
        raise error

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
            or ("safety" in text and "blocked" in text)
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
        timeout: int | None,
    ) -> str:
        if self._use_rest_transport():
            return self._generate_with_rest(
                prompt=prompt,
                api_key=attempt.api_key,
                timeout=timeout,
                temperature=temperature,
                response_mime_type=response_mime_type,
                model_override=attempt.model_name,
            )

        client = self._get_client(attempt.api_key)

        def _call():
            config = {"temperature": temperature}
            if response_mime_type:
                config["response_mime_type"] = response_mime_type
            with self._temporary_proxy_env():
                resp = client.models.generate_content(
                    model=attempt.model_name,
                    contents=prompt,
                    config=config,
                )
            return resp.text

        return self._generate_with_timeout_fn(_call, timeout)

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: Optional[int] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
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
        effective_timeout = timeout if timeout is not None else self.request_timeout

        logger.info(
            "[Gemini] generate start len=%s model=%s backup_model=%s keys=%s timeout=%ss transport=%s",
            len(prompt),
            primary_model,
            self.backup_model or "-",
            len(self.api_keys),
            effective_timeout,
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
                    timeout=effective_timeout,
                )
                duration = time.monotonic() - start_time
                call_number = llm_usage_metrics.increment_api_calls()
                logger.info(
                    "[API #%d] model=%s duration=%.1fs (key=%s attempt=%s/%s)",
                    call_number,
                    attempt.model_name,
                    duration,
                    attempt.key_role,
                    attempt_index + 1,
                    max_attempts,
                )
                return text.strip()
            except Exception as exc:
                exc = self._normalize_generation_exception(
                    exc, timeout=effective_timeout
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


def create_gemini_provider(
    api_key: Optional[str] = None,
    backup_api_key: Optional[str] = None,
    model: str = "pro",
    model_type: str = "pro",
    request_timeout: Optional[int] = None,
    max_attempts: Optional[int] = None,
    retry_delay: Optional[float] = None,
    network_policy: Any | None = None,
) -> GeminiProvider:
    """Convenience helper to create a Gemini provider."""
    return GeminiProvider(
        api_key=api_key,
        backup_api_key=backup_api_key,
        model=model,
        model_type=model_type,
        request_timeout=request_timeout,
        max_attempts=max_attempts,
        retry_delay=retry_delay,
        network_policy=network_policy,
    )
