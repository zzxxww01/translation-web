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
from .errors import (
    LLMConfigurationError,
    LLMUpstreamUnavailableError,
    normalize_llm_transport_error,
)
from .network_policy import build_network_policy
from .usage_metrics import llm_usage_metrics


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
            max_retries=0,  # retries belong to ProviderAdapter, not hidden SDK requests
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
        started_at = time.monotonic()
        usage = None

        def record_failure(error: Exception) -> None:
            llm_usage_metrics.record_call(
                provider="vectorengine",
                model=model_name,
                duration_seconds=time.monotonic() - started_at,
                success=False,
                input_chars=len(prompt),
                error_type=type(error).__name__,
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )

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
                    max_retries=0,
                )
            response = client.chat.completions.create(**request_params)

            usage = getattr(response, "usage", None)
            choices = getattr(response, "choices", None)
            content = choices[0].message.content if choices else None
            if not isinstance(content, str) or not content.strip():
                raise LLMUpstreamUnavailableError(
                    f"VectorEngine returned empty content (model={model_name})"
                )
            input_tokens = getattr(usage, "prompt_tokens", None)
            output_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
            llm_usage_metrics.record_call(
                provider="vectorengine",
                model=model_name,
                duration_seconds=time.monotonic() - started_at,
                success=True,
                input_chars=len(prompt),
                output_chars=len(content or ""),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )

            logger.info(
                f"[VectorEngine] Success: model={model_name}, "
                f"tokens={total_tokens} "
                f"(in={input_tokens}, out={output_tokens})"
            )

            return content

        except RateLimitError as e:
            record_failure(e)
            logger.error(f"[VectorEngine] Rate limit exceeded: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APITimeoutError as e:
            record_failure(e)
            logger.error(f"[VectorEngine] Request timeout: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIConnectionError as e:
            record_failure(e)
            logger.error(f"[VectorEngine] Connection error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIError as e:
            record_failure(e)
            logger.error(f"[VectorEngine] API error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except Exception as e:
            record_failure(e)
            logger.error(f"[VectorEngine] Unexpected error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> str:
        """Translate text using the shared prompt builder"""
        context_data = dict(context or {})
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5, timeout=timeout)

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        from ..prompts.task_builders import paragraph_prompt
        return paragraph_prompt(text, context)

    def deep_analyze_with_term_verification(self, outline, sampled_text, high_freq_candidates, timeout=None):
        from ..prompts import get_prompt_manager
        from ..prompts.contracts import object_response
        high_freq_terms_list = "\n".join(
            f"{i + 1}. {term['term']} (出现 {term['frequency']} 次)"
            for i, term in enumerate(high_freq_candidates)
        )
        prompt = get_prompt_manager().render(
            "longform/analysis/deep_analyze_with_terms", outline=outline,
            sampled_text=sampled_text, high_freq_terms_list=high_freq_terms_list,
        )
        return object_response(self.generate(prompt, response_format="json", temperature=0.3, timeout=timeout),
                               ("theme", "sampled_terms", "verified_high_freq_terms"))

    def analyze(self, text: str) -> Dict[str, Any]:
        from ..prompts.task_builders import analysis_prompt
        from ..prompts.contracts import object_response
        result = object_response(self.generate(analysis_prompt(text), response_format="json", temperature=0.3), ("terms", "style"))
        if not isinstance(result["terms"], list) or not isinstance(result["style"], dict):
            raise ValueError("Invalid analysis schema")
        return result

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

        # 清理和解析响应
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        import json
        result = json.loads(response)
        return result

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

        # 清理和解析响应
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        import json
        result = json.loads(response)
        return result.get("verified_terms", [])

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

    def translate_section(self, section_text: str, section_title: str, context: Dict[str, Any],
                          paragraph_ids: List[str]) -> List[Dict[str, str]]:
        from ..prompts.contracts import parse_json, translation_items
        prompt = self._build_batch_translation_prompt(section_text, section_title, context, paragraph_ids)
        return translation_items(parse_json(self.generate(prompt, response_format="json", temperature=0.3)), paragraph_ids)

    def _build_batch_translation_prompt(self, section_text: str, section_title: str,
                                      context: Dict[str, Any], paragraph_ids: List[str]) -> str:
        from ..prompts.task_builders import section_prompt
        return section_prompt(section_text, section_title, context, paragraph_ids)


    def _build_source_metadata_batch_prompt(self, entries: List[Dict[str, str]], context: Dict[str, Any]) -> str:
        from ..prompts.task_builders import source_metadata_prompt
        return source_metadata_prompt(entries, context)

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


def create_vectorengine_provider(**kwargs) -> LLMProvider:
    """Factory function to create VectorEngine provider"""
    return VectorEngineProvider(**kwargs)
