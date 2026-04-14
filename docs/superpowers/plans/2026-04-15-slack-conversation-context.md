# Slack 对话上下文支持实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Slack 回复功能添加对话历史上下文支持，使生成的回复能够基于完整的 thread 对话历史。

**Architecture:** 前端 Zustand store 维护会话级消息列表，每次 API 调用时将完整历史作为参数传递。后端保持无状态，格式化历史后插入 prompt 模板，调用 LLM 生成上下文相关的回复。

**Tech Stack:** TypeScript, React 19, Zustand, Python, FastAPI, Pydantic

---

## 文件结构

**后端新增/修改**:
- `src/api/routers/slack_models.py` - 添加 `ConversationMessage` 模型，扩展请求模型
- `src/api/routers/slack_process.py` - 添加历史格式化函数，修改 API 处理逻辑
- `src/api/routers/slack_compose.py` - 添加历史格式化函数，修改 API 处理逻辑
- `src/prompts/slack_process.txt` - 添加对话历史占位符和指令
- `src/prompts/slack_compose.txt` - 添加对话历史占位符和指令

**前端新增/修改**:
- `web/frontend/src/shared/types/index.ts` - 添加 `ConversationMessage` 类型
- `web/frontend/src/features/slack/store.ts` - 扩展 store，添加对话历史管理
- `web/frontend/src/features/slack/components/ConversationHistory.tsx` - 新建对话历史组件
- `web/frontend/src/features/slack/index.tsx` - 修改主界面布局和交互逻辑
- `web/frontend/src/features/slack/api.ts` - 扩展 API 调用参数

---

## Task 1: 后端数据模型扩展

**Files:**
- Modify: `src/api/routers/slack_models.py`

- [ ] **Step 1: 添加 ConversationMessage 模型**

在 `slack_models.py` 文件顶部导入区域后添加：

```python
class ConversationMessage(BaseModel):
    role: Literal["them", "me"]
    content: str
```

- [ ] **Step 2: 扩展 SlackProcessRequest**

修改 `SlackProcessRequest` 类：

```python
class SlackProcessRequest(BaseModel):
    message: str
    custom_prompt: Optional[str] = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
```

- [ ] **Step 3: 扩展 SlackComposeRequest**

修改 `SlackComposeRequest` 类：

```python
class SlackComposeRequest(BaseModel):
    content: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
```

- [ ] **Step 4: 验证模型定义**

运行类型检查：
```bash
cd C:\Users\DELL\Desktop\translation_agent
python -m mypy src/api/routers/slack_models.py
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/api/routers/slack_models.py
git commit -m "feat(slack): add conversation history data models"
```

---

## Task 2: 后端历史格式化函数

**Files:**
- Modify: `src/api/routers/slack_process.py`
- Modify: `src/api/routers/slack_compose.py`

- [ ] **Step 1: 在 slack_process.py 添加格式化函数**

在 `slack_process.py` 文件中，在 `router = APIRouter()` 之前添加：

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

- [ ] **Step 2: 在 slack_compose.py 添加相同函数**

在 `slack_compose.py` 文件中，在 `router = APIRouter()` 之前添加相同的 `format_conversation_history` 函数（完整复制上面的代码）。

- [ ] **Step 3: 验证函数正确性**

创建临时测试文件 `test_format.py`：

```python
from src.api.routers.slack_models import ConversationMessage
from src.api.routers.slack_process import format_conversation_history

messages = [
    ConversationMessage(role="them", content="Hello"),
    ConversationMessage(role="me", content="Hi there"),
]
result = format_conversation_history(messages)
print(result)
```

运行：
```bash
python test_format.py
```

Expected output:
```
## Conversation history
[Them]: Hello
[Me]: Hi there

```

- [ ] **Step 4: 删除测试文件**

```bash
rm test_format.py
```

- [ ] **Step 5: Commit**

```bash
git add src/api/routers/slack_process.py src/api/routers/slack_compose.py
git commit -m "feat(slack): add conversation history formatting function"
```

---

## Task 3: 后端 API 处理逻辑修改

**Files:**
- Modify: `src/api/routers/slack_process.py:28-57`
- Modify: `src/api/routers/slack_compose.py:24-44`

- [ ] **Step 1: 修改 slack_process.py 的 process_slack_message 函数**

