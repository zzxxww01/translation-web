# LLM 模块系统手册

更新时间：2026-04-20

本文档描述当前仓库中 LLM 模块的真实实现，覆盖配置系统、Provider 适配器、故障转移策略、前后端集成和维护方法。

相关阅读：
- [长文翻译技术手册](./长文翻译技术手册.md)
- [系统架构](./系统架构.md)

---

# 一、文档范围与边界

## 1.1 本文覆盖的内容

1. YAML 配置系统的结构、加载机制和验证规则
2. Provider 适配器的接口设计和实现
3. 三级故障转移策略（Key 轮换 → 同组模型切换 → 跨组模型切换）
4. 前端模型选择器的分组显示
5. 模型配置的最佳实践和维护方法

## 1.2 本文不重点展开的内容

1. 具体的翻译 Prompt 设计
2. 各个翻译链路的业务逻辑
3. 术语库和学习链路的实现

这些内容请参阅：
- [长文翻译技术手册](./长文翻译技术手册.md)
- [术语库系统手册](./术语库系统手册.md)

---

# 二、核心概念

## 2.1 设计目标

LLM 模块重构的核心目标：

1. **统一配置管理**：所有 LLM Provider 和模型配置集中在 YAML 文件中
2. **多 Provider 支持**：支持同时配置多个 LLM 服务商（Gemini、中转服务等）
3. **高可用性**：通过主备 API Key 和多级故障转移保证服务稳定性
4. **灵活性**：支持按任务类型指定默认模型，支持运行时动态切换
5. **向后兼容**：保持现有代码的调用方式不变

## 2.2 架构层次

```
┌─────────────────────────────────────────────────────┐
│  业务层 (Translation Agent, Services)                │
│  - 调用 LLMProvider 接口                             │
│  - 不关心具体 Provider 实现                          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  适配器层 (ProviderAdapter)                          │
│  - 统一的 generate_with_fallback() 接口              │
│  - 自动重试和故障转移                                │
│  - 性能优化（LRU 缓存）                              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Provider 层 (GeminiProvider, etc.)                  │
│  - 实现 LLMProvider 接口                             │
│  - 处理具体 API 调用                                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  配置层 (ConfigLoader)                               │
│  - 加载和验证 YAML 配置                              │
│  - 提供配置查询接口                                  │
└─────────────────────────────────────────────────────┘
```

---

# 三、配置系统

## 3.1 配置文件结构

配置文件位置：`config/llm_providers.yaml`

```yaml
providers:
  # Provider ID（唯一标识）
  gemini-official:
    # Provider 基本信息
    name: "Google Gemini Official"
    description: "Official Gemini API"
    priority: 1  # 数字越小优先级越高
    
    # API 配置
    api_keys:
      - key: "${GEMINI_API_KEY}"      # 主 Key（支持环境变量）
        priority: 1
      - key: "${GEMINI_API_KEY_2}"    # 备用 Key
        priority: 2
    
    base_url: "https://generativelanguage.googleapis.com"
    
    # 重试配置
    retry:
      max_attempts: 3
      initial_delay: 1.0
      max_delay: 10.0
      exponential_base: 2.0
    
    # 模型列表
    models:
      - alias: "gemini-flash"              # 模型别名（用于代码中引用）
        real_model: "gemini-flash-latest"  # 实际 API 模型名
        name: "Gemini Flash"               # 显示名称
        description: "Fast and efficient"
        supports_thinking: false
        priority: 1
        available: true
      
      - alias: "gemini-pro"
        real_model: "gemini-2.5-pro"
        name: "Gemini 2.5 Pro"
        description: "Balanced performance"
        supports_thinking: true
        priority: 2
        available: true

  vectorengine-relay:
    name: "VectorEngine Relay"
    description: "Relay service for multiple providers"
    priority: 2
    
    api_keys:
      - key: "${VECTORENGINE_API_KEY}"
        priority: 1
    
    base_url: "https://api.vectorengine.ai/v1"
    
    models:
      - alias: "deepseek-v3"
        real_model: "deepseek-v3.2"
        name: "DeepSeek V3"
        description: "Long context support"
        supports_thinking: true
        priority: 1
        available: true

# 任务默认模型配置
task_defaults:
  longform: "deepseek-v3"        # 长文翻译
  post: "gemini-flash"           # 帖子翻译
  title: "gemini-flash"          # 标题翻译
  metadata: "gemini-flash"       # 元数据提取
  analysis: "gemini-pro"         # 全文分析
```

