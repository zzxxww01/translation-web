# Slack & 微信模块安全审查报告（内部使用版）

**审查时间**: 2026-04-21  
**使用场景**: 🔒 **内部小团队使用（5-20人）**  
**网络环境**: 公网部署，但仅团队成员访问

---

## 🎯 场景调整说明

根据实际使用场景，调整修复策略：

### ✅ 保留的功能
- **custom_prompt**: 保留，团队成员需要灵活性
- **速率限制**: 设置为非常宽松（1000/minute）或不设置

### ⚠️ 仍需修复的问题
- **线程池竞态条件**: 即使内部使用，数据混乱也会影响工作
- **类型验证**: 防止意外错误，提升稳定性
- **错误处理**: 更好的调试体验

---

## 📊 调整后的问题优先级

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| 🔴 必须修复 | 2 个 | 影响数据正确性和稳定性 |
| 🟡 建议修复 | 3 个 | 提升用户体验 |
| 🟢 可忽略 | 4 个 | 内部使用无影响 |

---

## 🔴 必须修复（影响功能正确性）

### 1. 线程池竞态条件 - 微信格式化模块 ⚠️

**文件**: `src/services/wechat_formatter.py:129-131`

**问题**: 多人同时使用微信格式化时，图片可能保存到错误的项目目录

**场景示例**:
```
14:00:00 - 张三格式化文章A（project_a）
14:00:01 - 李四格式化文章B（project_b）
14:00:02 - 张三的图片被错误保存到 project_b 目录 ❌
```

**影响**: 
- 图片丢失或混乱
- 需要手动整理文件

**修复方案**（推荐方案 1）:

```python
# 方案 1: 实例级线程池（简单可靠）
class WechatFormatter:
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self._image_executor = ThreadPoolExecutor(max_workers=4)  # 每个实例独立
    
    def __del__(self):
        if hasattr(self, '_image_executor'):
            self._image_executor.shutdown(wait=False)

# 方案 2: 传递 project_id 参数（更彻底）
def _upload_to_local(self, image_url: str, project_id: str):  # 显式传参
    # 不依赖 self.project_id
    save_path = self._get_save_path(project_id, ...)
```

**工作量**: 15 分钟

---

### 2. 类型验证不足 - Slack Refine 模块

**文件**: `src/api/routers/slack_models.py:53`

**问题**: `conversation_history` 使用宽松类型，可能导致运行时错误

**当前代码**:
```python
class SlackRefineRequest(BaseModel):
    conversation_history: list[dict[str, str]] = []  # 任意 dict
```

**风险场景**:
```python
# 前端传错了数据
{
  "conversation_history": [
    {"foo": "bar"}  # 缺少 role 和 content
  ]
}

# 后端代码崩溃
role = msg.get("role")  # None
content = msg.get("content")  # None
# 下游逻辑出错
```

**修复方案**:
```python
from typing import List
from pydantic import BaseModel, Field

class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)

class SlackRefineRequest(BaseModel):
    conversation_history: List[ConversationMessage] = []
    
    @field_validator('conversation_history')
    @classmethod
    def validate_history(cls, v: List[ConversationMessage]) -> List[ConversationMessage]:
        if len(v) > 50:  # 内部使用，放宽到 50 条
            raise ValueError("Conversation history too long (max 50 messages)")
        return v
```

**好处**:
- 前端传错数据时立即返回清晰的错误信息
- 避免运行时崩溃
- 更好的 API 文档（自动生成的 OpenAPI schema 更准确）

**工作量**: 10 分钟

---

## 🟡 建议修复（提升体验）

### 3. 错误处理改进 - Slack Refine 模块

**文件**: `src/api/routers/slack_refine.py:50-51`

**当前代码**:
```python
except Exception as e:
    logger.error(f"Error refining result: {e}", exc_info=True)
    raise  # 前端收到完整堆栈信息
```

**问题**: 前端收到的错误信息太技术化，不友好

**修复方案**:
```python
from ..utils.llm_errors import raise_llm_service_unavailable

try:
    # ... LLM 调用
except Exception as e:
    logger.error(f"Error refining result: {e}", exc_info=True)
    # 返回友好的错误信息
    raise_llm_service_unavailable(operation="Slack refine", exc=e)
```

**效果对比**:
```json
// 修复前
{
  "detail": "Traceback (most recent call last):\n  File \"/app/src/llm/gemini.py\", line 123...",
  "error": "ConnectionError: Failed to connect to generativelanguage.googleapis.com"
}

// 修复后
{
  "detail": "Slack refine service temporarily unavailable. Please try again later.",
  "error_code": "LLM_SERVICE_UNAVAILABLE"
}
```