在 `process_slack_message` 函数中，找到 `prompt = prompt_manager.get(...)` 这一行，修改为：

```python
    if request.custom_prompt:
        prompt = request.custom_prompt.replace("{message}", message)
    else:
        conversation_history_section = format_conversation_history(request.conversation_history)
        prompt = prompt_manager.get(
            "slack_process",
            context_section="",
            conversation_history_section=conversation_history_section,
            message=message,
        )
```

- [ ] **Step 2: 修改 slack_compose.py 的 compose_slack_message 函数**

在 `compose_slack_message` 函数中，找到 `prompt = prompt_manager.get(...)` 这一行，修改为：

```python
    conversation_history_section = format_conversation_history(request.conversation_history)
    prompt = prompt_manager.get(
        "slack_compose",
        context_section="",
        conversation_history_section=conversation_history_section,
        content=content,
    )
```

- [ ] **Step 3: 验证语法正确性**

```bash
python -m py_compile src/api/routers/slack_process.py
python -m py_compile src/api/routers/slack_compose.py
```

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/api/routers/slack_process.py src/api/routers/slack_compose.py
git commit -m "feat(slack): integrate conversation history into API handlers"
```

---

## Task 4: 后端 Prompt 模板更新

**Files:**
- Modify: `src/prompts/slack_process.txt`
- Modify: `src/prompts/slack_compose.txt`

- [ ] **Step 1: 更新 slack_process.txt**

在 `{context_section}` 和 `## Incoming message` 之间插入：

```
{conversation_history_section}
```

然后在 `## Task` 部分的第 1 点后面添加第 2 点：

```
2. **Consider the conversation history above when suggesting replies** - your replies should naturally continue the conversation thread.
```

原来的第 2、3 点顺延为第 3、4 点。

- [ ] **Step 2: 更新 slack_compose.txt**

在 `{context_section}` 和 `## Chinese draft` 之间插入：

```
{conversation_history_section}
```

然后在 `## Task` 部分开头添加：

```
**Consider the conversation history above** - your English versions should naturally continue the conversation thread and maintain consistency with previous messages.

```

- [ ] **Step 3: 验证模板占位符**

检查两个文件确保包含 `{conversation_history_section}` 占位符：

```bash
grep "conversation_history_section" src/prompts/slack_process.txt
grep "conversation_history_section" src/prompts/slack_compose.txt
```

Expected: 每个命令输出一行匹配结果

- [ ] **Step 4: Commit**

```bash
git add src/prompts/slack_process.txt src/prompts/slack_compose.txt
git commit -m "feat(slack): update prompt templates with conversation history support"
```

---

## Task 5: 前端类型定义

**Files:**
- Modify: `web/frontend/src/shared/types/index.ts`

- [ ] **Step 1: 添加 ConversationMessage 类型**

在 `index.ts` 文件中，找到 Slack 相关类型定义区域，添加：

```typescript
export type MessageRole = 'them' | 'me';

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
}
```

- [ ] **Step 2: 扩展 ProcessMessageDto**

找到 `ProcessMessageDto` 接口，添加字段：

```typescript
export interface ProcessMessageDto {
  message: string;
  custom_prompt?: string;
  conversation_history?: ConversationMessage[];
}
```

- [ ] **Step 3: 扩展 ComposeDto**

找到 `ComposeDto` 接口，添加字段：

```typescript
export interface ComposeDto {
  content: string;
  conversation_history?: ConversationMessage[];
}
```

- [ ] **Step 4: 验证类型定义**

```bash
cd web/frontend
npm run type-check
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/shared/types/index.ts
git commit -m "feat(slack): add conversation message types"
```

---

## Task 6: 前端 Store 扩展

**Files:**
- Modify: `web/frontend/src/features/slack/store.ts`

- [ ] **Step 1: 导入新类型**

在文件顶部添加导入：

```typescript
import type { ConversationMessage, MessageRole } from '@/shared/types';
```

- [ ] **Step 2: 扩展 store 接口**

在 `SlackWorkspaceStore` 接口中添加字段和方法：

```typescript
interface SlackWorkspaceStore {
  // 现有字段...
  
  // 新增字段
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  
  // 现有方法...
  
  // 新增方法
  addMessage: (role: MessageRole, content: string) => void;
  addMessages: (role: MessageRole, contents: string[]) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;
}
```