## 3.2 配置加载机制

### 单例模式

`ConfigLoader` 使用线程安全的单例模式（Double-Check Locking）：

```python
from src.llm.config_loader import ConfigLoader

# 获取单例实例
loader = ConfigLoader.get_instance()

# 查询模型配置
model_config = loader.get_model_config("gemini-pro")
provider_config = loader.get_provider_for_model("gemini-pro")
```

### 环境变量处理

配置文件中的 `${VAR_NAME}` 会自动替换为环境变量值：

- 如果环境变量不存在或为空字符串，该 API Key 会被标记为不可用
- 至少需要一个可用的 API Key，否则 Provider 会被标记为不可用

### 配置验证

加载时会自动验证：

1. 必需字段是否存在（name, api_keys, models 等）
2. 优先级是否为正整数
3. 模型别名是否唯一（跨 Provider）
4. 至少有一个可用的 Provider 和模型

## 3.3 配置查询接口

```python
# 获取所有 Provider 配置
providers = loader.get_all_providers()

# 获取特定模型的配置
model = loader.get_model_config("gemini-pro")
# 返回: ModelConfig(alias, real_model, name, description, ...)

# 获取模型所属的 Provider
provider = loader.get_provider_for_model("gemini-pro")
# 返回: ProviderConfig(id, name, api_keys, models, ...)

# 获取任务默认模型
default_model = loader.get_task_default("longform")
# 返回: "deepseek-v3"

# 获取分组的模型列表（用于前端）
grouped = loader.get_models_grouped()
# 返回: List[Dict] 按 Provider 分组的模型列表
```

---

# 四、Provider 适配器

## 4.1 接口设计

`ProviderAdapter` 提供统一的 LLM 调用接口，封装了重试和故障转移逻辑：

```python
from src.llm.provider_adapter import ProviderAdapter

# 创建适配器实例
adapter = ProviderAdapter(
    provider_id="gemini-official",
    model_alias="gemini-pro"
)

# 生成文本（自动故障转移）
result = adapter.generate_with_fallback(
    prompt="Translate: Hello",
    temperature=0.3,
    max_tokens=1000
)
```

## 4.2 核心方法

### generate_with_fallback()

带故障转移的文本生成：

```python
def generate_with_fallback(
    self,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> str:
    """
    生成文本，失败时自动故障转移
    
    故障转移顺序：
    1. 当前 Provider 的其他 API Key
    2. 当前 Provider 的其他模型（同组）
    3. 其他 Provider 的模型（跨组）
    """
```

### 性能优化

- 使用 `@lru_cache` 缓存 Provider 实例，避免重复创建
- 缓存故障转移计划，减少计算开销

---

# 五、故障转移策略

## 5.1 三级故障转移

当 LLM 调用失败时，系统会按以下顺序尝试：

### Level 1: Key 轮换

在同一个 Provider 的同一个模型上，尝试其他 API Key：

```
gemini-official / gemini-pro / key-1 (失败)
  ↓
gemini-official / gemini-pro / key-2
```

### Level 2: 同组模型切换

在同一个 Provider 内，切换到其他可用模型：

```
gemini-official / gemini-pro (所有 Key 都失败)
  ↓
gemini-official / gemini-flash
```

### Level 3: 跨组故障转移

