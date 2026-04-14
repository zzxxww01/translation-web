# LLM 配置系统文档

## 概述

本系统实现了一个灵活、可扩展的 LLM 多供应商配置和故障转移机制,支持:

- 多供应商管理 (Gemini、VectorEngine 等)
- 每个供应商支持多个 API Key (主备机制)
- 三级故障转移策略 (Key 级别 → 同组模型 → 跨组模型)
- 前端分组模型选择器
- 向后兼容旧的环境变量配置

## 架构设计

### 1. 配置文件结构

配置文件位于 `config/llm_providers.yaml`,采用 YAML 格式:

```yaml
providers:
  gemini-official:
    type: gemini
    name: "Gemini 官方 API"
    description: "Google 官方 API，稳定可靠"
    group_priority: 1  # 组优先级,数字越小越优先
    api_keys:
      - key: "${GEMINI_API_KEY}"
        priority: 1
        name: "主 Key"
      - key: "${GEMINI_BACKUP_API_KEY}"
        priority: 2
        name: "备用 Key"
    models:
      - alias: "flash-official"
        real_model: "gemini-flash-latest"
        name: "Flash"
        description: "快速低成本"
        priority: 2
        supports_thinking: false
        config:
          temperature: 0.7
          max_tokens: 8192
          timeout: 60
    retry_config:
      max_retries: 5
      base_delay: 0.5
      max_delay: 16.0
      exponential_backoff: true

fallback_rules:
  within_provider:
    enabled: true
    strategy: "key_first"  # 先尝试所有 Key,再切换模型
  
  cross_provider:
    enabled: true
    model_priority_keywords: ["claude", "gemini", "gpt", "deepseek", "kimi", "doubao", "qwen"]

task_defaults:
  longform: "deepseek-relay"
  post: "flash-official"
  analysis: "pro-official"
```

### 2. 核心组件

#### ConfigLoader (src/llm/config_loader.py)

负责加载和解析 YAML 配置文件:

- 支持环境变量替换 (`${VAR_NAME}`)
- 单例模式,避免重复加载
- 提供便捷的查询方法 (`get_model_config`, `get_provider_for_model`)

```python
from src.llm.config_loader import get_config_loader

loader = get_config_loader()
config = loader.load()
model = loader.get_model_config("pro-official")
provider = loader.get_provider_for_model("pro-official")
```

#### FallbackStrategy (src/llm/fallback_strategy.py)

构建故障转移计划:

```python
from src.llm.fallback_strategy import FallbackStrategy

strategy = FallbackStrategy(config)
plan = strategy.build_attempt_plan("pro-official")

# plan 是一个 AttemptPlan 列表,按优先级排序:
# 1. pro-official + 主Key
# 2. pro-official + 备用Key
# 3. flash-official + 主Key
# 4. flash-official + 备用Key
# 5. deepseek-relay + 主Key (跨组)
# ...
```

故障转移优先级:

1. **同组内 Key 轮换**: 先尝试主 Key,失败后尝试备用 Key
2. **同组内模型切换**: 所有 Key 都失败后,切换到同组其他模型
3. **跨组模型故障转移**: 同组所有模型都失败后,根据 `model_priority_keywords` 切换到其他组

#### ProviderAdapter (src/llm/provider_adapter.py)

包装现有的 Provider 实现,添加自动故障转移能力:

```python
from src.llm.provider_adapter import get_provider_adapter

adapter = get_provider_adapter("pro-official")
result = adapter.generate_with_fallback(
    prompt="Translate this text",
    temperature=0.7
)
```

适配器会自动:
- 按照故障转移计划尝试不同的 Provider/Model/Key 组合
- 记录每次尝试的日志
- 在所有尝试都失败后抛出最后一个异常

### 3. API 端点

#### GET /models

返回分组的模型列表:

```json
{
  "providers": [
    {
      "id": "gemini-official",
      "name": "Gemini 官方 API",
      "description": "Google 官方 API，稳定可靠",
      "models": [
        {
          "alias": "flash-official",
          "name": "Flash",
          "description": "快速低成本",
          "supports_thinking": false,
          "priority": 2,
          "available": true
        }
      ]
    }
  ]
}
```

- `available` 字段表示该模型是否有可用的 API Key
- 按 `group_priority` 排序 Provider
- 按 `priority` 排序每个 Provider 内的模型

#### GET /models/legacy

返回扁平的模型列表 (向后兼容):

```json
{
  "models": [
    {
      "alias": "flash-official",
      "provider": "gemini",
      "real_model": "gemini-flash-latest",
      "description": "快速低成本",
      "supports_thinking": false
    }
  ]
}
```

### 4. 前端集成

#### ModelSelector 组件

位于 `web/frontend/src/components/ModelSelector.tsx`:

```tsx
import { ModelSelector } from '@/components/ModelSelector';

<ModelSelector
  value={selectedModel}
  onChange={setSelectedModel}
  className="..."
  disabled={false}
/>
```

特性:
- 使用 `<optgroup>` 显示分组结构
- 显示模型的思考能力标记 `[思考]`
- 禁用不可用的模型 `[不可用]`
- 自动加载和缓存模型列表

#### 类型定义

位于 `web/frontend/src/shared/types/index.ts`:

```typescript
export interface ModelInfo {
  alias: string;
  name: string;
  description: string;
  supports_thinking: boolean;
  priority: number;
  available: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  models: ModelInfo[];
}

export interface ModelListResponse {
  providers: ProviderInfo[];
}
```