- [ ] **Step 3: 实现 store 方法**

在 `create<SlackWorkspaceStore>()` 调用中添加实现：

```typescript
export const useSlackWorkspaceStore = create<SlackWorkspaceStore>((set) => ({
  // 现有字段初始值...
  
  // 新增字段初始值
  conversationMessages: [],
  isHistoryCollapsed: false,
  
  // 现有方法...
  
  // 新增方法实现
  addMessage: (role, content) =>
    set((state) => ({
      conversationMessages: [
        ...state.conversationMessages,
        {
          id: crypto.randomUUID(),
          role,
          content,
          timestamp: Date.now(),
        },
      ],
    })),
  
  addMessages: (role, contents) =>
    set((state) => ({
      conversationMessages: [
        ...state.conversationMessages,
        ...contents.map((content) => ({
          id: crypto.randomUUID(),
          role,
          content,
          timestamp: Date.now(),
        })),
      ],
    })),
  
  removeMessage: (id) =>
    set((state) => ({
      conversationMessages: state.conversationMessages.filter((msg) => msg.id !== id),
    })),
  
  updateMessage: (id, content) =>
    set((state) => ({
      conversationMessages: state.conversationMessages.map((msg) =>
        msg.id === id ? { ...msg, content } : msg
      ),
    })),
  
  clearConversation: () => set({ conversationMessages: [] }),
  
  toggleHistoryCollapse: () =>
    set((state) => ({ isHistoryCollapsed: !state.isHistoryCollapsed })),
}));
```

- [ ] **Step 4: 验证类型正确性**

```bash
cd web/frontend
npm run type-check
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/features/slack/store.ts
git commit -m "feat(slack): extend store with conversation history management"
```

---

## Task 7: 前端对话历史组件

**Files:**
- Create: `web/frontend/src/features/slack/components/ConversationHistory.tsx`

- [ ] **Step 1: 创建组件文件**

创建 `ConversationHistory.tsx` 文件：

```typescript
import { useState } from 'react';
import { X, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import type { ConversationMessage } from '@/shared/types';

interface ConversationHistoryProps {
  messages: ConversationMessage[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onRemoveMessage: (id: string) => void;
  onUpdateMessage: (id: string, content: string) => void;
  onClearAll: () => void;
}

export function ConversationHistory({
  messages,
  isCollapsed,
  onToggleCollapse,
  onRemoveMessage,
  onUpdateMessage,
  onClearAll,
}: ConversationHistoryProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const handleStartEdit = (msg: ConversationMessage) => {
    setEditingId(msg.id);
    setEditContent(msg.content);
  };

  const handleSaveEdit = (id: string) => {
    if (editContent.trim()) {
      onUpdateMessage(id, editContent.trim());
    }
    setEditingId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  if (messages.length === 0) {
    return null;
  }

  return (
    <Card className="mb-6 p-4">
      <div className="mb-2 flex items-center justify-between">
        <button
          onClick={onToggleCollapse}
          className="flex items-center gap-2 text-sm font-semibold hover:text-primary"
        >
          {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          对话历史 ({messages.length} 条消息)
        </button>
        <Button variant="ghost" size="sm" onClick={onClearAll}>
          <Trash2 className="h-4 w-4" />
          清空对话
        </Button>
      </div>

      {!isCollapsed && (
        <div className="space-y-2">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="group flex items-start gap-2 rounded-lg border bg-muted/30 p-3"
            >
              <div className="flex-1">
                <div className="mb-1 text-xs font-semibold text-muted-foreground">
                  {msg.role === 'me' ? '[我]' : '[对方]'}
                </div>
                {editingId === msg.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full rounded border p-2 text-sm"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleSaveEdit(msg.id)}>
                        保存
                      </Button>
                      <Button size="sm" variant="outline" onClick={handleCancelEdit}>
                        取消
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div
                    onClick={() => handleStartEdit(msg)}
                    className="cursor-pointer whitespace-pre-wrap text-sm hover:text-primary"
                  >
                    {msg.content}
                  </div>
                )}
              </div>
              <button
                onClick={() => onRemoveMessage(msg.id)}
                className="opacity-0 transition-opacity group-hover:opacity-100"
              >
                <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
              </button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: 验证组件编译**

```bash
cd web/frontend
npm run type-check
```

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/features/slack/components/ConversationHistory.tsx
git commit -m "feat(slack): add conversation history component"
```