切换到其他 Provider 的模型：

```
gemini-official / * (所有模型都失败)
  ↓
vectorengine-relay / deepseek-v3
```

## 5.2 故障转移规则

### 同组模型选择

按模型优先级（priority 字段）排序，优先选择高优先级模型。

### 跨组模型选择

1. 按 Provider 优先级排序
2. 在每个 Provider 内，优先选择与原模型"相似"的模型：
   - 如果原模型别名包含 "flash"，优先选择其他 "flash" 模型
   - 如果原模型别名包含 "pro"，优先选择其他 "pro" 模型
   - 否则按模型优先级排序

### 示例

原始请求：`gemini-official / gemini-pro`

完整故障转移计划：

```
1. gemini-official / gemini-pro / key-1
2. gemini-official / gemini-pro / key-2
3. gemini-official / gemini-flash / key-1
4. gemini-official / gemini-flash / key-2
5. vectorengine-relay / deepseek-v3 / key-1  (跨组，选择 pro 类模型)
```

## 5.3 实现入口

故障转移策略由 `FallbackStrategy` 类实现：

```python
from src.llm.fallback_strategy import FallbackStrategy

strategy = FallbackStrategy()
plan = strategy.build_fallback_plan(
    provider_id="gemini-official",
    model_alias="gemini-pro"
)

# plan 是一个列表，每个元素包含：
# - provider_id: str
# - model_alias: str
# - api_key_index: int
```

---

# 六、前后端集成

## 6.1 后端 API

### 获取模型列表（分组）

```
GET /api/models
```

返回格式：

```json
{
  "providers": [
    {
      "id": "gemini-official",
      "name": "Google Gemini Official",
      "description": "Official Gemini API",
      "models": [
        {
          "alias": "gemini-flash",
          "name": "Gemini Flash",
          "description": "Fast and efficient",
          "supports_thinking": false,
          "priority": 1,
          "available": true
        },
        {
          "alias": "gemini-pro",
          "name": "Gemini 2.5 Pro",
          "description": "Balanced performance",
          "supports_thinking": true,
          "priority": 2,
          "available": true
        }
      ]
    },
    {
      "id": "vectorengine-relay",
      "name": "VectorEngine Relay",
      "description": "Relay service",
      "models": [...]
    }
  ]
}
```

### 向后兼容 API

```
GET /api/models/legacy
```

返回扁平的模型列表（向后兼容旧版前端）：

```json
{
  "models": [
    {
      "alias": "gemini-flash",
      "name": "Gemini Flash",
      ...
    },
    ...
  ]
}
```

## 6.2 前端集成

### ModelSelector 组件

位置：`web/frontend/src/components/ModelSelector.tsx`

特性：

1. 使用 HTML `<optgroup>` 实现 Provider 分组
2. 自动禁用不可用的模型
3. 显示 thinking 能力标记（🧠）
4. 支持加载状态和错误处理

使用示例：

```tsx
<ModelSelector
  value={selectedModel}
  onChange={setSelectedModel}
  disabled={isTranslating}
/>
```

### 类型定义

位置：`web/frontend/src/shared/types/index.ts`

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

---

# 七、使用指南

## 7.1 添加新的 Provider

1. 在 `config/llm_providers.yaml` 中添加配置：

```yaml
providers:
  new-provider:
    name: "New Provider"
    description: "Description"
    priority: 3
    api_keys:
      - key: "${NEW_PROVIDER_API_KEY}"
        priority: 1
    base_url: "https://api.newprovider.com"
    models:
      - alias: "new-model"
        real_model: "new-model-v1"
        name: "New Model"
        description: "Description"
        supports_thinking: false
        priority: 1
        available: true
```

2. 在 `.env` 中添加 API Key：

```
NEW_PROVIDER_API_KEY=your-api-key
```

3. 实现 Provider 类（如果需要特殊处理）：

