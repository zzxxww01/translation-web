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

from .config_loader import get_config_loader
from .config_models import ProviderConfig, ModelConfig, APIKeyConfig, ProviderNetworkConfig
from .fallback_strategy import FallbackStrategy, AttemptPlan
from .base import LLMProvider
from .errors import LLMProxyConfigurationError
from .network_policy import build_network_policy
from .network_policy import RuntimeNetworkPolicy

logger = logging.getLogger(__name__)

# 故障转移统计
_fallback_stats = {
    "total_requests": 0,
    "fallback_triggered": 0,
    "total_attempts": 0,
    "failed_requests": 0,
}


def get_fallback_stats() -> dict:
    """获取故障转移统计信息"""
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

        # 构建故障转移计划
        self.fallback_strategy = FallbackStrategy(self.llm_config)
        self.attempt_plan = self.fallback_strategy.build_attempt_plan(model_alias)

        if not self.attempt_plan:
            raise ValueError(f"No valid attempt plan for model {model_alias}")

        logger.info(
            f"[ProviderAdapter] Initialized for {model_alias} with {len(self.attempt_plan)} attempts"
        )

    def create_provider(self, attempt: AttemptPlan) -> LLMProvider:
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
        network_policy = _build_runtime_network_policy(
            provider_config.type, provider_config.network
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

        # 更新统计
        _fallback_stats["total_requests"] += 1
        start_time = time.time()

        for idx, attempt in enumerate(self.attempt_plan, 1):
            try:
                _fallback_stats["total_attempts"] += 1

                logger.info(
                    f"[ProviderAdapter] request_id={request_id} "
                    f"Attempt {idx}/{len(self.attempt_plan)}: "
                    f"provider={attempt.provider.provider_id}, "
                    f"model={attempt.model.alias}, "
                    f"key={attempt.api_key.name}"
                )

                provider = self.create_provider(attempt)
                result = provider.generate(
                    prompt=prompt,
                    response_format=response_format,
                    temperature=temperature,
                    timeout=timeout,
                    model=attempt.model.real_model,
                    **provider_kwargs,
                )

                duration = time.time() - start_time
                if idx > 1:
                    _fallback_stats["fallback_triggered"] += 1
                    logger.warning(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"Fallback succeeded on attempt {idx}/{len(self.attempt_plan)} "
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
                    f"Attempt {idx}/{len(self.attempt_plan)} failed: {type(e).__name__}: {e}"
                )

                # 如果还有更多尝试，继续
                if idx < len(self.attempt_plan):
                    continue
                else:
                    # 所有尝试都失败了
                    _fallback_stats["failed_requests"] += 1
                    duration = time.time() - start_time
                    logger.error(
                        f"[ProviderAdapter] request_id={request_id} "
                        f"All {len(self.attempt_plan)} attempts failed for model {self.model_alias} "
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
