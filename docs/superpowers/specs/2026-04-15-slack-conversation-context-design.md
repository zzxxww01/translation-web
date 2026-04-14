# Slack 对话上下文支持设计

**日期**: 2026-04-15  
**状态**: 待实现  
**方案**: 前端状态管理 + 后端无状态

## 背景

当前 Slack 回复功能是无状态的，每次调用独立处理单条消息，无法利用对话上下文。典型场景：对方连发多条消息，我回复一条，对方继续回复，我再回复 —— 这种 thread 对话需要完整上下文才能生成连贯的回复。

## 需求

1. **对话历史管理**: 支持逐条添加消息，区分"对方"和"我"
2. **自动加入历史**: 选择/复制回复后自动加入对话历史
3. **会话级保存**: 刷新页面清空，无需持久化
4. **完整上下文**: 所有历史消息原样传给 LLM
5. **双向支持**: 支持我发起对话和对方发起对话两种场景

## 架构方案

### 方案选择：前端状态管理 + 后端无状态

**理由**:
- 符合历史决策（之前删除了 `conversation.py`）
- 会话级保存需求，前端管理最直接
- 无状态后端更容易测试和部署
- 20 条消息约 2KB，网络开销可忽略

**替代方案**:
- 后端内存会话管理：需要会话清理机制，增加复杂度
- 混合方案：过度设计，当前需求不需要

## 数据模型

### 前端数据结构

```typescript
type MessageRole = 'them' | 'me';

interface ConversationMessage {
  id: string;           // UUID，用于 React key
  role: MessageRole;    // 'them' 或 'me'
  content: string;      // 消息内容
  timestamp: number;    // 时间戳
}

interface SlackWorkspaceStore {
  // 现有字段保持不变
  incomingText: string;
  incomingTranslation: string;
  incomingSuggestions: SlackReplyVariant[];
  draftText: string;
  draftVersions: SlackReplyVariant[];
  
  // 新增：对话历史
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  
  // 新增方法
  addMessage: (role: MessageRole, content: string) => void;
  addMessages: (role: MessageRole, contents: string[]) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;
}
```

### 后端数据结构

```python
# slack_models.py 扩展
class ConversationMessage(BaseModel):
    role: Literal["them", "me"]
    content: str

class SlackProcessRequest(BaseModel):
    message: str
    custom_prompt: Optional[str] = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)

class SlackComposeRequest(BaseModel):
    content: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
```

## UI 设计

### 界面布局

```
┌─────────────────────────────────────────┐
│ 对话历史区（可折叠，默认展开）            │
│ ┌─────────────────────────────────────┐ │
│ │ [我]   消息1                    [×]  │ │
│ │ [对方] 消息2                    [×]  │ │
│ │ [我]   回复1                    [×]  │ │
│ └─────────────────────────────────────┘ │
│ [清空对话]                               │
├─────────────────────────────────────────┤
│ 左栏：对方的话                           │
│ - 输入框（支持多行，可粘贴多条消息）      │
│ - [英译中 + 建议回复] 按钮               │
├─────────────────────────────────────────┤
│ 右栏：我想说的话                         │
│ - 输入框（我的中文草稿）                 │
│ - [生成英文版本] 按钮 → A/B/C           │
└─────────────────────────────────────────┘
```

### 交互流程

**场景 1：我发起对话**
1. 右栏输入中文草稿
2. 点击"生成英文版本" → 基于对话历史生成 A/B/C
3. 选择版本并复制 → 自动加入历史（role='me'），清空右栏输入框
4. 对方回复后，左栏粘贴对方消息
5. 点击"英译中 + 建议回复" → 对方消息加入历史（role='them'），显示翻译和建议

**场景 2：对方发起对话**
1. 左栏粘贴对方消息（可以一次粘贴多条，用换行分隔）
2. 点击"英译中 + 建议回复" → 自动拆分并加入历史（role='them'），显示翻译和建议
3. 选择建议回复或右栏自己写 → 加入历史（role='me'）

**场景 3：对方连发多条**
1. 左栏一次性粘贴多行消息
2. 点击"英译中 + 建议回复"
3. 系统自动拆分成多条 `role='them'` 消息加入历史
4. 基于完整上下文生成翻译和建议回复

**历史管理**:
- 每条消息右侧有 [×] 删除按钮
- 点击消息内容可以 inline 编辑
- "清空对话"清空所有历史
- 折叠后显示："对话历史 (5 条消息) [展开]"

**自动行为**:
- 选择任何回复版本后，自动加入历史 + 清空对应输入框
- Toast 提示："已复制并加入对话历史"

## Prompt 改造

### 历史格式化

```python
def format_conversation_history(messages: list[ConversationMessage]) -> str:
    """格式化对话历史为 prompt 文本"""
    if not messages:
        return ""
    
    lines = ["## Conversation history"]
    for msg in messages:
        role_label = "Me" if msg.role == "me" else "Them"
        lines.append(f"[{role_label}]: {msg.content}")
    lines.append("")  # 空行分隔
    return "\n".join(lines)
```

### slack_process.txt 改造

在现有 prompt 中插入历史部分：

```
You are an expat employee at a top tech or hardware company.
You help the user handle internal workplace chat messages in tools like Slack, Teams, and Discord.

{context_section}

{conversation_history_section}

## Incoming message
{message}

## Style rules for suggested replies
[保持原有规则不变...]

## Task
1. Translate the incoming message into clear, natural Chinese.
2. **Consider the conversation history above when suggesting replies** - your replies should naturally continue the conversation thread.
3. Suggest 3 English replies that directly answer the message.
[其余规则保持不变...]
```