```python
# src/llm/new_provider.py
from src.llm.base import LLMProvider

class NewProvider(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # 实现 API 调用逻辑
        pass
```

4. 在 `src/llm/provider_adapter.py` 中注册：

```python
def _create_provider(self, provider_config: ProviderConfig) -> LLMProvider:
    if provider_config.id == "new-provider":
        return NewProvider(...)
    # ...
```

## 7.2 修改任务默认模型

编辑 `config/llm_providers.yaml` 中的 `task_defaults` 部分：

```yaml
task_defaults:
  longform: "deepseek-v3"     # 长文翻译
  post: "gemini-flash"        # 帖子翻译
  analysis: "gemini-pro"      # 全文分析
```

## 7.3 在代码中使用

### 方式 1: 使用 ProviderAdapter（推荐）

```python
from src.llm.provider_adapter import ProviderAdapter

# 使用任务默认模型
adapter = ProviderAdapter.from_task_default("longform")
result = adapter.generate_with_fallback(prompt="...")

# 指定模型
adapter = ProviderAdapter(
    provider_id="gemini-official",
    model_alias="gemini-pro"
)
result = adapter.generate_with_fallback(prompt="...")
```

### 方式 2: 直接使用 Provider（向后兼容）

```python
from src.llm.gemini import GeminiProvider

# 使用默认模型
provider = GeminiProvider()
result = provider.generate(prompt="...")

# 指定模型
result = provider.generate(prompt="...", model="gemini-pro")
```

---

# 八、维护和调试

## 8.1 配置文件安全

**重要**：`config/llm_providers.yaml` 包含敏感信息，已添加到 `.gitignore`。

- 提供示例配置：`config/llm_providers.yaml.example`
- 生产环境使用环境变量注入 API Key
- 不要在配置文件中硬编码 API Key

## 8.2 日志和监控

配置加载日志：

```python
import logging
logging.basicConfig(level=logging.INFO)

# 会输出：
# INFO: Loaded 2 providers, 5 models
# WARNING: Provider 'xxx' has no available API keys
```

故障转移日志：

```python
# ProviderAdapter 会记录每次故障转移
# INFO: Attempt 1 failed, trying fallback...
# INFO: Switched to provider 'xxx', model 'yyy'
```

## 8.3 常见问题

### 问题 1: 配置加载失败

**症状**：启动时报错 "Failed to load LLM config"

**排查**：
1. 检查 `config/llm_providers.yaml` 是否存在
2. 检查 YAML 语法是否正确
3. 检查必需字段是否缺失

### 问题 2: 所有 API Key 不可用

**症状**：Provider 被标记为不可用

**排查**：
1. 检查环境变量是否设置：`echo $GEMINI_API_KEY`
2. 检查环境变量是否为空字符串
3. 检查 `.env` 文件是否正确加载

### 问题 3: 模型别名冲突

**症状**：配置加载时报错 "Duplicate model alias"

**排查**：
1. 检查是否有多个 Provider 使用了相同的模型别名
2. 修改其中一个别名，确保全局唯一

### 问题 4: 故障转移不生效

**症状**：调用失败后没有自动切换到备用模型

**排查**：
1. 检查是否使用了 `generate_with_fallback()` 方法
2. 检查备用模型是否可用（available: true）
3. 检查日志中的故障转移计划

## 8.4 测试

运行单元测试：

```bash
pytest tests/test_llm_config_system.py -v
```

测试覆盖：
- 配置加载和验证
- 环境变量处理
- 故障转移计划构建
- API 响应格式
- 模型查询接口

---

# 九、最佳实践

## 9.1 模型选择策略

1. **快速任务**（术语预扫描、规则提取）→ Flash 模型
2. **标准任务**（段落翻译、标题翻译）→ Pro 模型
3. **复杂任务**（全文分析、四步法反思）→ Pro 或 Preview 模型
4. **长文本任务**（长文翻译）→ 支持长上下文的模型（如 DeepSeek）

