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
from contextlib import contextmanager, nullcontext
from contextvars import copy_context
from dataclasses import dataclass
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Lock, RLock
from typing import Optional, Dict, Any, List
from types import ModuleType

from src.settings import settings
from src.core.longform_context import (
    build_article_challenge_payload,
    build_section_guideline_lines,
    limit_format_tokens,
)
from src.core.glossary_prompt import render_glossary_prompt_block

from .base import LLMProvider
from .output_validation import ensure_complete_generation, gemini_response_text
from .errors import (
    LLMConnectionError,
    LLMConfigurationError,
    LLMDeadlineExceededError,
    LLMRequestCancelledError,
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
from .token_usage import gemini_usage, TokenUsage
from .execution_context import generation_budget, remaining_timeout, bounded_sleep, output_limit, check_active
from .rate_limiter import transport_slot


logger = logging.getLogger(__name__)

# 传输层超时相对 future 门限的比例。取小于 1 让 httpx 先于 future.result() 醒来，
# 这样超时的 worker 通常已经退出，_timeout_leak_count 才只统计真正的泄漏。
_TRANSPORT_TIMEOUT_RATIO = 0.9
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
            or candidate_alias == normalized_alias
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
        # 钉具体版本，不用 *-latest：见 config/llm_providers.yaml 同处说明
        "default": "gemini-3.6-flash",
        "description": "Fast model with lower cost",
        "max_output_tokens": 65536,
        "supports_thinking": False,
    },
    "pro": {
        "env_var": "GEMINI_PRO_MODEL",
        "default": "gemini-3.1-pro-preview",
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


@dataclass(frozen=True)
class GeminiGenerationResult:
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    billable_output_tokens: Optional[int] = None


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

    def _sdk_http_options(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Build explicit SDK transport options from the provider policy.

        google-genai/httpx trusts HTTP_PROXY and HTTPS_PROXY by default.  Merely
        returning ``None`` from ``_resolve_proxy_config`` therefore does not make
        ``proxy_mode: disabled`` a direct connection: ambient proxy variables can
        still be picked up by the SDK.  Pass trust_env explicitly so the YAML
        policy remains authoritative.
        """
        policy = self.network_policy
        if policy is None:
            return None

        trust_env = bool(getattr(policy, "trust_env", False))
        client_args: Dict[str, Any] = {"trust_env": trust_env}
        async_client_args: Dict[str, Any] = {"trust_env": trust_env}

        if getattr(policy, "use_proxy", False):
            proxies = getattr(policy, "proxies", None) or {}
            proxy_url = proxies.get("https") or proxies.get("http")
            if proxy_url:
                client_args["proxy"] = proxy_url
                async_client_args["proxy"] = proxy_url

        return {
            "client_args": client_args,
            "async_client_args": async_client_args,
        }

    def _build_rest_session(self) -> requests.Session:
        """Create a REST client that obeys the same network policy as the SDK."""
        session = requests.Session()
        if self.network_policy is not None:
            session.trust_env = bool(
                getattr(self.network_policy, "trust_env", False)
            )
        return session

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
        if not overrides:
            yield
            return

        with self._proxy_env_lock:
            previous = {key: os.environ.get(key) for key in overrides}
            try:
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
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        http_options = self._sdk_http_options()
        if http_options is not None:
            client_kwargs["http_options"] = http_options

        with self._temporary_proxy_env():
            try:
                return genai_module.Client(**client_kwargs)
            except TypeError:
                previous = os.environ.get("GEMINI_API_KEY")
                os.environ["GEMINI_API_KEY"] = api_key
                try:
                    fallback_kwargs: Dict[str, Any] = {}
                    if http_options is not None:
                        fallback_kwargs["http_options"] = http_options
                    return genai_module.Client(**fallback_kwargs)
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

    # Shared thread pool for timeout-guarded LLM calls.
    # 章节级翻译现在通过 asyncio.to_thread 真并发执行；SDK 传输模式下每个 generate()
    # 都经此池提交。若仍固定 4 worker，会把高并发翻译重新卡回 4 路串行。改为按需放大
    # （主要是网络 IO 等待，worker 多无妨），可用 GEMINI_TIMEOUT_POOL_WORKERS 覆盖。
    _timeout_executor = ThreadPoolExecutor(
        max_workers=max(16, int(os.getenv("GEMINI_TIMEOUT_POOL_WORKERS", "0") or 0)),
        thread_name_prefix="gemini-timeout",
    )

    # 超时后无法回收的 worker 计数：future.cancel() 对已开始执行的任务返回 False，
    # 线程要等传输层超时才会退出。累计该计数便于把「所有调用瞬间超时」定位到
    # 本地线程池被挤满，而不是误判为上游劣化（审计 BE8）。
    _timeout_leak_lock = Lock()
    _timeout_leak_count = 0
    # 装的 google-genai 不支持 per-request http_options 时置位，避免每个请求都
    # 先失败一次再重发（旧 SDK 环境等于每次两轮往返）。
    _http_options_unsupported = False

    def _generate_with_timeout_fn(self, fn, timeout: int | None):
        if not timeout or timeout <= 0:
            return fn()
        context = copy_context()
        future = self._timeout_executor.submit(context.run, fn)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            if not future.cancel():
                with GeminiProvider._timeout_leak_lock:
                    GeminiProvider._timeout_leak_count += 1
                    leaked = GeminiProvider._timeout_leak_count
                logger.warning(
                    "[Gemini] timeout worker still running after %ss; pool workers occupied so far=%d "
                    "(pool size=%d). 若该计数持续增长，说明传输层超时未生效或代理挂死。",
                    timeout,
                    leaked,
                    getattr(self._timeout_executor, "_max_workers", -1),
                )
            raise

    def _resolve_max_output_tokens(self) -> int:
        """解析当前模型的最大输出 token 数。

        此前 SDK / REST 生成配置都未传 max_output_tokens，输出依赖供应商默认值，
        长 section / 长 JSON 可能被静默截断（再喂给 _parse_json_response 退化为 {}）。
        """
        if output_limit() is not None:
            return output_limit()
        config = MODEL_CONFIG.get(self.model_type)
        if config and isinstance(config.get("max_output_tokens"), int):
            return config["max_output_tokens"]
        return 65536

    def _generate_with_rest(
        self,
        prompt: str,
        api_key: str,
        timeout: int | None,
        temperature: float = 0.7,
        response_mime_type: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> GeminiGenerationResult:
        model = model_override or self.model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": self._resolve_max_output_tokens(),
        }
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

        with transport_slot(), self._build_rest_session() as session:
            budget = remaining_timeout(timeout)
            if budget is not None:
                request_timeout = (min(budget, 15.0), budget)
            response = session.post(
                url,
                json=payload,
                headers=headers,
                timeout=request_timeout,
                proxies=self.proxy_config,
            )
        if response.status_code >= 400:
            self._raise_rest_http_error(response, model)
        data = response.json()
        usage = gemini_usage(data.get("usageMetadata"))
        try:
            text = gemini_response_text(data)
        except Exception as exc:
            exc._llm_usage = usage
            raise
        return GeminiGenerationResult(text=text, **usage.as_metrics())

    @staticmethod
    def _usage_value(usage: Any, *names: str) -> Optional[int]:
        if usage is None:
            return None
        for name in names:
            if isinstance(usage, dict):
                value = usage.get(name)
            else:
                value = getattr(usage, name, None)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None

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
        # 注意：auth 错误（401/403/invalid key）是确定性失败，重试同一 key 永远不会成功，
        # 因此不计入 retryable，避免在最终路由上空耗整个指数退避预算。auth 失败仍允许
        # 在 has_fresh_attempt 分支轮换到其它 key/model（见 generate 重试循环）。
        text = error_str.lower()
        return (
            GeminiProvider._is_rate_limited(error_str)
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
    def _as_non_retryable(exc: Exception) -> Exception:
        """把已判定为不可重试的异常换成 fallback 层能识别的类型（审计 BE9）。

        适配器只认类型、不认具体 provider 的判定函数，避免强耦合；此处延迟导入
        provider_adapter，防止 gemini ←→ provider_adapter 的模块级循环导入。
        原始异常保留在 __cause__ 中，消息原样透传给上层错误映射。
        """
        try:
            from .provider_adapter import LLMNonRetryableError
        except Exception:  # pragma: no cover - 兜底，导入失败时不改变原有行为
            return exc

        if isinstance(exc, LLMNonRetryableError):
            return exc
        wrapped = LLMNonRetryableError(str(exc))
        wrapped.__cause__ = exc
        return wrapped

    @staticmethod
    def _is_non_retryable_error(error_str: str) -> bool:
        text = error_str.lower()
        return (
            GeminiProvider._is_provider_agnostic_failure(error_str)
            or "prompt is too long" in text
            or "too many tokens" in text
            or "context length" in text
        )

    @staticmethod
    def _is_provider_agnostic_failure(error_str: str) -> bool:
        """换 key／换模型／换 provider 都救不回来的失败。

        只有这一类才向上层 fallback 宣告"别试了"。上下文超长一类**不算**：
        它是模型相关的，换到上下文窗口更大的模型或另一家 provider 仍有机会
        成功，整盘中止会白白砍掉本可成功的回退。
        """
        text = error_str.lower()
        return (
            "invalid argument" in text
            or "request contains an invalid argument" in text
            or "unsupported response mime type" in text
            or "candidate was blocked" in text
            or ("safety" in text and "blocked" in text)
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

    def _generate_once(self, prompt, attempt, temperature, response_mime_type, timeout):
        if self._use_rest_transport():
            return self._generate_with_timeout_fn(lambda: self._generate_with_rest(
                prompt=prompt, api_key=attempt.api_key, timeout=timeout,
                temperature=temperature, response_mime_type=response_mime_type,
                model_override=attempt.model_name), timeout)

        client = self._get_client(attempt.api_key)

        def _call():
            with transport_slot():
                budget = remaining_timeout(timeout)
                config = {
                    "temperature": temperature,
                    "max_output_tokens": self._resolve_max_output_tokens(),
                    "http_options": {"retry_options": {"attempts": 1}},
                }
                if response_mime_type:
                    config["response_mime_type"] = response_mime_type
                if budget is not None:
                    config["http_options"]["timeout"] = max(1, int(budget * _TRANSPORT_TIMEOUT_RATIO * 1000))
                # Configured clients already have explicit per-client proxy and
                # trust_env settings. Do not serialize network IO under an env lock.
                proxy_scope = nullcontext() if getattr(self, "network_policy", None) is not None else self._temporary_proxy_env()
                with proxy_scope:
                    try:
                        resp = client.models.generate_content(model=attempt.model_name, contents=prompt, config=config)
                    except (TypeError, ValueError) as exc:
                        if "http_options" in str(exc):
                            raise LLMConfigurationError("Installed Gemini SDK must support request timeout and retry_options") from exc
                        raise
                usage = gemini_usage(getattr(resp, "usage_metadata", None))
                try:
                    candidates = getattr(resp, "candidates", None)
                    if candidates:
                        ensure_complete_generation(getattr(candidates[0], "finish_reason", None))
                    text = resp.text
                    if text is None:
                        feedback = getattr(resp, "prompt_feedback", None)
                        block_reason = getattr(feedback, "block_reason", None) if feedback else None
                        if block_reason:
                            raise LLMConfigurationError("Gemini blocked this generation")
                        raise LLMUpstreamUnavailableError("Gemini returned no text")
                except Exception as exc:
                    exc._llm_usage = usage
                    raise
                return GeminiGenerationResult(text=text, **usage.as_metrics())

        return self._generate_with_timeout_fn(_call, timeout)

    @generation_budget
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
        if _kwargs.get("_single_attempt"):
            attempt_plan, max_attempts = attempt_plan[:1], 1
        effective_timeout = timeout if timeout is not None else self.request_timeout
        response_mime_type = "application/json" if response_format == "json" else None
        backoff_index = 0
        for attempt_index in range(max_attempts):
            check_active()
            plan_index = min(attempt_index, len(attempt_plan) - 1)
            attempt = attempt_plan[plan_index]
            started = time.monotonic()
            usage = TokenUsage()
            try:
                generation = self._generate_once(prompt=prompt, attempt=attempt,
                    temperature=temperature if temperature is not None else 0.7,
                    response_mime_type=response_mime_type,
                    timeout=remaining_timeout(effective_timeout))
                if isinstance(generation, GeminiGenerationResult):
                    text = (generation.text or "").strip()
                    usage = TokenUsage(**{key: getattr(generation, key) for key in TokenUsage.__dataclass_fields__})
                else:
                    text = str(generation or "").strip()
                if not text:
                    raise LLMUpstreamUnavailableError("Gemini returned empty content")
                llm_usage_metrics.record_call(provider="gemini", model=attempt.model_name,
                    duration_seconds=time.monotonic() - started, success=True,
                    input_chars=len(prompt), output_chars=len(text), attempts=1,
                    **usage.as_metrics())
                return text
            except Exception as exc:
                usage = getattr(exc, "_llm_usage", usage)
                error = self._normalize_generation_exception(exc, timeout=effective_timeout)
                # Record EACH failed transport attempt, including known usage on
                # truncated/refused outputs. Do not hide attempts in success totals.
                llm_usage_metrics.record_call(provider="gemini", model=attempt.model_name,
                    duration_seconds=time.monotonic() - started, success=False,
                    input_chars=len(prompt), attempts=1, error_type=type(error).__name__,
                    **usage.as_metrics())
                if isinstance(error, (LLMDeadlineExceededError, LLMRequestCancelledError, LLMConfigurationError)):
                    raise error
                error_text = self._error_to_text(error)
                if self._is_non_retryable_error(error_text):
                    if self._is_provider_agnostic_failure(error_text):
                        raise self._as_non_retryable(error)
                    raise error
                fresh = plan_index < len(attempt_plan) - 1
                retryable = self._is_retryable_error(error_text) or (fresh and self._is_auth_error(error_text))
                if attempt_index >= max_attempts - 1 or not retryable:
                    raise error
                if self._is_rate_limited(error_text) or not fresh:
                    delay = self._retry_delay_for_error(error_text, backoff_index)
                    backoff_index += 1
                    bounded_sleep(delay)
        raise RuntimeError("Gemini generation has no usable attempts")

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None) -> str:
        """
        缈昏瘧鏂囨湰

        Args:
            text: 瑕佺炕璇戠殑鍘熸枃
            context: 涓婁笅鏂囦俊鎭?
            timeout: 超时时间（秒）

        Returns:
            str: 缈昏瘧缁撴灉
        """
        context_data = dict(context or {})
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5, timeout=timeout)

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

    def repair_format_tokens(self, source_text: str, translated_text: str,
                             format_tokens: List[Dict[str, Any]], issues: Optional[List[str]] = None,
                             model: Optional[str] = None) -> Optional[str]:
        return super().repair_format_tokens(source_text, translated_text, format_tokens, issues, model)

    def deep_analyze_with_term_verification(
        self,
        outline: str,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        合并深度分析和术语验证（方案6）

        Args:
            outline: 文档大纲
            sampled_text: 采样文本
            high_freq_candidates: 高频术语候选列表
            timeout: 超时时间（秒）

        Returns:
            Dict: 合并分析结果
        """
        # 构建高频术语列表文本
        high_freq_terms_list = "\n".join([
            f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
            for i, term in enumerate(high_freq_candidates)
        ])

        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze_with_terms",
            outline=outline,
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 解析JSON响应
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] Failed to parse JSON response: {e}")
            logger.error(f"[Gemini] Response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def deep_analyze_document(
        self,
        outline: str,
        sampled_text: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        深度分析文档（不包含术语验证）

        Args:
            outline: 文档大纲
            sampled_text: 采样文本
            timeout: 超时时间（秒）

        Returns:
            Dict: 分析结果
        """
        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze",
            outline=outline,
            sampled_text=sampled_text
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 解析JSON响应
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] Failed to parse JSON response: {e}")
            logger.error(f"[Gemini] Response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def verify_high_frequency_terms(
        self,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        验证高频术语候选

        Args:
            sampled_text: 采样文本
            high_freq_candidates: 高频术语候选列表
            timeout: 超时时间（秒）

        Returns:
            List[Dict]: 验证通过的术语列表
        """
        # 构建高频术语列表文本
        high_freq_terms_list = "\n".join([
            f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
            for i, term in enumerate(high_freq_candidates)
        ])

        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/verify_terms",
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 解析JSON响应
        try:
            result = json.loads(response)
            return result.get("verified_terms", [])
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] Failed to parse JSON response: {e}")
            logger.error(f"[Gemini] Response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def analyze(self, text: str) -> Dict[str, Any]:
        from ..prompts.task_builders import analysis_prompt
        from ..prompts.contracts import object_response
        result = object_response(self.generate(analysis_prompt(text), response_format="json", temperature=0.3), ("terms", "style"))
        if not isinstance(result["terms"], list) or not isinstance(result["style"], dict):
            raise ValueError("Invalid analysis schema")
        return result

    def check_consistency(self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]) -> List[Dict[str, Any]]:
        from ..prompts.task_builders import consistency_prompt
        from ..prompts.contracts import object_response, PromptContractError
        result = object_response(self.generate(consistency_prompt(paragraphs, glossary), response_format="json", temperature=0.3), ("issues",))
        if not isinstance(result["issues"], list):
            raise PromptContractError("issues must be a list")
        for issue in result["issues"]:
            index = issue.get("paragraph_index") if isinstance(issue, dict) else None
            if type(index) is not int or not 0 <= index < len(paragraphs):
                raise PromptContractError("Invalid consistency issue index")
        return result["issues"]

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        from ..prompts.task_builders import paragraph_prompt
        return paragraph_prompt(text, context)

    def _build_retranslation_prompt(self, source_text: str, current_translation: str, context: Dict[str, Any]) -> str:
        from ..prompts.task_builders import paragraph_prompt
        return paragraph_prompt(source_text, context, current=current_translation)

    def _resolve_translation_prompt_style(self) -> str:
        style = settings.translation_prompt_style.strip().lower()
        if style not in {"original", "simplified"}:
            return "original"
        return style

    def _build_analysis_prompt(self, text):
        from ..prompts.task_builders import analysis_prompt
        return analysis_prompt(text)

    def _build_consistency_prompt(self, paragraphs, glossary):
        from ..prompts.task_builders import consistency_prompt
        return consistency_prompt(paragraphs, glossary)

    def _build_source_metadata_batch_prompt(self, entries: List[Dict[str, str]], context: Dict[str, Any]) -> str:
        from ..prompts.task_builders import source_metadata_prompt
        return source_metadata_prompt(entries, context)

    def translate_section(self, section_text: str, section_title: str, context: Dict[str, Any],
                          paragraph_ids: List[str]) -> List[Dict[str, str]]:
        from ..prompts.contracts import parse_json, translation_items
        prompt = self._build_batch_translation_prompt(section_text, section_title, context, paragraph_ids)
        return translation_items(parse_json(self.generate(prompt, response_format="json", temperature=0.3)), paragraph_ids)

    @staticmethod
    def _coerce_translation_items(
        raw: Any, *, expected_count: Optional[int] = None, label: str = "batch"
    ) -> List[Dict[str, str]]:
        """规整批翻 JSON 输出，只保留含 id/translation 的合法条目。

        模型偶尔会返回字符串列表、缺键或多/少条目。直接交给下游
        ``{item["id"]: item["translation"]}`` 会抛 KeyError/TypeError，
        中断整章并绕过本应触发的逐段回退。这里宽容地丢弃畸形条目，
        让调用方的 per-paragraph fallback 干净接管。
        """
        if not isinstance(raw, list):
            logger.warning("[Gemini] %s translation output is not a list: %r", label, type(raw))
            return []
        cleaned: List[Dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            pid = item.get("id")
            translation = item.get("translation")
            if pid is None or not isinstance(translation, str):
                continue
            cleaned.append({"id": str(pid), "translation": translation})
        if expected_count is not None and len(cleaned) != expected_count:
            logger.warning(
                "[Gemini] %s translation count mismatch: got %d well-formed of expected %d",
                label,
                len(cleaned),
                expected_count,
            )
        return cleaned

    def translate_source_metadata_batch(self, entries: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        from ..prompts.contracts import parse_json, translation_items
        prompt = self._build_source_metadata_batch_prompt(entries, context or {})
        return translation_items(parse_json(self.generate(prompt, response_format="json", temperature=0.2)), [e["id"] for e in entries])

    def translate_title(self, title: str, context: Optional[Dict[str, Any]] = None,
                        subtitle: Optional[str] = None) -> Dict[str, str]:
        from ..prompts.task_builders import title_prompt
        from ..prompts.contracts import parse_title_lines
        return parse_title_lines(self.generate(title_prompt(title, subtitle, context or {}), temperature=0.3))

    def translate_section_title(self, title: str, context: Optional[Dict[str, Any]] = None,
                                *, glossary_block: str = "", whitelist_rules: str = "") -> str:
        from ..prompts.task_builders import section_title_prompt
        from ..prompts.contracts import PromptContractError
        result = self.generate(section_title_prompt(title, context or {}, glossary_block, whitelist_rules), temperature=0.3)
        if not isinstance(result, str) or not result.strip():
            raise PromptContractError("Empty section title")
        return result.strip()

    def translate_all_section_titles(self, sections: List[Dict[str, Any]], *, article_theme: str = "",
                                     glossary_block: str = "", whitelist_rules: str = "") -> Dict[str, str]:
        return super().translate_all_section_titles(sections, article_theme, glossary_block=glossary_block, whitelist_rules=whitelist_rules)

    def _build_batch_translation_prompt(self, section_text: str, section_title: str,
                                      context: Dict[str, Any], paragraph_ids: List[str]) -> str:
        from ..prompts.task_builders import section_prompt
        return section_prompt(section_text, section_title, context, paragraph_ids)

    def _format_glossary_for_prompt(
        self,
        glossary: Any,
        term_usage: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """Render glossary context into prompt-friendly text."""
        return render_glossary_prompt_block(
            glossary,
            include_title=False,
            term_usage=term_usage,
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
        """Run section prescan with the default model."""
        return self.prescan_section(
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms,
        )


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
