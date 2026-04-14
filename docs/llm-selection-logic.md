# LLM 选型逻辑说明

## 架构概览

系统采用**多层抽象 + 模型注册表**的设计，支持灵活的模型选择和路由。

```
用户请求 → API 路由 → LLM Factory → Provider → 实际 API 调用
              ↓
         模型注册表
```

## 核心组件

### 1. 模型注册表 (`src/llm/models.py`)

定义所有可用的模型别名及其配置：

```python
MODEL_REGISTRY = {
    # Gemini 官方 API
    "flash-official": {
        "provider": "gemini",
        "real_model": "gemini-flash-latest",
        "description": "Gemini Flash 官方 API - 快速低成本",
        "supports_thinking": False,
    },
    "pro-official": {
        "provider": "gemini",
        "real_model": "gemini-3-pro-preview",
        "description": "Gemini Pro 官方 API - 平衡质量与成本",
        "supports_thinking": True,
    },
    
    # VectorEngine 中转 API
    "deepseek-relay": {
        "provider": "vectorengine",
        "real_model": "deepseek-v3.2",
        "description": "DeepSeek v3.2 中转 - 高性价比推理模型",
        "supports_thinking": True,
    },
    "gpt4-relay": {
        "provider": "vectorengine",
        "real_model": "gpt-4o",
        "description": "GPT-4o 中转 - OpenAI 旗舰模型",
        "supports_thinking": False,
    },
    "claude-relay": {
        "provider": "vectorengine",
        "real_model": "claude-sonnet-4-20250514",
        "description": "Claude Sonnet 4 中转 - Anthropic 高质量模型",
        "supports_thinking": False,
    },
}
```

**命名规范**：
- 官方 API：`{model}-official`（如 `flash-official`）
- 中转 API：`{model}-relay`（如 `deepseek-relay`）

### 2. Provider 工厂 (`src/llm/factory.py`)

负责创建和路由 LLM Provider 实例。

#### 核心函数

##### `create_llm_provider(provider, model, **kwargs)`

创建 LLM Provider 实例，支持两种输入方式：

1. **模型别名**（推荐）：
   ```python
   provider = create_llm_provider("deepseek-relay")
   # 自动解析：provider=vectorengine, model=deepseek-v3.2
   ```

2. **直接指定 provider + model**：
   ```python
   provider = create_llm_provider("vectorengine", model="deepseek-v3.2")
   ```

**解析逻辑**：
```python
if provider in MODEL_REGISTRY:
    # 1. 尝试作为模型别名解析
    resolved_provider = get_model_provider(provider)  # 获取 provider 名称
    resolved_model = get_real_model_name(provider)    # 获取真实模型名
else:
    # 2. 作为 provider 名称直接使用
    resolved_provider = provider
    resolved_model = model
```

##### `get_llm_provider_for_task(task_type)`

根据任务类型自动选择模型：

```python
task_model_map = {
    "longform": settings.llm_model_longform,    # 默认: deepseek-relay
    "post": settings.llm_model_post,            # 默认: flash-official
    "analysis": settings.llm_model_analysis,    # 默认: pro-official
    "title": settings.llm_model_title,          # 默认: flash-official
    "metadata": settings.llm_model_metadata,    # 默认: flash-official
}
```

### 3. Provider 实现

#### Gemini Provider (`src/llm/gemini.py`)
- 使用 Google Generative AI SDK
- 支持 thinking mode（pro/preview 模型）
- 模型：`gemini-flash-latest`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`

#### VectorEngine Provider (`src/llm/vectorengine.py`)
- 使用 OpenAI SDK（兼容接口）
- Base URL: `https://api.vectorengine.ai/v1`
- 支持多个模型：`deepseek-v3.2`, `gpt-4o`, `claude-sonnet-4-20250514`

### 4. 配置系统 (`src/config.py`)

```python
class Settings(BaseSettings):
    # 默认模型（未指定任务类型时使用）
    llm_default_model: str = "pro-official"
    
    # 任务类型默认模型
    llm_model_longform: str = "deepseek-relay"   # 长文翻译
    llm_model_post: str = "flash-official"       # 帖子翻译
    llm_model_analysis: str = "pro-official"     # 文本分析
    llm_model_title: str = "flash-official"      # 标题翻译
    llm_model_metadata: str = "flash-official"   # 元数据翻译
    
    # Provider 配置
    gemini_api_key: str
    vectorengine_api_key: str
    vectorengine_base_url: str = "https://api.vectorengine.ai/v1"
```

## 模型选择流程

### 场景 1：用户在前端选择模型

```
用户选择 "deepseek-relay"
    ↓
前端发送请求: { model: "deepseek-relay" }
    ↓
后端 API: create_llm_provider("deepseek-relay")
    ↓
解析: provider=vectorengine, real_model=deepseek-v3.2
    ↓
创建 VectorEngineProvider(model="deepseek-v3.2")
    ↓
调用 API: https://api.vectorengine.ai/v1/chat/completions
```

### 场景 2：任务类型自动路由