## 9.2 API Key 管理

1. 为每个 Provider 配置至少 2 个 API Key（主备）
2. 使用环境变量管理 API Key，不要硬编码
3. 定期轮换 API Key，提高安全性
4. 监控 API Key 使用量，避免超限

## 9.3 故障转移配置

1. 设置合理的 Provider 优先级（priority）
2. 确保至少有一个备用 Provider
3. 为关键任务配置多个可用模型
4. 定期测试故障转移是否正常工作

## 9.4 性能优化

1. 使用 `ProviderAdapter` 的缓存机制
2. 避免频繁创建 Provider 实例
3. 合理设置重试参数（max_attempts, delay）
4. 监控 API 调用延迟，及时调整配置

---

# 十、迁移指南

## 10.1 从旧版本迁移

如果你的代码使用了旧的硬编码模型配置，需要进行以下迁移：

### 步骤 1: 创建配置文件

复制示例配置并填入你的 API Key：

```bash
cp config/llm_providers.yaml.example config/llm_providers.yaml
```

### 步骤 2: 更新环境变量

在 `.env` 中添加所有需要的 API Key。

### 步骤 3: 更新代码

**旧代码**：

```python
# 硬编码模型
result = llm.generate(prompt="...", model="preview")
```

**新代码**：

```python
# 使用默认模型（推荐）
result = llm.generate(prompt="...")

# 或使用 ProviderAdapter
adapter = ProviderAdapter.from_task_default("longform")
result = adapter.generate_with_fallback(prompt="...")
```

### 步骤 4: 测试

运行测试确保迁移成功：

```bash
pytest tests/test_llm_config_system.py -v
```

## 10.2 向后兼容性

新系统保持了向后兼容：

1. 旧的 `LLMProvider` 接口保持不变
2. 旧的 `generate()` 方法仍然可用
3. 旧的 API 端点（`/api/models/legacy`）仍然可用

建议逐步迁移到新的 `ProviderAdapter` 接口，以获得故障转移等新特性。

---

# 十一、相关文件

## 11.1 核心文件

| 文件 | 说明 |
|---|---|
| `config/llm_providers.yaml` | LLM 配置文件（生产环境） |
| `config/llm_providers.yaml.example` | 配置文件示例 |
| `src/llm/config_loader.py` | 配置加载器 |
| `src/llm/config_models.py` | 配置数据模型 |
| `src/llm/provider_adapter.py` | Provider 适配器 |
| `src/llm/fallback_strategy.py` | 故障转移策略 |
| `src/llm/base.py` | LLMProvider 基类 |
| `src/llm/gemini.py` | Gemini Provider 实现 |

## 11.2 前端文件

| 文件 | 说明 |
|---|---|
| `web/frontend/src/components/ModelSelector.tsx` | 模型选择器组件 |
| `web/frontend/src/shared/types/index.ts` | TypeScript 类型定义 |
| `web/frontend/src/shared/api/models.ts` | 模型 API 客户端 |

## 11.3 测试文件

| 文件 | 说明 |
|---|---|
| `tests/test_llm_config_system.py` | LLM 配置系统单元测试 |

## 11.4 API 路由

| 文件 | 说明 |
|---|---|
| `src/api/routers/models.py` | 模型列表 API 路由 |

---

# 十二、更新历史

| 日期 | 版本 | 变更说明 |
|---|---|---|
| 2026-04-07 | 1.0 | 初始版本，完成 LLM 模块重构 |
| 2026-04-07 | 1.1 | 移除所有硬编码模型，统一使用配置文件默认模型 |
| 2026-04-20 | 1.2 | 修复所有 API 调用缺少 task_type 参数的问题；修复长文翻译 Pydantic 模型序列化问题；更新代理配置为可选模式 |

---

# 附录：配置文件完整示例

参见：`config/llm_providers.yaml.example`