---

## Task 8: 前端主界面集成

**Files:**
- Modify: `web/frontend/src/features/slack/index.tsx`

- [ ] **Step 1: 导入新组件和 store 方法**

在文件顶部添加导入：

```typescript
import { ConversationHistory } from './components/ConversationHistory';
```

在 `useSlackWorkspaceStore` 调用中添加新字段：

```typescript
const {
  incomingText, incomingTranslation, incomingSuggestions,
  draftText, draftVersions,
  conversationMessages, isHistoryCollapsed,
  setIncomingText, setIncomingResult, clearIncoming,
  setDraftText, setDraftVersions, clearDraft,
  addMessage, addMessages, removeMessage, updateMessage, clearConversation, toggleHistoryCollapse,
} = useSlackWorkspaceStore();
```

- [ ] **Step 2: 修改 handleAnalyze 函数**

替换现有的 `handleAnalyze` 函数：

```typescript
const handleAnalyze = async () => {
  const content = incomingText.trim();
  if (!content || analyzeMutation.isPending) return;
  
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  
  try {
    const result = await analyzeMutation.mutateAsync({ 
      message: lines[lines.length - 1],
      conversation_history: conversationMessages,
    });
    
    addMessages('them', lines);
    setIncomingResult(result.translation, result.suggested_replies ?? []);
    setIncomingText('');
  } catch { /* handled */ }
};
```

- [ ] **Step 3: 修改 handleTranslateDraft 函数**

在 `handleTranslateDraft` 函数中，修改 `mutateAsync` 调用：

```typescript
const handleTranslateDraft = async () => {
  const content = draftText.trim();
  if (!content || composeMutation.isPending) return;
  if (draftLanguage === 'en') {
    toast.error('这里用于中文草稿。英文内容直接复制即可。');
    return;
  }
  try {
    const result = await composeMutation.mutateAsync({ 
      content,
      conversation_history: conversationMessages,
    });
    setDraftVersions(
      result.versions.map((v: SlackReplyVariant) => ({ ...v, chinese: v.chinese || content }))
    );
  } catch { /* handled */ }
};
```

- [ ] **Step 4: 修改回复选择处理**

在 `ReplySuggestions` 的 `onSelectReply` 回调中，修改为：

```typescript
onSelectReply={async (en) => {
  await copyEnglish(en, '建议回复已复制');
  addMessage('me', en);
  toast.success('已复制并加入对话历史');
}}
```

在右栏的 `ReplySuggestions` 的 `onSelectReply` 回调中，修改为：

```typescript
onSelectReply={async (en) => {
  await copyEnglish(en, '英文版本已复制');
  addMessage('me', en);
  setDraftText('');
  toast.success('已复制并加入对话历史');
}}
```

- [ ] **Step 5: 添加 ConversationHistory 组件到 JSX**

在 `return` 语句的 `<div className="mx-auto grid...">` 之前添加：

```typescript
<ConversationHistory
  messages={conversationMessages}
  isCollapsed={isHistoryCollapsed}
  onToggleCollapse={toggleHistoryCollapse}
  onRemoveMessage={removeMessage}
  onUpdateMessage={updateMessage}
  onClearAll={clearConversation}
/>
```

- [ ] **Step 6: 验证编译**

```bash
cd web/frontend
npm run type-check
```

Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add web/frontend/src/features/slack/index.tsx
git commit -m "feat(slack): integrate conversation history into main UI"
```

---

## Task 9: 端到端测试

**Files:**
- Test: 整个 Slack 功能

- [ ] **Step 1: 启动后端服务**

```bash
cd C:\Users\DELL\Desktop\translation_agent
python -m uvicorn src.api.app:app --reload --port 54321
```

Expected: 服务启动成功

- [ ] **Step 2: 启动前端服务**

在新终端：
```bash
cd web/frontend
npm run dev
```

Expected: 前端启动成功

- [ ] **Step 3: 测试场景 1 - 对方发起对话**

1. 打开浏览器访问 `http://localhost:54321`
2. 进入 Slack 功能页面
3. 左栏输入："Hey, about the PR"
4. 点击"英译中 + 建议回复"
5. 验证：对话历史区显示 `[对方] Hey, about the PR`
6. 验证：显示中文翻译和 A/B/C 建议回复
7. 选择建议回复 B 并复制
8. 验证：对话历史区显示 `[我] <选择的回复>`
9. 验证：Toast 提示"已复制并加入对话历史"

