"""
VectorEngine LLM Provider

OpenAI-compatible relay API provider for multiple models.
Supports DeepSeek, GPT-4, Claude, and other models through VectorEngine.
"""

import logging
import time
from typing import Optional, Dict, Any, List

import httpx
from openai import OpenAI
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from src.settings import settings
from .base import LLMProvider
from .config_loader import get_config_loader
from .errors import LLMConfigurationError, normalize_llm_transport_error
from .network_policy import build_network_policy


logger = logging.getLogger(__name__)


class VectorEngineProvider(LLMProvider):
    """VectorEngine API Provider (OpenAI-compatible)"""

    @staticmethod
    def _get_primary_provider_config():
        try:
            return get_config_loader().get_primary_provider_by_type("vectorengine")
        except Exception:
            return None

    @classmethod
    def _resolve_effective_network_policy(cls, requested_policy: Any | None) -> Any | None:
        provider = cls._get_primary_provider_config()
        if provider is None or provider.network is None:
            return requested_policy

        try:
            configured_policy = build_network_policy("vectorengine", provider.network)
        except ValueError as exc:
            raise LLMConfigurationError(str(exc)) from exc
        if requested_policy is None:
            return configured_policy

        requested_mode = str(getattr(requested_policy, "proxy_mode", "") or "").strip().lower()
        configured_mode = str(configured_policy.proxy_mode).strip().lower()
        if requested_mode and requested_mode != configured_mode:
            raise LLMConfigurationError(
                "VectorEngine network policy is enforced by YAML and cannot be overridden."
            )
        return configured_policy

    @classmethod
    def _resolve_default_runtime_settings(
        cls,
        model_selector: Optional[str],
    ) -> tuple[Optional[float], Optional[int]]:
        provider = cls._get_primary_provider_config()
        if provider is None:
            return None, None

        selected_model = None
        normalized_selector = (model_selector or "").strip().lower()
        for candidate in provider.models:
            candidate_alias = candidate.alias.strip().lower()
            candidate_real_model = candidate.real_model.strip().lower()
            if normalized_selector and (
                normalized_selector == candidate_alias
                or normalized_selector == candidate_real_model
            ):
                selected_model = candidate
                break

        if selected_model is None and provider.models:
            selected_model = sorted(provider.models, key=lambda item: item.priority)[0]

        model_timeout = None
        if selected_model is not None and isinstance(selected_model.config, dict):
            model_timeout = selected_model.config.get("timeout")

        return model_timeout, provider.retry_config.max_retries

    def _build_http_client(self) -> httpx.Client:
        policy = self.network_policy
        if policy is None:
            return httpx.Client(trust_env=False)

        client_kwargs: Dict[str, Any] = {
            "trust_env": bool(getattr(policy, "trust_env", False)),
        }
        if getattr(policy, "use_proxy", False):
            proxies = getattr(policy, "proxies", None) or {}
            proxy_url = proxies.get("https") or proxies.get("http")
            if proxy_url:
                client_kwargs["proxy"] = proxy_url

        return httpx.Client(**client_kwargs)

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        network_policy: Any | None = None,
    ):
        """
        Initialize VectorEngine Provider

        Args:
            api_key: VectorEngine API Key (defaults to VECTORENGINE_API_KEY env var)
            base_url: API base URL (defaults to https://api.vectorengine.ai/v1)
            model: Default model name (e.g., "deepseek-v3.2", "gpt-4o")
        """
        super().__init__()

        self.api_key = api_key or settings.vectorengine_api_key
        if not self.api_key:
            raise ValueError(
                "VectorEngine API key is required. Set VECTORENGINE_API_KEY environment variable, or pass api_key."
            )

        self.base_url = base_url or settings.vectorengine_base_url
        self.default_model = model or settings.vectorengine_default_model
        self.temperature = settings.vectorengine_temperature
        self.max_tokens = settings.vectorengine_max_tokens
        config_timeout, config_max_retries = self._resolve_default_runtime_settings(
            model or settings.vectorengine_default_model
        )
        self.timeout = (
            timeout if timeout is not None else (
                config_timeout if config_timeout is not None else settings.vectorengine_timeout
            )
        )
        self.max_retries = (
            max_retries if max_retries is not None else (
                config_max_retries if config_max_retries is not None else settings.vectorengine_max_retries
            )
        )
        self.network_policy = self._resolve_effective_network_policy(network_policy)

        # Initialize OpenAI client
        http_client = self._build_http_client()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            http_client=http_client,
        )

        logger.info(
            f"[VectorEngine] Initialized with base_url={self.base_url}, default_model={self.default_model}"
        )

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Generate text using VectorEngine API

        Args:
            prompt: Input prompt
            response_format: "json" for JSON output (optional)
            temperature: Sampling temperature (defaults to config)
            model: Model name override (defaults to default_model)
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        model_name = model or self.default_model
        temp = temperature if temperature is not None else self.temperature
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        request_timeout = timeout if timeout is not None else self.timeout

        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
        }

        # Add response format if JSON requested
        if response_format == "json":
            request_params["response_format"] = {"type": "json_object"}

        try:
            logger.info(f"[VectorEngine] Calling model={model_name}, temp={temp}, timeout={request_timeout}")
            client = self.client
            if hasattr(self.client, "with_options"):
                client = self.client.with_options(
                    timeout=request_timeout,
                    max_retries=(0 if timeout is not None else self.max_retries),
                )
            response = client.chat.completions.create(**request_params)

            content = response.choices[0].message.content

            logger.info(
                f"[VectorEngine] Success: model={model_name}, "
                f"tokens={response.usage.total_tokens} "
                f"(in={response.usage.prompt_tokens}, out={response.usage.completion_tokens})"
            )

            return content

        except RateLimitError as e:
            logger.error(f"[VectorEngine] Rate limit exceeded: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APITimeoutError as e:
            logger.error(f"[VectorEngine] Request timeout: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIConnectionError as e:
            logger.error(f"[VectorEngine] Connection error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIError as e:
            logger.error(f"[VectorEngine] API error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except Exception as e:
            logger.error(f"[VectorEngine] Unexpected error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e


def create_vectorengine_provider(**kwargs) -> LLMProvider:
    """Factory function to create VectorEngine provider"""
    return VectorEngineProvider(**kwargs)
