"""
LLM Provider 工厂适配器

将新的配置系统适配到现有的 Provider 实现，支持：
- 从 YAML 配置创建 Provider
- 故障转移和重试逻辑
- 统一的错误处理
"""

import logging
import uuid
import time
from typing import Optional, Any, Dict
from functools import lru_cache
from threading import RLock
from .execution_context import generation_budget, remaining_timeout, bounded_sleep, route_scope

from .config_loader import get_config_loader
from .config_models import ProviderConfig, ModelConfig, APIKeyConfig, ProviderNetworkConfig
from .fallback_strategy import FallbackStrategy, AttemptPlan
from .base import LLMProvider
from .errors import (LLMError, LLMProxyConfigurationError,
                     LLMUpstreamUnavailableError, normalize_llm_transport_error)
from .network_policy import build_network_policy
from .network_policy import RuntimeNetworkPolicy

logger = logging.getLogger(__name__)
_provider_construction_lock = RLock()


class LLMNonRetryableError(LLMError):
    """provider 已判定「换 key/换模型也必然同样失败」的错误。

    典型场景：prompt 过长、token 数超限、内容被安全策略拦截、invalid argument。
    provider（如 GeminiProvider）识别后抛出该类型，故障转移层看到即刻中止整个
    attempt_plan，避免把秒级失败重放成 N 次无效调用、白烧每个 key 一次配额
    （审计 BE9）。类型定义在适配层是为了保持 provider 无关——适配器不得反向
    依赖任何具体 provider 的实现或私有判定函数。
    """


# 故障转移统计
_fallback_stats = {
    "total_requests": 0,
    "fallback_triggered": 0,
    "total_attempts": 0,
    "failed_requests": 0,
}


def get_fallback_stats() -> dict:
    """获取故障转移统计信息"""
    with _provider_construction_lock:
        return _fallback_stats.copy()


def _build_runtime_network_policy(
    provider_type: str,
    network_config: Optional[ProviderNetworkConfig],
) -> Optional[RuntimeNetworkPolicy]:
    provider_type = provider_type.strip().lower()

    if network_config is None:
        try:
            provider = get_config_loader().get_primary_provider_by_type(provider_type)
        except Exception:
            provider = None
        if provider is not None:
            network_config = provider.network

    if network_config is not None:
        try:
            return build_network_policy(provider_type, network_config)
        except ValueError as exc:
            raise LLMProxyConfigurationError(str(exc)) from exc

    return None


def _build_provider_runtime_kwargs(
    provider_config: ProviderConfig,
    model_config: ModelConfig,
) -> Dict[str, Any]:
    model_timeout = None
    model_runtime_config = getattr(model_config, "config", None)
    if isinstance(model_runtime_config, dict):
        model_timeout = model_runtime_config.get("timeout")

    if provider_config.type == "gemini":
        return {
            "request_timeout": model_timeout,
            "max_attempts": provider_config.retry_config.max_retries,
            "retry_delay": provider_config.retry_config.base_delay,
        }

    if provider_config.type == "vectorengine":
        return {
            "timeout": model_timeout,
            "max_retries": provider_config.retry_config.max_retries,
        }

    return {}