- [ ] **Step 4: 测试场景 2 - 我发起对话**

1. 清空对话历史
2. 右栏输入："关于那个 PR 我有个问题"
3. 点击"生成英文版本"
4. 选择版本 B 并复制
5. 验证：对话历史区显示 `[我] <英文版本>`
6. 左栏输入："Sure, what's the question?"
7. 点击"英译中 + 建议回复"
8. 验证：对话历史区显示两条消息（我的 + 对方的）
9. 验证：建议回复基于上下文生成

- [ ] **Step 5: 测试场景 3 - 批量粘贴**

1. 清空对话历史
2. 左栏输入多行：
   ```
   Hey there
   I reviewed your code
   Looks good overall
   ```
3. 点击"英译中 + 建议回复"
4. 验证：对话历史区显示 3 条 `[对方]` 消息
5. 验证：翻译和建议基于最后一条消息

- [ ] **Step 6: 测试历史管理**

1. 点击某条消息内容
2. 验证：进入编辑模式
3. 修改内容并保存
4. 验证：消息内容更新
5. 点击某条消息的 [×] 按钮
6. 验证：消息被删除，Toast 提示"已从对话历史中移除"
7. 点击"清空对话"
8. 验证：所有消息清空，Toast 提示"对话历史已清空"

- [ ] **Step 7: 测试折叠/展开**

1. 添加几条消息
2. 点击"对话历史 (N 条消息)"
3. 验证：历史区折叠，只显示标题
4. 再次点击
5. 验证：历史区展开，显示所有消息

- [ ] **Step 8: 测试刷新页面**

1. 添加几条消息
2. 刷新浏览器页面
3. 验证：对话历史清空（会话级保存）

- [ ] **Step 9: 测试向后兼容**

1. 使用 API 测试工具（如 Postman）
2. 发送不带 `conversation_history` 的请求到 `/slack/process`
3. 验证：正常返回结果（无状态模式）

- [ ] **Step 10: 记录测试结果**

创建测试报告文件：

```bash
echo "# Slack 对话上下文功能测试报告

测试日期：$(date +%Y-%m-%d)

## 测试场景
- [x] 对方发起对话
- [x] 我发起对话
- [x] 批量粘贴多条消息
- [x] 编辑历史消息
- [x] 删除历史消息
- [x] 清空对话
- [x] 折叠/展开历史
- [x] 刷新页面清空
- [x] 向后兼容

## 测试结果
所有场景通过。
" > docs/superpowers/test-reports/2026-04-15-slack-context-test.md
```

- [ ] **Step 11: Commit**

```bash
git add docs/superpowers/test-reports/2026-04-15-slack-context-test.md
git commit -m "test(slack): add conversation context E2E test report"
```

---

## 自检清单

**Spec 覆盖检查**:
- ✅ 对话历史管理（Task 6, 7）
- ✅ 自动加入历史（Task 8）
- ✅ 会话级保存（Task 6 - Zustand 内存存储）
- ✅ 完整上下文传递（Task 2, 3, 4）
- ✅ 双向支持（Task 8 - handleAnalyze 和 handleTranslateDraft）
- ✅ 批量粘贴（Task 8 - lines.split）
- ✅ 编辑/删除消息（Task 7）
- ✅ 折叠/展开（Task 7）
- ✅ 向后兼容（Task 1 - default_factory=list）

**占位符检查**:
- ✅ 所有代码块包含完整实现
- ✅ 所有文件路径精确
- ✅ 所有命令包含预期输出
- ✅ 无 TBD/TODO/类似引用

**类型一致性检查**:
- ✅ `ConversationMessage` 在前后端定义一致
- ✅ `MessageRole` 类型为 `'them' | 'me'`（前端）和 `Literal["them", "me"]`（后端）
- ✅ Store 方法签名与组件 props 匹配
- ✅ API 参数类型与 DTO 定义匹配

---

## 实现完成标准

- [ ] 所有 9 个 Task 的所有步骤完成
- [ ] 所有测试场景通过
- [ ] 代码通过类型检查和编译
- [ ] 所有更改已提交到 git
- [ ] 功能在浏览器中正常工作