```
长文翻译任务
    ↓
get_llm_provider_for_task("longform")
    ↓
读取配置: llm_model_longform = "deepseek-relay"
    ↓
create_llm_provider("deepseek-relay")
    ↓
创建 VectorEngineProvider(model="deepseek-v3.2")
```

### 场景 3：使用默认模型

```
未指定模型的请求
    ↓
create_llm_provider()  # provider=None
    ↓
使用默认: llm_default_model = "pro-official"
    ↓
创建 GeminiProvider(model="gemini-3-pro-preview")
```

## API 端点

### 获取可用模型列表

```http
GET /api/models
```

**响应**：
```json
{
  "models": [
    {
      "alias": "flash-official",
      "provider": "gemini",
      "real_model": "gemini-flash-latest",
      "description": "Gemini Flash 官方 API - 快速低成本",
      "supports_thinking": false
    },
    {
      "alias": "deepseek-relay",
      "provider": "vectorengine",
      "real_model": "deepseek-v3.2",
      "description": "DeepSeek v3.2 中转 - 高性价比推理模型",
      "supports_thinking": true
    }
  ]
}
```

### 翻译请求（带模型选择）

```http
POST /api/posts/translate
Content-Type: application/json

{
  "content": "Hello world",
  "preserve_tone": true,
  "model": "deepseek-relay"  // 可选，不指定则使用任务默认模型
}
```

```http
POST /api/projects/{project_id}/translate-stream
Content-Type: application/json

{
  "model": "gpt4-relay"  // 可选
}
```

## 优先级规则

模型选择的优先级（从高到低）：

1. **用户显式指定**：API 请求中的 `model` 参数
2. **任务类型默认**：`llm_model_{task_type}` 配置
3. **全局默认**：`llm_default_model` 配置
4. **硬编码默认**：`pro-official`

## 扩展新模型

### 1. 添加到模型注册表

```python
# src/llm/models.py
MODEL_REGISTRY["new-model-relay"] = {
    "provider": "vectorengine",  # 或新的 provider
    "real_model": "actual-model-name",
    "description": "模型描述",
    "supports_thinking": False,
}
```

### 2. 添加新 Provider（如需要）

```python
# src/llm/new_provider.py
from .base import LLMProvider

class NewProvider(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # 实现生成逻辑
        pass

def create_new_provider(**kwargs) -> NewProvider:
    return NewProvider(**kwargs)

# src/llm/factory.py
from .new_provider import create_new_provider

_PROVIDER_FACTORIES["new_provider"] = create_new_provider
```

### 3. 更新配置（可选）

```python
# .env
NEW_PROVIDER_API_KEY=your-key
LLM_MODEL_LONGFORM=new-model-relay  # 设为某任务的默认模型
```

## 前端集成

### ModelSelector 组件

```tsx
import { ModelSelector } from '@/components/ModelSelector';

function MyComponent() {
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  
  return (
    <ModelSelector
      value={selectedModel}
      onChange={setSelectedModel}
      className="w-full"
    />
  );
}
```

### API 调用

```typescript
// 帖子翻译
const result = await translateMutation.mutateAsync({
  content: text,
  preserve_tone: true,
  model: selectedModel || undefined,
});

// 长文翻译
await fullTranslationService.startTranslation(
  projectId,
  onProgress,
  onComplete,
  method,
  selectedModel || undefined
);
```

## 日志和调试

系统会记录模型选择过程：

```
[LLM Factory] task=longform → model_alias=deepseek-relay
[LLM Factory] creating provider=vectorengine (from input=deepseek-relay, model=deepseek-v3.2)
```

查看日志：
```bash
# 查看 API 日志
tail -f logs/api.log | grep "LLM Factory"
```

## 最佳实践

1. **使用模型别名**：优先使用 `deepseek-relay` 而非直接指定 provider
2. **任务类型配置**：为不同任务配置合适的默认模型
3. **成本优化**：简单任务用 `flash-official`，复杂任务用 `deepseek-relay` 或 `pro-official`
4. **用户选择**：在前端提供模型选择器，让用户根据需求选择
5. **监控使用**：记录各模型的使用频率和成本

## 故障排查

### 问题：模型别名无法识别

**检查**：
1. 确认别名在 `MODEL_REGISTRY` 中定义
2. 检查拼写是否正确（区分大小写）

### 问题：Provider 创建失败

**检查**：
1. API Key 是否正确配置
2. 网络连接是否正常
3. Provider 是否已注册到 `_PROVIDER_FACTORIES`

### 问题：模型返回错误

**检查**：
1. 真实模型名称是否正确
2. API Key 是否有权限访问该模型
3. 请求参数是否符合模型要求

## 总结

系统的 LLM 选型逻辑具有以下特点：

- **灵活性**：支持多种模型和 Provider
- **可扩展性**：易于添加新模型和 Provider
- **配置驱动**：通过环境变量控制默认行为
- **用户友好**：前端提供直观的模型选择界面
- **向后兼容**：保持旧代码的兼容性

通过模型注册表和工厂模式，系统实现了模型选择的集中管理和灵活路由。