### slack_compose.txt 改造

```
You are an expat employee at a top tech or hardware company.
You help the user turn Chinese drafts into short English replies for internal workplace chat tools like Slack, Teams, and Discord.

{context_section}

{conversation_history_section}

## Chinese draft
{content}

## Core style
[保持原有规则不变...]

## Task
**Consider the conversation history above** - your English versions should naturally continue the conversation thread and maintain consistency with previous messages.

Provide exactly 3 English versions every time:
[其余规则保持不变...]
```

## 实现细节

### 后端实现

**文件**: `src/api/routers/slack_process.py`, `slack_compose.py`

```python
# 在 process_slack_message 中
conversation_history_section = format_conversation_history(request.conversation_history)
prompt = prompt_manager.get(
    "slack_process",
    context_section="",
    conversation_history_section=conversation_history_section,
    message=message,
)
```

### 前端实现

**文件**: `web/frontend/src/features/slack/store.ts`

扩展 Zustand store，添加对话历史管理方法。

**文件**: `web/frontend/src/features/slack/api.ts`

```typescript
export const slackApi = {
  processMessage: (data: ProcessMessageDto & { conversation_history?: ConversationMessage[] }) =>
    apiClient.post<ProcessResult>('/slack/process', data),

  composeReply: (data: ComposeDto & { conversation_history?: ConversationMessage[] }) =>
    apiClient.post<ComposeResult>('/slack/compose', data),
};
```

**文件**: `web/frontend/src/features/slack/index.tsx`

核心交互逻辑：

```typescript
const handleAnalyze = async () => {
  const content = incomingText.trim();
  if (!content || analyzeMutation.isPending) return;
  
  // 拆分多行消息
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  
  try {
    const result = await analyzeMutation.mutateAsync({ 
      message: lines[lines.length - 1], // 最后一条作为当前消息
      conversation_history: conversationMessages 
    });
    
    // 添加所有消息到历史
    addMessages('them', lines);
    
    setIncomingResult(result.translation, result.suggested_replies ?? []);
    setIncomingText(''); // 清空输入框
  } catch { /* handled */ }
};

const handleSelectReply = async (englishReply: string) => {
  await copyToClipboard(englishReply);
  addMessage('me', englishReply); // 自动加入历史
  toast.success('已复制并加入对话历史');
  clearIncoming(); // 清空翻译和建议
};
```

**新建组件**: `web/frontend/src/features/slack/components/ConversationHistory.tsx`

显示消息列表，支持编辑、删除、折叠/展开。

## 错误处理与边界情况

### 1. 空历史处理
- `conversation_history` 为空时，`conversation_history_section` 返回空字符串
- Prompt 正常工作，就像现在的无状态模式

### 2. 历史过长处理
- 前端不做限制，依赖 LLM 的 context window（Gemini 支持 1M+ tokens）
- 如果超限，LLM 返回错误，前端 toast 提示："对话历史过长，请清空部分消息"

### 3. 消息拆分逻辑
- 左栏输入框支持多行，按 `\n` 拆分
- 空行自动过滤（`filter(Boolean)`）
- 单行消息直接作为一条，多行消息拆分成多条

### 4. 自动加入历史的时机
- **对方消息**: 点击"英译中 + 建议回复"时立即加入
- **我的回复**: 选择建议回复或生成版本并复制时加入
- 如果用户复制后没有实际发送，历史会不准确 → 可以手动删除

### 5. 编辑历史消息
- 点击消息内容进入编辑模式（contentEditable 或 inline input）
- 保存后更新 store 中的消息内容
- 不会重新调用 LLM，只是修正历史记录

### 6. 清空操作
- "清空对话"按钮清空 `conversationMessages`
- "清空"按钮（左右栏）只清空当前输入框和结果，不影响历史
- 刷新页面自动清空所有状态（会话级）

### 7. Toast 提示
- 复制成功："已复制并加入对话历史"
- 删除消息："已从对话历史中移除"
- 清空对话："对话历史已清空"
- LLM 错误："生成失败，请重试"

### 8. 兼容性
- 后端 `conversation_history` 参数默认为空列表，向后兼容
- 旧版前端不传该参数，后端正常工作（无状态模式）

## 数据流总结

1. 用户在左栏/右栏输入内容
2. 点击按钮 → 前端将 `conversationMessages` + 新消息发送到后端
3. 后端格式化历史 → 插入 prompt → 调用 LLM
4. 返回结果 → 前端显示
5. 用户选择回复 → 自动加入历史 → 下次调用时带上

## 关键特性

- ✅ 支持我发起/对方发起两种场景
- ✅ 支持批量粘贴多条消息
- ✅ 自动加入历史，无需手动操作
- ✅ 会话级保存，刷新清空
- ✅ 完整上下文传递给 LLM
- ✅ 后端无状态，易于部署
- ✅ 向后兼容现有功能

## 实现顺序

1. 后端：扩展数据模型（`ConversationMessage`）
2. 后端：实现历史格式化函数
3. 后端：修改 `slack_process.py` 和 `slack_compose.py`
4. 后端：更新 prompt 模板
5. 前端：扩展 Zustand store
6. 前端：创建 `ConversationHistory` 组件
7. 前端：修改 `index.tsx` 主界面布局
8. 前端：实现核心交互逻辑
9. 测试：验证各种场景
10. 文档：更新用户手册