class ProviderAdapter:
    """Provider 适配器，支持故障转移"""

    def __init__(self, model_alias: str):
        """
        初始化 Provider 适配器

        Args:
            model_alias: 模型别名（如 "pro-official", "deepseek-v3.2"）
        """
        self.model_alias = model_alias
        self.config_loader = get_config_loader()
        self.llm_config = self.config_loader.load()
        # 缓存已构建的 provider 实例，按 (type, provider_id, real_model, api_key) 复用，
        # 避免每次 fallback attempt / 每次请求都重建 Provider 及其 genai Client/HTTP 会话。
        self._provider_cache: dict = {}

        # 构建故障转移计划
        self.fallback_strategy = FallbackStrategy(self.llm_config)
        self.attempt_plan = self.fallback_strategy.build_attempt_plan(model_alias)

        if not self.attempt_plan:
            raise ValueError(f"No valid attempt plan for model {model_alias}")

        logger.info(
            f"[ProviderAdapter] Initialized for {model_alias} with {len(self.attempt_plan)} attempts"
        )

    def create_provider(self, attempt: AttemptPlan) -> LLMProvider:
        with _provider_construction_lock:
            return self._create_provider_locked(attempt)

    def _create_provider_locked(self, attempt: AttemptPlan) -> LLMProvider:
        """
        根据尝试计划创建 Provider 实例

        Args:
            attempt: 尝试计划

        Returns:
            LLMProvider 实例
        """
        provider_config = attempt.provider
        model_config = attempt.model
        api_key = attempt.api_key.key

        # 懒初始化（兼容通过 __new__ 绕过 __init__ 构造的实例，如测试）
        cache = getattr(self, "_provider_cache", None)
        if cache is None:
            cache = self._provider_cache = {}

        cache_key = (
            provider_config.type,
            provider_config.provider_id,
            model_config.real_model,
            api_key,
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        network_policy = _build_runtime_network_policy(
            provider_config.type, provider_config.network
        )
        provider_runtime_kwargs = _build_provider_runtime_kwargs(
            provider_config, model_config
        )

        # 根据 provider type 创建对应的 Provider
        if provider_config.type == "gemini":
            from .gemini import GeminiProvider

            provider = GeminiProvider(
                api_key=api_key,
                model=model_config.real_model,
                network_policy=network_policy,
                **provider_runtime_kwargs,
            )

        elif provider_config.type == "vectorengine":
            from .vectorengine import VectorEngineProvider

            provider = VectorEngineProvider(
                api_key=api_key,
                base_url=provider_config.base_url,
                model=model_config.real_model,
                network_policy=network_policy,
                **provider_runtime_kwargs,
            )

        else:
            raise ValueError(f"Unknown provider type: {provider_config.type}")

        cache[cache_key] = provider
        return provider

    @classmethod
    def from_provider(cls, provider: LLMProvider, provider_type: str, model: str):
        """Bound legacy/custom-constructor calls without replacing their settings.

        No cross-provider configuration is invented for an explicitly constructed
        transport. It still gets the same empty/transient retry and timeout rules.
        """
        from types import SimpleNamespace

        adapter = cls.__new__(cls)
        adapter.model_alias = model
        adapter.timeout = getattr(provider, "request_timeout", None) or getattr(provider, "timeout", None) or 120
        adapter.attempt_plan = [SimpleNamespace(
            provider=SimpleNamespace(type=provider_type, provider_id=provider_type),
            model=SimpleNamespace(alias=model, real_model=model),
            api_key=SimpleNamespace(name="explicit"),
        )]
        adapter.create_provider = lambda attempt: provider
        return adapter

    def _bounded_attempt_plan(self):
        """One owner of retries: at most four transport requests per generation.

        Keep a slot for official fallback even with many relay keys/models.
        Explicit official aliases never leave the official provider.
        """
        plans = []
        seen = set()
        for plan in self.attempt_plan:
            key = (plan.provider.provider_id, plan.model.real_model,
                   getattr(plan.api_key, "key", getattr(plan.api_key, "name", "")))
            if key not in seen:
                seen.add(key)
                plans.append(plan)
        if "official" in self.model_alias.lower() or (plans and plans[0].provider.type == "gemini"):
            plans = [p for p in plans if p.provider.type == "gemini"]
        if len(plans) > 4:
            official = next((p for p in plans if p.provider.type == "gemini"), None)
            plans = plans[:4]
            if official is not None and not any(p.provider.type == "gemini" for p in plans):
                plans[-1] = official
        if len(plans) == 1:
            plans *= 2  # isolated route still gets one transient/empty retry
        return plans

    def as_llm_provider(self) -> LLMProvider:
        """Keep the concrete prompt/parsing API, but route every self.generate.

        A shallow instance copy avoids modifying the cached transport provider.
        Both concrete and inherited LLMProvider methods retain their signatures,
        optional results and parsing semantics; only the generation seam changes.
        """
        from copy import copy
        from types import MethodType

        plans = self._bounded_attempt_plan()
        if not plans:
            raise ValueError(f"No valid route for model {self.model_alias}")
        primary = self.create_provider(plans[0])
        facade = copy(primary)
        from src.services.work_checkpoints import fingerprint
        facade._route_fingerprint = fingerprint([
            {"provider": p.provider.provider_id, "model": p.model.real_model,
             "url": getattr(p.provider, "base_url", None),
             "config": getattr(p.model, "config", {}),
             "credential_digest": fingerprint(getattr(p.api_key, "key", "explicit"))}
            for p in plans
        ])
        facade.model_alias = self.model_alias
        facade._request_budget_config = dict(getattr(plans[0].model, "config", {}) or {})
        adapter = self

        def routed_generate(_self, prompt, response_format=None, temperature=None,
                            model=None, **kwargs):
            from .work_budget import current_generation_defaults
            phase = current_generation_defaults()
            if "temperature" in phase:
                temperature = phase["temperature"]
            for option in ("max_tokens", "timeout"):
                if option in phase:
                    kwargs.setdefault(option, phase[option])
            target = adapter
            if model and model not in (adapter.model_alias, adapter.attempt_plan[0].model.real_model):
                target = get_provider_adapter(model)
            return target.generate_with_fallback(
                prompt, response_format=response_format, temperature=temperature, **kwargs
            )

        facade.generate = MethodType(routed_generate, facade)
        return facade

    @generation_budget
    def generate_with_fallback(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        使用故障转移机制生成文本

        Args:
            prompt: 输入提示
            response_format: 响应格式（如 "json"）
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            生成的文本

        Raises:
            Exception: 所有尝试都失败时抛出最后一个异常
        """
        last_error = None
        provider_kwargs = dict(kwargs)
        timeout = provider_kwargs.pop("timeout", None)
        request_id = str(provider_kwargs.pop("request_id", "") or uuid.uuid4().hex[:8])
        result_metadata = provider_kwargs.pop("result_metadata", None)
        # Caller/provider retry settings must not multiply the adapter budget.
        provider_kwargs.pop("max_retries", None)
        provider_kwargs.pop("_single_attempt", None)

        # 更新统计
        _fallback_stats["total_requests"] += 1
        start_time = time.time()

        attempt_plan = self._bounded_attempt_plan()
        for idx, attempt in enumerate(attempt_plan, 1):
            try:
                _fallback_stats["total_attempts"] += 1

                logger.info(
                    f"[ProviderAdapter] request_id={request_id} "
                    f"Attempt {idx}/{len(attempt_plan)}: "
                    f"provider={attempt.provider.provider_id}, "
                    f"model={attempt.model.alias}, "
                    f"key={attempt.api_key.name}"
                )

                provider = self.create_provider(attempt)
                runtime = getattr(attempt.model, "config", {})
                runtime = runtime if isinstance(runtime, dict) else {}
                attempt_kwargs = dict(provider_kwargs)
                if attempt_kwargs.get("max_tokens") is None and runtime.get("max_tokens") is not None:
                    attempt_kwargs["max_tokens"] = runtime["max_tokens"]
                from .request_budget import RequestLimits, check_request
                window_keys = ("input_token_limit", "context_window_tokens", "output_token_limit")
                if any(runtime.get(k) for k in window_keys):
                    check_request(prompt, RequestLimits(
                        input_tokens=runtime.get("input_token_limit"),
                        context_tokens=runtime.get("context_window_tokens"),
                        output_tokens=runtime.get("output_token_limit"),
                        reserve_output_tokens=attempt_kwargs.get("max_tokens", getattr(provider, "max_tokens", None) or 8192),
                    ), model=attempt.model.real_model)
                route_timeout = runtime.get("timeout") or timeout
                with route_scope(attempt.provider.provider_id, getattr(attempt.provider, "rate_limit", None)):
                    result = provider.generate(
                        prompt=prompt,
                        response_format=response_format,
                        temperature=temperature if temperature is not None else runtime.get("temperature"),
                        timeout=remaining_timeout(route_timeout),
                        model=attempt.model.real_model,
                        _single_attempt=True,
                        **attempt_kwargs,
                    )

                if not isinstance(result, str) or not result.strip():
                    raise LLMUpstreamUnavailableError("LLM returned empty content")
                duration = time.time() - start_time
                if isinstance(result_metadata, dict):
                    result_metadata.update(
                        {
                            "model_used": attempt.model.alias,
                            "real_model_used": attempt.model.real_model,
                            "provider_used": attempt.provider.provider_id,
                            "fallback_used": idx > 1,
                            "attempt": idx,
                        }
                    )
                if idx > 1:
                    _fallback_stats["fallback_triggered"] += 1
                    logger.warning(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"Fallback succeeded on attempt {idx}/{len(attempt_plan)} "
                        f"after {duration:.2f}s"
                    )
                else:
                    logger.info(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"Success on first attempt in {duration:.2f}s"
                    )
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[ProviderAdapter] request_id={request_id} "
                    f"Attempt {idx}/{len(attempt_plan)} failed: {type(e).__name__}: {e}"
                )

                # provider 已判定为不可重试（prompt 过长 / 被安全策略拦截 / invalid
                # argument 等）：后续路由只是用同一份 prompt 重复触发同一个错误，
                # 直接中止，把秒级失败原样抛给调用方（审计 BE9）。
                normalized = normalize_llm_transport_error(e, provider_name=attempt.provider.type)
                status_code = getattr(e, "status_code", None)
                permanent_http = isinstance(status_code, int) and 400 <= status_code < 500 and status_code not in {408, 409, 429}
                if permanent_http or isinstance(e, LLMNonRetryableError) or normalized is None or not normalized.retryable:
                    _fallback_stats["failed_requests"] += 1
                    duration = time.time() - start_time
                    logger.error(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"Aborted at attempt {idx}/{len(attempt_plan)} on non-retryable error "
                        f"after {duration:.2f}s: {e}"
                    )
                    raise

                # 如果还有更多尝试，继续
                if idx < len(attempt_plan):
                    try:
                        bounded_sleep(min(0.5 * (2 ** (idx - 1)), 2.0))
                    except Exception:
                        _fallback_stats["failed_requests"] += 1
                        raise
                    continue
                else:
                    # 所有尝试都失败了
                    _fallback_stats["failed_requests"] += 1
                    duration = time.time() - start_time
                    logger.error(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"All {len(attempt_plan)} attempts failed for model {self.model_alias} "
                        f"after {duration:.2f}s. Stats: {_fallback_stats}"
                    )
                    raise last_error

        # 理论上不会到达这里
        raise last_error or Exception("All attempts failed")


@lru_cache(maxsize=32)
def get_provider_adapter(model_alias: str) -> ProviderAdapter:
    """
    获取 Provider 适配器（带缓存）

    Args:
        model_alias: 模型别名

    Returns:
        ProviderAdapter 实例
    """
    return ProviderAdapter(model_alias)


def create_provider_from_config(model_alias: str) -> LLMProvider:
    """
    从配置创建 Provider（简化接口，不使用故障转移）

    Args:
        model_alias: 模型别名

    Returns:
        LLMProvider 实例
    """
    config_loader = get_config_loader()
    provider_config = config_loader.get_provider_for_model(model_alias)
    model_config = config_loader.get_model_config(model_alias)

    if not provider_config or not model_config:
        raise ValueError(f"Model {model_alias} not found in configuration")

    # 获取第一个可用的 API Key
    api_key = next(
        (k.key for k in provider_config.api_keys if k.enabled and k.key),
        None
    )

    if not api_key:
        raise ValueError(f"No valid API key for model {model_alias}")

    network_policy = _build_runtime_network_policy(
        provider_config.type,
        provider_config.network,
    )
    provider_runtime_kwargs = _build_provider_runtime_kwargs(
        provider_config, model_config
    )

    # 根据 provider type 创建对应的 Provider
    if provider_config.type == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(
            api_key=api_key,
            model=model_config.real_model,
            network_policy=network_policy,
            **provider_runtime_kwargs,
        )

    elif provider_config.type == "vectorengine":
        from .vectorengine import VectorEngineProvider

        return VectorEngineProvider(
            api_key=api_key,
            base_url=provider_config.base_url,
            model=model_config.real_model,
            network_policy=network_policy,
            **provider_runtime_kwargs,
        )

    else:
        raise ValueError(f"Unknown provider type: {provider_config.type}")