**工作量**: 5 分钟

---

### 4. 输入长度限制 - Slack 模块

**文件**: `src/api/routers/slack_models.py`

**问题**: 无长度限制，超大输入可能导致超时

**修复方案**（放宽限制）:
```python
MAX_SLACK_MESSAGE_LENGTH = 50000  # 50K 字符（内部使用，放宽）
MAX_CUSTOM_PROMPT_LENGTH = 10000  # 10K 字符

class SlackProcessRequest(BaseModel):
    message: str = Field(..., max_length=MAX_SLACK_MESSAGE_LENGTH)
    custom_prompt: Optional[str] = Field(None, max_length=MAX_CUSTOM_PROMPT_LENGTH)
```

**好处**: 防止意外粘贴超大文本导致服务卡死

**工作量**: 5 分钟

---

### 5. 路径防护增强 - 微信格式化模块

**文件**: `src/services/wechat_formatter.py:328-336`

**当前代码**:
```python
def _sanitize_project_id(self, project_id: str) -> str:
    return re.sub(r'[^\w\-]', '_', project_id)
```

**问题**: 清理后可能变成空字符串或全下划线

**修复方案**:
```python
def _sanitize_project_id(self, project_id: str) -> str:
    if not project_id:
        return "default_project"
    
    sanitized = re.sub(r'[^\w\-]', '_', project_id)
    
    # 验证清理后的值
    if not sanitized.strip('_'):
        return "default_project"
    
    if len(sanitized) > 200:  # 内部使用，放宽到 200
        sanitized = sanitized[:200]
    
    return sanitized
```

**工作量**: 5 分钟

---

## 🟢 可忽略（内部使用无影响）

### ~~6. Prompt 注入漏洞~~
- **原因**: 内部使用，团队成员可信任
- **保留**: custom_prompt 功能完全保留

### ~~7. 速率限制~~
- **原因**: 内部使用，不会恶意攻击
- **建议**: 设置为 1000/minute（防止前端代码 bug 导致死循环）

### ~~8. 微信主题扫描~~
- **原因**: 内部使用，调用频率低
- **无需修复**

---

## 🔧 调整后的修复方案

### 必须修复（30 分钟）
1. ✅ 线程池竞态条件（15 分钟）
2. ✅ 类型验证（10 分钟）
3. ✅ 错误处理（5 分钟）

### 建议修复（10 分钟）
4. ⏳ 输入长度限制（5 分钟）
5. ⏳ 路径防护增强（5 分钟）

### 可选：添加宽松速率限制（5 分钟）
```python
# 防止前端代码 bug 导致死循环
@limiter.limit("1000/minute")  # 非常宽松
async def process_slack_message(request: Request, body: SlackProcessRequest):
    ...
```

**总工作量**: 40-45 分钟

---

## 📋 修复后验证清单

### 功能测试
- [ ] 多人同时使用微信格式化，图片保存正确
- [ ] Slack refine 传入错误数据时返回清晰错误
- [ ] custom_prompt 功能正常工作

### 稳定性测试
- [ ] 2 人同时格式化不同文章，无数据混乱
- [ ] 超长输入被正确拒绝（返回 422 错误）
- [ ] LLM 调用失败时返回友好错误信息

---

## 🎯 推荐行动

### 最小修复（30 分钟）
```
1. 修复线程池竞态（15 分钟）
2. 修复类型验证（10 分钟）
3. 改进错误处理（5 分钟）
```

### 完整修复（45 分钟）
```
1-3. 最小修复（30 分钟）
4. 添加输入长度限制（5 分钟）
5. 增强路径防护（5 分钟）
6. 添加宽松速率限制（5 分钟）
```

---

## 📊 内部使用 vs 公网开放对比

| 安全措施 | 公网开放 | 内部使用（你的场景） |
|---------|---------|---------------------|
| custom_prompt | ❌ 必须禁用 | ✅ 保留 |
| 速率限制 | ✅ 严格（10-20/min） | ⏳ 宽松（1000/min）或不设置 |
| Prompt 注入防护 | ✅ 必须 | ⏳ 可选 |
| 线程池竞态 | ✅ 必须修复 | ✅ 必须修复 |
| 类型验证 | ✅ 必须 | ✅ 建议 |
| 输入长度限制 | ✅ 严格（5K） | ⏳ 宽松（50K） |

---

## 总结

**调整后的修复重点**:
1. ✅ 修复会导致数据错误的 bug（线程池竞态）
2. ✅ 提升稳定性（类型验证、错误处理）
3. ⏳ 保留灵活性（custom_prompt、宽松限制）

**预计时间**: 30-45 分钟

**修复后状态**: ✅ 适合内部团队使用，稳定可靠
