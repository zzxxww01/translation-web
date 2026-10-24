"""
故障转移策略管理器

负责构建 LLM 调用的故障转移计划，支持：
- 同组内 Key 轮换
- 同组内模型切换
- 跨组模型故障转移
"""

from typing import List, Optional
import logging

from .config_models import ProviderConfig, ModelConfig, APIKeyConfig, LLMConfig, is_relay_provider
from .config_loader import resolve_config_model_alias

logger = logging.getLogger(__name__)


class AttemptPlan:
    """单次尝试计划"""

    def __init__(self, provider: ProviderConfig, model: ModelConfig, api_key: APIKeyConfig):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def __repr__(self):
        return f"AttemptPlan(provider={self.provider.provider_id}, model={self.model.alias}, key={self.api_key.name})"


class FallbackStrategy:
    """故障转移策略管理器"""

    def __init__(self, config: LLMConfig):
        self.config = config

    def build_attempt_plan(self, initial_model_alias: str) -> List[AttemptPlan]:
        """
        构建完整的尝试计划

        优先级：
        1. 同组内：主模型 + 所有 Key（按 priority 排序）
        2. 同组内：其他模型 + 所有 Key（按模型 priority 排序）
        3. 跨组：映射的其他组模型 + 所有 Key

        主模型在中转上时，第 1 步之后先降级到官方组（同家族优先），再试中转上的其他模型。
        """
        attempts = []
        resolved_alias = self._resolve_config_model_alias(initial_model_alias)
        if not resolved_alias:
            raise ValueError(f"Model {initial_model_alias} not found in any provider")

        # 获取初始模型的 Provider
        initial_provider = self._get_provider_for_model(resolved_alias)

        initial_model = self._get_model_config(resolved_alias)

        # 第一阶段：同组内故障转移
        within_attempts = self._build_within_provider_attempts(initial_provider, initial_model)

        # 第二阶段：跨组故障转移
        cross_attempts = []
        if self.config.fallback_rules.get('cross_provider', {}).get('enabled', False):
            cross_attempts = self._build_cross_provider_attempts(resolved_alias)

        if is_relay_provider(initial_provider):
            same_model = [a for a in within_attempts if a.model.alias == initial_model.alias]
            attempts = (
                same_model
                + [a for a in cross_attempts if not is_relay_provider(a.provider)]
                + [a for a in within_attempts if a.model.alias != initial_model.alias]
                + [a for a in cross_attempts if is_relay_provider(a.provider)]
            )
        else:
            attempts = within_attempts + cross_attempts

        logger.info(
            f"Built attempt plan with {len(attempts)} attempts for model {resolved_alias} "
            f"(within: {len(within_attempts)}, cross: {len(attempts) - len(within_attempts)})"
        )

        return attempts

    def _resolve_config_model_alias(self, alias: str) -> Optional[str]:
        """Resolve public/legacy aliases to a canonical YAML config alias."""
        return resolve_config_model_alias(self.config, alias)

    def _build_within_provider_attempts(
        self, provider: ProviderConfig, initial_model: ModelConfig
    ) -> List[AttemptPlan]:
        """构建同组内的尝试计划"""
        attempts = []

        # 按 priority 排序 API Keys（priority 越小越优先）
        sorted_keys = sorted(
            [k for k in provider.api_keys if k.enabled and k.key],
            key=lambda k: k.priority
        )

        if not sorted_keys:
            logger.warning(f"Provider {provider.provider_id} has no valid API keys")
            return attempts

        # 按 priority 排序模型（priority 越小越优先）
        sorted_models = sorted(
            [m for m in provider.models if m.enabled],
            key=lambda m: m.priority
        )

        # 策略：key_first - 先尝试所有 Key，再切换模型
        strategy = self.config.fallback_rules.get('within_provider', {}).get('strategy', 'key_first')

        if strategy == 'key_first':
            # 初始模型 + 所有 Key
            for key in sorted_keys:
                attempts.append(AttemptPlan(provider, initial_model, key))

            # 其他模型 + 所有 Key
            for model in sorted_models:
                if model.alias != initial_model.alias and model.fallback:
                    for key in sorted_keys:
                        attempts.append(AttemptPlan(provider, model, key))

        return attempts

    def _build_cross_provider_attempts(self, initial_model_alias: str) -> List[AttemptPlan]:
        """构建跨组的尝试计划（基于组优先级和模型名称匹配）"""
        attempts = []

        if not self.config.fallback_rules.get('cross_provider', {}).get('enabled', False):
            return attempts

        # 获取模型优先级关键词
        model_priority_keywords = self.config.fallback_rules.get('cross_provider', {}).get(
            'model_priority_keywords',
            ["claude", "gemini", "gpt", "deepseek", "kimi", "doubao", "qwen"]
        )

        # 获取初始模型的 Provider
        initial_provider = self._get_provider_for_model(initial_model_alias)
        if not initial_provider:
            return attempts

        def family(name: str) -> int:
            """模型名命中的第一个关键词序号；都不命中时排在最后。"""
            name = name.lower()
            return next((idx for idx, keyword in enumerate(model_priority_keywords) if keyword in name),
                        len(model_priority_keywords))

        initial_model = self._get_model_config(initial_model_alias)
        initial_family = min(family(initial_model.alias), family(initial_model.real_model))

        # 收集所有其他组的模型（排除当前组）
        other_models = []
        for provider in self.config.providers.values():
            if provider.provider_id == initial_provider.provider_id or not provider.enabled:
                continue

            for model in provider.models:
                if model.enabled and model.fallback:
                    other_models.append((provider, model))

        # 排序：同家族优先（如中转 DeepSeek → 官方 DeepSeek），再按组优先级、模型名称匹配优先级、模型 priority
        def get_sort_key(item):
            provider, model = item
            model_family = min(family(model.alias), family(model.real_model))
            same_family = model_family == initial_family < len(model_priority_keywords)
            return (not same_family, provider.group_priority, model_family, model.priority, model.alias)

        sorted_models = sorted(other_models, key=get_sort_key)

        # 为每个模型构建尝试（所有 Key）
        for provider, model in sorted_models:
            sorted_keys = sorted(
                [k for k in provider.api_keys if k.enabled and k.key],
                key=lambda k: k.priority
            )
            for key in sorted_keys:
                attempts.append(AttemptPlan(provider, model, key))

        return attempts

    def _get_provider_for_model(self, alias: str) -> Optional[ProviderConfig]:
        """根据模型别名获取 Provider"""
        for provider in self.config.providers.values():
            for model in provider.models:
                if model.alias == alias:
                    return provider
        return None

    def _get_model_config(self, alias: str) -> Optional[ModelConfig]:
        """根据别名获取模型配置"""
        for provider in self.config.providers.values():
            for model in provider.models:
                if model.alias == alias:
                    return model
        return None
