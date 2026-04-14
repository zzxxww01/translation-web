"""
LLM 配置数据模型

定义了 LLM 配置文件的数据结构，包括：
- APIKeyConfig: API Key 配置
- ModelConfig: 模型配置
- RetryConfig: 重试配置
- ProviderConfig: Provider 配置
- FallbackMapping: 故障转移映射
- LLMConfig: 完整的 LLM 配置
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class APIKeyConfig:
    """API Key 配置"""
    key: str
    priority: int
    name: str
    enabled: bool = True


@dataclass
class ModelConfig:
    """模型配置"""
    alias: str
    real_model: str
    name: str
    description: str
    priority: int
    supports_thinking: bool
    config: Dict[str, Any]
    enabled: bool = True


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int
    base_delay: float
    max_delay: float
    exponential_backoff: bool


@dataclass
class ProviderConfig:
    """Provider 配置"""
    provider_id: str
    type: str
    name: str
    description: str
    api_keys: List[APIKeyConfig]
    models: List[ModelConfig]
    retry_config: RetryConfig
    group_priority: int = 999  # 组优先级，数字越小越优先
    base_url: Optional[str] = None
    enabled: bool = True


@dataclass
class FallbackMapping:
    """故障转移映射"""
    from_models: List[str]
    to_models: List[str]
    condition: str


@dataclass
class FallbackRules:
    """故障转移规则"""
    within_provider: Dict[str, Any]
    cross_provider: Dict[str, Any]


@dataclass
class LLMConfig:
    """完整的 LLM 配置"""
    providers: Dict[str, ProviderConfig]
    fallback_rules: Dict[str, Any]
    task_defaults: Dict[str, str]
