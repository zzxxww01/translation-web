"""
LLM 配置加载器

负责加载和解析 YAML 配置文件，支持：
- 环境变量替换 (${VAR} 语法)
- 配置验证
- 单例模式
"""

import yaml
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Any
import logging

from .config_models import (
    LLMConfig,
    ProviderConfig,
    APIKeyConfig,
    ModelConfig,
    RetryConfig,
)

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = "config/llm_providers.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[LLMConfig] = None

    def load(self) -> LLMConfig:
        """加载并解析配置文件"""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请从 {self.config_path}.example 复制并配置"
            )

        logger.info(f"加载 LLM 配置文件: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # 验证配置结构
        self._validate_config_structure(raw_config)

        # 环境变量替换
        raw_config = self._resolve_env_vars(raw_config)

        # 解析为数据类
        providers = {}
        for provider_id, provider_data in raw_config['providers'].items():
            providers[provider_id] = self._parse_provider(provider_id, provider_data)

        self._config = LLMConfig(
            providers=providers,
            fallback_rules=raw_config['fallback_rules'],
            task_defaults=raw_config['task_defaults']
        )

        logger.info(f"成功加载 {len(providers)} 个 Provider 配置")
        return self._config

    def _validate_config_structure(self, config: dict) -> None:
        """验证配置文件结构"""
        required_fields = ['providers', 'fallback_rules', 'task_defaults']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置文件缺少必需字段: {field}")

        if not isinstance(config['providers'], dict):
            raise ValueError("'providers' 必须是字典类型")

        if not config['providers']:
            raise ValueError("至少需要配置一个 Provider")

        # 验证 fallback_rules 结构
        if 'within_provider' not in config['fallback_rules']:
            raise ValueError("fallback_rules 缺少 'within_provider' 配置")
        if 'cross_provider' not in config['fallback_rules']:
            raise ValueError("fallback_rules 缺少 'cross_provider' 配置")

    def _resolve_env_vars(self, data: Any) -> Any:
        """递归替换 ${VAR} 为环境变量值"""
        if isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            value = os.getenv(var_name)
            if value is None:
                logger.warning(f"环境变量 {var_name} 未设置")
                return ""
            value = value.strip()
            if not value:
                logger.warning(f"环境变量 {var_name} 为空")
            return value
        return data

    def _parse_provider(self, provider_id: str, data: dict) -> ProviderConfig:
        """解析单个 Provider 配置"""
        api_keys = [
            APIKeyConfig(**key_data) for key_data in data['api_keys']
        ]
        models = [
            ModelConfig(**model_data) for model_data in data['models']
        ]
        retry_config = RetryConfig(**data['retry_config'])

        return ProviderConfig(
            provider_id=provider_id,
            type=data['type'],
            name=data['name'],
            description=data['description'],
            api_keys=api_keys,
            models=models,
            retry_config=retry_config,
            group_priority=data.get('group_priority', 999),
            base_url=data.get('base_url'),
            enabled=data.get('enabled', True)
        )

    def get_model_config(self, alias: str) -> Optional[ModelConfig]:
        """根据别名获取模型配置"""
        if not self._config:
            self._config = self.load()

        for provider in self._config.providers.values():
            for model in provider.models:
                if model.alias == alias:
                    return model
        return None

    def get_provider_for_model(self, alias: str) -> Optional[ProviderConfig]:
        """根据模型别名获取 Provider 配置"""
        if not self._config:
            self._config = self.load()

        for provider in self._config.providers.values():
            for model in provider.models:
                if model.alias == alias:
                    return provider
        return None

    def list_all_models(self) -> Dict[str, Dict[str, Any]]:
        """列出所有可用的模型"""
        if not self._config:
            self._config = self.load()

        models = {}
        for provider in self._config.providers.values():
            if not provider.enabled:
                continue

            for model in provider.models:
                if not model.enabled:
                    continue

                # 检查是否有可用的 API Key
                has_valid_key = any(k.enabled and k.key for k in provider.api_keys)

                models[model.alias] = {
                    "name": model.name,
                    "description": model.description,
                    "provider": provider.name,
                    "provider_id": provider.provider_id,
                    "supports_thinking": model.supports_thinking,
                    "available": has_valid_key,
                }

        return models


# 全局单例
_config_loader: Optional[ConfigLoader] = None
_loader_lock = threading.Lock()


def get_config_loader() -> ConfigLoader:
    """获取配置加载器单例（线程安全）"""
    global _config_loader
    if _config_loader is None:
        with _loader_lock:
            # Double-check locking pattern
            if _config_loader is None:
                _config_loader = ConfigLoader()
    return _config_loader


def reset_config_loader():
    """重置配置加载器（用于测试）"""
    global _config_loader
    with _loader_lock:
        _config_loader = None