## 使用指南

### 添加新的供应商

1. 在 `config/llm_providers.yaml` 中添加新的 provider:

```yaml
providers:
  new-provider:
    type: openai  # 或其他类型
    name: "新供应商"
    description: "描述"
    group_priority: 3
    api_keys:
      - key: "${NEW_PROVIDER_API_KEY}"
        priority: 1
        name: "主 Key"
    models:
      - alias: "new-model"
        real_model: "actual-model-name"
        name: "新模型"
        description: "模型描述"
        priority: 1
        supports_thinking: false
        config:
          temperature: 0.7
    retry_config:
      max_retries: 3
      base_delay: 1.0
      max_delay: 10.0
      exponential_backoff: true
```

2. 如果需要新的 Provider 类型,在 `src/llm/provider_adapter.py` 中添加:

```python
elif provider_config.type == "openai":
    from .openai import OpenAIProvider
    return OpenAIProvider(
        api_key=api_key,
        model=model_config.real_model,
    )
```

### 添加新的模型

在现有 provider 的 `models` 列表中添加:

```yaml
- alias: "new-model-alias"
  real_model: "real-model-name"
  name: "显示名称"
  description: "模型描述"
  priority: 3  # 数字越小越优先
  supports_thinking: false
  config:
    temperature: 0.7
    max_tokens: 8192
    timeout: 120
```

### 配置故障转移规则

修改 `fallback_rules`:

```yaml
fallback_rules:
  within_provider:
    enabled: true
    strategy: "key_first"  # 或 "model_first"
  
  cross_provider:
    enabled: true
    model_priority_keywords: ["claude", "gemini", "gpt", "deepseek"]
```

- `within_provider.strategy`:
  - `key_first`: 先尝试所有 Key,再切换模型
  - `model_first`: 先切换模型,再尝试其他 Key (未实现)

- `cross_provider.model_priority_keywords`: 跨组故障转移时的模型优先级

### 在代码中使用

#### 方式 1: 使用 generate_with_fallback (推荐)

```python
from src.api.utils.llm_factory import generate_with_fallback

result = generate_with_fallback(
    prompt="Your prompt here",
    model="pro-official",  # 可选,不指定则使用任务默认模型
    task_type="post",      # 用于选择默认模型
    temperature=0.7
)
```

#### 方式 2: 直接使用 ProviderAdapter

```python
from src.llm.provider_adapter import get_provider_adapter

adapter = get_provider_adapter("pro-official")
result = adapter.generate_with_fallback(
    prompt="Your prompt here",
    temperature=0.7
)
```

#### 方式 3: 使用 Factory (无故障转移)

```python
from src.llm.factory import create_llm_provider

provider = create_llm_provider("pro-official")
result = provider.generate(
    prompt="Your prompt here",
    model="gemini-2.5-pro",
    temperature=0.7
)
```

## 测试

运行测试:

```bash
python -m pytest tests/test_llm_config_system.py -v
```

测试覆盖:
- 配置加载和解析
- 故障转移计划构建
- API 响应结构
- 模型查询功能

## 日志示例

启用故障转移后的日志输出:

```
[ProviderAdapter] Initialized for pro-official with 12 attempts
[ProviderAdapter] Attempt 1/12: provider=gemini-official, model=pro-official, key=主Key
[ProviderAdapter] Attempt 1 failed: RateLimitError: 429 Too Many Requests
[ProviderAdapter] Attempt 2/12: provider=gemini-official, model=pro-official, key=备用Key
[ProviderAdapter] Success on attempt 2/12
```

## 向后兼容性

系统保持与旧代码的兼容:

1. **环境变量**: 仍然支持通过环境变量配置 (在 YAML 中使用 `${VAR}`)
2. **Legacy API**: `/models/legacy` 端点返回扁平列表
3. **MODEL_REGISTRY**: 如果 YAML 配置加载失败,自动回退到 `src/llm/models.py` 中的 `MODEL_REGISTRY`

## 性能优化

- ConfigLoader 使用单例模式,配置只加载一次
- ProviderAdapter 使用 `@lru_cache` 缓存实例
- 前端使用 React Query 缓存模型列表 (5 分钟)

## 安全考虑

- API Key 不在日志中输出 (只显示名称)
- YAML 配置文件应添加到 `.gitignore`
- 提供 `config/llm_providers.yaml.example` 作为模板

## 故障排查

### 配置加载失败

检查:
1. YAML 文件格式是否正确
2. 环境变量是否设置
3. 查看日志中的错误信息

### 所有尝试都失败

检查:
1. 是否有可用的 API Key
2. API Key 是否有效
3. 网络连接是否正常
4. 查看详细的故障转移日志

### 前端模型列表为空

检查:
1. 后端 API 是否正常运行
2. 浏览器控制台是否有错误
3. 是否有至少一个 Provider 启用且有可用的 API Key

## 未来扩展

可能的改进方向:

1. **动态配置重载**: 支持运行时重新加载配置,无需重启服务
2. **模型性能监控**: 记录每个模型的响应时间、成功率等指标
3. **智能路由**: 根据历史性能自动选择最优模型
4. **成本优化**: 根据成本和质量自动选择模型
5. **A/B 测试**: 支持多个模型并行测试,比较效果
