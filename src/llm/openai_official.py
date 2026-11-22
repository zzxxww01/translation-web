"""Official OpenAI transport; shared translation prompts, no cross-brand fallback."""
import logging
import time

from openai import OpenAI, APIStatusError

from .base import LLMProvider
from .vectorengine import VectorEngineProvider
from .errors import LLMError, LLMConfigurationError, LLMUpstreamUnavailableError, normalize_llm_transport_error
from .execution_context import generation_budget, remaining_timeout, positive_token_limit
from .output_validation import ensure_complete_generation
from .rate_limiter import transport_slot
from .token_usage import openai_usage
from .usage_metrics import llm_usage_metrics

logger = logging.getLogger(__name__)


class OpenAIOfficialProvider(VectorEngineProvider):
    """Reuse vendor-neutral task methods, never relay settings or transport.

    gpt-6.1-sol was verified on official Chat Completions. Use the supported
    max_completion_tokens parameter and omit temperature (task/phase defaults
    must not leak unsupported sampling parameters to reasoning models).
    """

    def __init__(self, api_key, model, base_url=None, timeout=120, network_policy=None, **kwargs):
        LLMProvider.__init__(self)
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required")
        if base_url not in (None, "https://api.openai.com/v1"):
            raise LLMConfigurationError("Official OpenAI requires api.openai.com")
        self.default_model = model
        self.timeout = timeout or 120
        self.max_tokens = 32768
        self.network_policy = network_policy
        self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1",
                             max_retries=0, timeout=self.timeout,
                             http_client=self._build_http_client())

    @generation_budget
    def generate(self, prompt, response_format=None, temperature=None, model=None,
                 timeout=None, **kwargs):
        model_name = model or self.default_model
        started = time.monotonic()
        usage = None
        success = False
        error_type = None
        content = ""
        params = {"model": model_name, "messages": [{"role": "user", "content": prompt}],
                  "max_completion_tokens": positive_token_limit(kwargs.get("max_tokens", self.max_tokens)),
                  "store": False}
        if response_format == "json":
            params["response_format"] = {"type": "json_object"}
        try:
            with transport_slot():
                response = self.client.with_options(timeout=remaining_timeout(timeout or self.timeout),
                                                    max_retries=0).chat.completions.create(**params)
            usage = response.usage
            # Reject mismatched upstream identity rather than label another model GPT.
            if response.model != model_name:
                raise LLMConfigurationError("Official OpenAI returned an unexpected model identity")
            if response.choices:
                ensure_complete_generation(response.choices[0].finish_reason)
                content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise LLMUpstreamUnavailableError("Official OpenAI returned empty content")
            success = True
            logger.info("[OpenAI official] model=%s response_id=%s", response.model, response.id)
            return content
        except Exception as exc:
            error_type = type(exc).__name__
            # Do not log provider bodies, input or credentials, even on permanent 4xx.
            normalized = normalize_llm_transport_error(exc, provider_name="OpenAI official")
            if isinstance(exc, APIStatusError) and 400 <= exc.status_code < 500 and exc.status_code not in (408, 409, 429):
                raise LLMConfigurationError(f"Official OpenAI rejected request (HTTP {exc.status_code})") from None
            if normalized is not None:
                raise type(normalized.error)("Official OpenAI transport failed") from None
            if isinstance(exc, LLMError):
                raise
            raise LLMUpstreamUnavailableError("Official OpenAI request failed") from None
        finally:
            llm_usage_metrics.record_call(provider="openai", model=model_name,
                duration_seconds=time.monotonic() - started, success=success,
                input_chars=len(prompt), output_chars=len(content or ""), error_type=error_type,
                **openai_usage(usage).as_metrics())

    @generation_budget
    def generate_with_web_search(self, prompt, model=None, timeout=None, **kwargs):
        """Chatbot 联网回答：Responses API 的 web_search 工具，搜不搜由模型自己决定。
        返回 {"text", "sources": [{"title", "url"}]}；出错规则和 generate 一样。"""
        model_name = model or self.default_model
        started = time.monotonic()
        usage = None
        success = False
        error_type = None
        content = ""
        try:
            with transport_slot():
                response = self.client.with_options(timeout=remaining_timeout(timeout or self.timeout),
                                                    max_retries=0).responses.create(
                    model=model_name, input=prompt, tools=[{"type": "web_search"}],
                    max_output_tokens=positive_token_limit(kwargs.get("max_tokens", self.max_tokens)), store=False)
            usage = response.usage
            if response.model != model_name:
                raise LLMConfigurationError("Official OpenAI returned an unexpected model identity")
            content = response.output_text
            if not isinstance(content, str) or not content.strip():
                raise LLMUpstreamUnavailableError("Official OpenAI returned empty content")
            sources, seen = [], set()
            for item in response.output or []:
                for part in getattr(item, "content", None) or []:
                    for note in getattr(part, "annotations", None) or []:
                        url = getattr(note, "url", None)
                        if getattr(note, "type", "") == "url_citation" and url and url not in seen:
                            seen.add(url)
                            sources.append({"title": getattr(note, "title", "") or url, "url": url})
            success = True
            logger.info("[OpenAI official] web search model=%s response_id=%s sources=%d",
                        response.model, response.id, len(sources))
            return {"text": content, "sources": sources}
        except Exception as exc:
            error_type = type(exc).__name__
            normalized = normalize_llm_transport_error(exc, provider_name="OpenAI official")
            if isinstance(exc, APIStatusError) and 400 <= exc.status_code < 500 and exc.status_code not in (408, 409, 429):
                raise LLMConfigurationError(f"Official OpenAI rejected request (HTTP {exc.status_code})") from None
            if normalized is not None:
                raise type(normalized.error)("Official OpenAI transport failed") from None
            if isinstance(exc, LLMError):
                raise
            raise LLMUpstreamUnavailableError("Official OpenAI request failed") from None
        finally:
            llm_usage_metrics.record_call(provider="openai", model=model_name,
                duration_seconds=time.monotonic() - started, success=success,
                input_chars=len(prompt), output_chars=len(content or ""), error_type=error_type,
                **openai_usage(usage).as_metrics())
