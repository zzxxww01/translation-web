# Slack 回复功能重构设计

**日期**: 2026-04-19  
**状态**: 待实现  
**方案**: 保持左右栏 + 多轮调整 + 手动确认历史

## 背景

当前 Slack 回复功能存在以下问题：
1. 不支持多轮调整 - 对生成结果不满意时无法继续优化
2. 自动加入历史 - 用户复制后可能没实际发送，导致历史不准确
3. 交互逻辑不清晰 - 用户不确定何时消息会加入历史

## 核心改进

### 1. 多轮调整支持
- 左栏（对方消息）和右栏（我的草稿）都支持多轮调整
- 结果区下方增加"继续调整"输入框
- 用户可以反复要求 AI 优化，直到满意

### 2. 手动确认历史
- 每个回复版本旁边有 [✓ 用这个] 按钮
- 只有点击确认后才加入对话历史
- 单纯 [复制] 不会加入历史

### 3. 调整历史可见
- 显示用户的每次调整要求
- 支持撤销某次调整
- 保持调整上下文，AI 理解完整意图

## 数据模型

### 前端状态

```typescript
// 调整会话（Refinement Session）
interface RefinementSession {
  id: string;                    // 会话 ID
  type: 'incoming' | 'draft';    // 左栏 or 右栏
  originalInput: string;         // 原始输入
  currentResult: {
    translation?: string;        // 翻译（仅 incoming）
    variants: SlackReplyVariant[]; // A/B/C 版本
  };
  refinementHistory: RefinementTurn[]; // 调整历史
  status: 'idle' | 'generating' | 'refining';
}

interface RefinementTurn {
  userRequest: string;           // 用户的调整要求
  aiResponse: {
    translation?: string;
    variants: SlackReplyVariant[];
  };
  timestamp: number;
}

// 全局状态
interface SlackWorkspaceStore {
  // 对话历史（已确认的消息）
  conversationMessages: ConversationMessage[];
  
  // 左栏会话
  incomingSession: RefinementSession | null;
  
  // 右栏会话
  draftSession: RefinementSession | null;
  
  // 选中的模型
  selectedModel: string;
  
  // 历史管理
  isHistoryCollapsed: boolean;
  
  // 方法
  startIncomingSession: (input: string) => void;
  startDraftSession: (input: string) => void;
  refineSession: (type: 'incoming' | 'draft', request: string) => void;
  confirmAndAddToHistory: (type: 'incoming' | 'draft', variant: SlackReplyVariant) => void;
  undoLastRefinement: (type: 'incoming' | 'draft') => void;
  clearSession: (type: 'incoming' | 'draft') => void;
}
```

### 后端数据模型

```python
class SlackRefineRequest(BaseModel):
    """多轮调整请求"""
    session_type: Literal["incoming", "draft"]
    original_input: str
    current_result: dict  # 当前的翻译和版本
    refinement_request: str  # 用户的调整要求
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    model: Optional[str] = None

class SlackRefineResponse(BaseModel):
    """多轮调整响应"""
    translation: Optional[str] = None  # 仅 incoming 类型
    variants: list[SlackReplyVariant]
```

## UI 设计

### 左栏（对方的话）- 完整流程

#### 初始状态
```
┌─────────────────────────────────────┐
│ 对方的话                             │
├─────────────────────────────────────┤
│ [输入框：粘贴对方的英文消息...]      │
│                                     │
│ [英译中 + 建议回复] [重置]          │
└─────────────────────────────────────┘
```

#### 显示初始结果
```
┌─────────────────────────────────────┐
│ 对方的话                             │
├─────────────────────────────────────┤
│ [已分析的消息，灰色背景]             │
│ "Hey, can you review the PR?"       │
│                                     │
│ [重新分析] [清空]                    │
├─────────────────────────────────────┤
│ 中文理解：                           │
│ "嘿，你能审查一下这个 PR 吗？"       │
├─────────────────────────────────────┤
│ 建议回复：                           │
│                                     │
│ A (最随意)                          │
│ yep, on it                          │
│ 中文：好的，马上看                   │
│ [✓ 用这个] [复制]                   │
│                                     │
│ B (标准职场)                        │
│ sure, I'll take a look              │
│ 中文：好的，我看一下                 │
│ [✓ 用这个] [复制]                   │
│                                     │
│ C (较正式)                          │
│ certainly, I'll review it shortly   │
│ 中文：当然，我马上审查                │
│ [✓ 用这个] [复制]                   │
├─────────────────────────────────────┤
│ 不满意？继续调整：                   │
│ [输入框：比如"B版本改得更友好"]      │
│ [调整]                              │
└─────────────────────────────────────┘
```

#### 显示调整结果
```
┌─────────────────────────────────────┐
│ 对方的话                             │
├─────────────────────────────────────┤
│ [已分析的消息]                       │
│ "Hey, can you review the PR?"       │
├─────────────────────────────────────┤
│ 中文理解：                           │
│ "嘿，你能审查一下这个 PR 吗？"       │
├─────────────────────────────────────┤
│ 调整历史：                           │
│ > 你说："B 版本改得更随意一点"       │
│   [撤销这次调整]                     │
├─────────────────────────────────────┤
│ 建议回复（已调整）：                 │
│                                     │
│ A (最随意)                          │
│ yep, on it                          │
│ [✓ 用这个] [复制]                   │
│                                     │
│ B (标准职场) - 已调整               │
│ sure thing, I'll check it out       │
│ 中文：没问题，我看看                 │
│ [✓ 用这个] [复制]                   │
│                                     │
│ C (较正式)                          │
│ certainly, I'll review it shortly   │
│ [✓ 用这个] [复制]                   │
├─────────────────────────────────────┤
│ 还需要调整？                         │
│ [输入框]                            │
│ [继续调整]                          │
└─────────────────────────────────────┘
```

#### 确认加入历史
点击 [✓ 用这个] 后弹出对话框：
```
┌─────────────────────────────────────┐
│ 确认加入对话历史                     │
├─────────────────────────────────────┤
│ 将以下消息加入对话历史：             │
│                                     │
│ [对方] Hey, can you review the PR?  │
│ [我]   sure thing, I'll check it out│
│                                     │
│ ☑ 同时复制到剪贴板                  │
│                                     │
│ [确认] [取消]                       │
└─────────────────────────────────────┘
```

确认后：
- 对话历史新增两条消息
- 左栏清空，回到初始状态
- Toast："已加入对话历史并复制"

### 右栏（我想说的话）- 完整流程

#### 初始状态
```
┌─────────────────────────────────────┐
│ 我想说的话                           │
├─────────────────────────────────────┤
│ [输入框：输入你的中文草稿...]        │
│                                     │
│ [中译英] [重置]                     │
└─────────────────────────────────────┘
```

#### 显示生成结果
```
┌─────────────────────────────────────┐
│ 我想说的话                           │
├─────────────────────────────────────┤
│ [已生成的中文草稿，灰色背景]         │
│ "我明天请假，家里有事"               │
│                                     │
│ [重新生成] [清空]                    │
├─────────────────────────────────────┤
│ 英文版本：                           │
│                                     │
│ A (最随意)                          │
│ taking tomorrow off, family stuff   │
│ [✓ 用这个] [复制]                   │
│                                     │
│ B (标准职场)                        │
│ I'll be out tomorrow, family matter │
│ [✓ 用这个] [复制]                   │
│                                     │
│ C (较正式)                          │
│ I'll be taking a day off tomorrow   │
│ due to a family matter              │
│ [✓ 用这个] [复制]                   │
├─────────────────────────────────────┤
│ 需要调整？                           │
│ [输入框：比如"A版本加上请假时间"]    │
│ [调整]                              │
└─────────────────────────────────────┘
```

#### 显示调整结果
```
┌─────────────────────────────────────┐
│ 我想说的话                           │
├─────────────────────────────────────┤
│ [已生成的中文草稿]                   │
│ "我明天请假，家里有事"               │
├─────────────────────────────────────┤
│ 调整历史：                           │
│ > 你说："A 版本说明是全天请假"       │
│   [撤销这次调整]                     │
├─────────────────────────────────────┤
│ 英文版本（已调整）：                 │
│                                     │
│ A (最随意) - 已调整                 │
│ taking the full day off tomorrow,   │
│ family stuff                        │
│ [✓ 用这个] [复制]                   │
│                                     │
│ B (标准职场)                        │
│ I'll be out tomorrow, family matter │
│ [✓ 用这个] [复制]                   │
│                                     │
│ C (较正式)                          │
│ I'll be taking a day off tomorrow   │
│ due to a family matter              │
│ [✓ 用这个] [复制]                   │
├─────────────────────────────────────┤
│ 还需要调整？                         │
│ [输入框]                            │
│ [继续调整]                          │
└─────────────────────────────────────┘
```

#### 确认加入历史
点击 [✓ 用这个] 后弹出对话框：
```
┌─────────────────────────────────────┐
│ 确认加入对话历史                     │
├─────────────────────────────────────┤
│ 将以下消息加入对话历史：             │
│                                     │
│ [我] taking the full day off        │
│      tomorrow, family stuff         │
│                                     │
│ ☑ 同时复制到剪贴板                  │
│                                     │
│ [确认] [取消]                       │
└─────────────────────────────────────┘
```

### 对话历史管理

#### 显示状态
```
┌─────────────────────────────────────┐
│ ▼ 对话历史 (5 条消息)  [清空全部]   │
├─────────────────────────────────────┤
│ [对方] Hey, can you review...  [×]  │
│ [我]   sure thing, I'll...     [×]  │
│ [对方] Thanks! When can...     [×]  │
│ [我]   I'll have it done...    [×]  │
│ [对方] Perfect, appreciate it  [×]  │
│                                     │
│ [+ 手动添加消息]                    │
└─────────────────────────────────────┘
```

#### 手动添加消息
点击 [+ 手动添加消息]：
```
┌─────────────────────────────────────┐
│ 添加消息到对话历史                   │
├─────────────────────────────────────┤
│ 消息来源：                           │
│ ○ 对方  ○ 我                       │
│                                     │
│ 消息内容：                           │
│ [输入框]                            │
│                                     │
│ [添加] [取消]                       │
└─────────────────────────────────────┘
```

**用途**：用户直接在 Slack 发了消息，想补录到历史中

#### 编辑消息
点击消息内容：
```
┌─────────────────────────────────────┐
│ [对方]                              │
│ [输入框：Hey, can you review...]    │
│ [保存] [取消]                       │
└─────────────────────────────────────┘
```

## 交互流程

### 场景 1：对方发消息给我

1. 用户在左栏粘贴："Hey, can you review the PR?"
2. 点击 [英译中 + 建议回复]
3. 显示翻译 + 建议回复 A/B/C
4. 用户觉得 B 版本不够随意，输入："B 版本改得更随意一点"
5. 点击 [调整]，AI 重新生成 B 版本
6. 用户满意，点击 B 版本的 [✓ 用这个]
7. 弹出确认对话框，显示将加入的两条消息
8. 点击 [确认]
9. 对话历史新增：
   - [对方] Hey, can you review the PR?
   - [我] sure thing, I'll check it out
10. 左栏清空，回到初始状态

### 场景 2：我主动发起

1. 用户在右栏输入："我明天请假，家里有事"
2. 点击 [中译英]
3. 显示英文版本 A/B/C
4. 用户觉得 A 版本需要说明是全天，输入："A 版本说明是全天请假"
5. 点击 [调整]，AI 调整 A 版本
6. 用户满意，点击 A 版本的 [✓ 用这个]
7. 弹出确认对话框
8. 点击 [确认]
9. 对话历史新增：
   - [我] taking the full day off tomorrow, family stuff
10. 右栏清空，回到初始状态

### 场景 3：只复制不加入历史

1. 用户生成了回复版本
2. 点击 [复制] 按钮（不点 [✓ 用这个]）
3. 内容复制到剪贴板
4. Toast："已复制（未加入历史）"
5. 会话状态保持，用户可以继续调整或清空

### 场景 4：撤销调整

1. 用户已经调整了 2 次
2. 发现第 2 次调整不如第 1 次
3. 点击第 2 次调整历史中的 [撤销这次调整]
4. 结果回退到第 1 次调整后的状态
5. 调整历史移除最后一条

### 场景 5：重新分析/生成

1. 用户已经调整了多次
2. 发现原始输入有问题，想重新开始
3. 点击 [重新分析] 或 [重新生成]
4. 清空当前会话（包括调整历史）
5. 重新调用初始 API
6. 显示新的初始结果

## 后端实现

### 新增 API 端点

```python
@router.post(
    "/slack/refine",
    response_model=SlackRefineResponse,
    summary="Refine Slack reply based on user feedback",
    description="Multi-turn refinement for Slack replies",
    tags=["slack"],
)
async def refine_slack_result(request: SlackRefineRequest):
    """
    多轮调整接口
    
    根据用户的调整要求，重新生成结果
    保持 A/B/C 结构，只修改用户要求的部分
    """
    session_type = request.session_type
    original_input = request.original_input
    current_result = request.current_result
    refinement_request = request.refinement_request
    conversation_history = request.conversation_history
    
    # 构建 prompt
    conversation_history_section = format_conversation_history(conversation_history)
    
    if session_type == "incoming":
        prompt = prompt_manager.get(
            "slack_refine_incoming",
            conversation_history_section=conversation_history_section,
            original_message=original_input,
            current_translation=current_result.get("translation", ""),
            current_variants=json.dumps(current_result.get("variants", []), ensure_ascii=False),
            refinement_request=refinement_request,
        )
    else:  # draft
        prompt = prompt_manager.get(
            "slack_refine_draft",
            conversation_history_section=conversation_history_section,
            original_draft=original_input,
            current_variants=json.dumps(current_result.get("variants", []), ensure_ascii=False),
            refinement_request=refinement_request,
        )
    
    try:
        response_text = generate_with_fallback(prompt, task_type="slack")
        data = parse_llm_json_response(response_text)
        
        translation = data.get("translation") if session_type == "incoming" else None
        variants = normalize_variants(data.get("variants", []))
        
        return SlackRefineResponse(
            translation=translation,
            variants=variants,
        )
    except Exception as exc:
        raise_llm_service_unavailable(operation="Slack refine", exc=exc)
```

### 新增 Prompt 模板

#### slack_refine_incoming.txt
```
You are an expat employee at a top tech or hardware company.
You are helping refine Slack reply suggestions based on user feedback.

{conversation_history_section}

## Original incoming message
{original_message}

## Current translation
{current_translation}

## Current suggested replies
{current_variants}

## User's refinement request
{refinement_request}

## Task
Based on the user's request, adjust the suggested replies.
- Keep the same structure: translation + 3 variants (A/B/C)
- Only modify what the user asked for
- Keep other parts unchanged unless the user explicitly asks to change them
- Maintain the formality levels: A (casual), B (standard), C (formal)

## Output (strict JSON)
{{
  "translation": "Chinese translation (keep unchanged unless user asks)",
  "suggested_replies": [
    {{
      "version": "A",
      "english": "...",
      "chinese": "..."
    }},
    {{
      "version": "B",
      "english": "...",
      "chinese": "..."
    }},
    {{
      "version": "C",
      "english": "...",
      "chinese": "..."
    }}
  ]
}}

Output only the JSON object.
```

#### slack_refine_draft.txt
```
You are an expat employee at a top tech or hardware company.
You are helping refine English versions of a Chinese draft based on user feedback.

{conversation_history_section}

## Original Chinese draft
{original_draft}

## Current English versions
{current_variants}

## User's refinement request
{refinement_request}

## Task
Based on the user's request, adjust the English versions.
- Keep the same structure: 3 variants (A/B/C)
- Only modify what the user asked for
- Keep other parts unchanged unless the user explicitly asks to change them
- Maintain the formality levels: A (casual), B (standard), C (formal)

## Output (strict JSON)
{{
  "versions": [
    {{
      "version": "A",
      "english": "..."
    }},
    {{
      "version": "B",
      "english": "..."
    }},
    {{
      "version": "C",
      "english": "..."
    }}
  ]
}}

Output only the JSON object.
```

## 前端实现

### 状态管理（store.ts）

```typescript
interface SlackWorkspaceStore {
  // 对话历史
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  
  // 左栏会话
  incomingSession: RefinementSession | null;
  
  // 右栏会话
  draftSession: RefinementSession | null;
  
  // 模型选择
  selectedModel: string;
  
  // 会话管理
  startIncomingSession: (input: string, result: ProcessResult) => void;
  startDraftSession: (input: string, result: ComposeResult) => void;
  refineIncomingSession: (request: string, result: RefineResult) => void;
  refineDraftSession: (request: string, result: RefineResult) => void;
  undoLastRefinement: (type: 'incoming' | 'draft') => void;
  clearSession: (type: 'incoming' | 'draft') => void;
  
  // 历史管理
  confirmAndAddToHistory: (messages: ConversationMessage[]) => void;
  addMessage: (role: MessageRole, content: string) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;
  
  // 模型选择
  setSelectedModel: (model: string) => void;
}
```

### API 调用（api.ts）

```typescript
export const slackApi = {
  processMessage: (data: ProcessMessageDto) =>
    apiClient.post<ProcessResult>('/slack/process', data),
  
  composeReply: (data: ComposeDto) =>
    apiClient.post<ComposeResult>('/slack/compose', data),
  
  refineResult: (data: RefineDto) =>
    apiClient.post<RefineResult>('/slack/refine', data),
};

interface RefineDto {
  session_type: 'incoming' | 'draft';
  original_input: string;
  current_result: {
    translation?: string;
    variants: SlackReplyVariant[];
  };
  refinement_request: string;
  conversation_history: ConversationMessage[];
  model?: string;
}

interface RefineResult {
  translation?: string;
  variants: SlackReplyVariant[];
}
```

### 主界面组件（index.tsx）

核心逻辑：
1. 初始生成：调用 `/slack/process` 或 `/slack/compose`
2. 多轮调整：调用 `/slack/refine`
3. 确认使用：弹出对话框，确认后加入历史
4. 撤销调整：回退到上一个结果
5. 重新生成：清空会话，重新调用初始 API

### 新增组件

#### RefinementPanel.tsx
显示调整历史和调整输入框

#### ConfirmHistoryDialog.tsx
确认加入历史的对话框

#### VariantCard.tsx
显示单个回复版本，包含 [✓ 用这个] 和 [复制] 按钮

## 边界情况处理

### 1. 调整过程中切换到另一栏
**场景**：左栏正在调整，用户点击右栏输入

**处理**：
- 弹出提示："左栏有未完成的调整，是否放弃？"
- [放弃并切换] [继续调整]

### 2. 调整过程中刷新页面
**处理**：
- 会话状态丢失（session-only）
- 对话历史保留（已确认的消息）

### 3. 只复制不加入历史
**操作**：
- 用户点击 [复制] 按钮（不点 [✓ 用这个]）
- 只复制到剪贴板，不加入历史
- Toast："已复制（未加入历史）"

### 4. 撤销调整
**操作**：
- 点击调整历史中的 [撤销这次调整]
- 回退到上一个结果
- `refinementHistory.pop()`

### 5. 重新分析/生成
**操作**：
- 点击 [重新分析] 或 [重新生成]
- 清空当前会话，重新调用初始 API
- 调整历史清空

### 6. 确认对话框中取消
**操作**：
- 用户点击 [✓ 用这个]，弹出确认对话框
- 用户点击 [取消]
- 会话状态保持，用户可以继续调整或选择其他版本

### 7. 手动添加消息
**用途**：
- 用户直接在 Slack 发了消息，想补录到历史中
- 点击 [+ 手动添加消息]
- 选择消息来源（对方/我）
- 输入消息内容
- 点击 [添加]

### 8. 编辑历史消息
**操作**：
- 点击历史消息内容
- 进入编辑模式
- 修改内容
- 点击 [保存]
- 不会重新调用 LLM，只是修正历史记录

## 关键特性

- ✅ 支持多轮调整，直到满意
- ✅ 手动确认加入历史，避免误操作
- ✅ 调整历史可见，支持撤销
- ✅ 保持左右栏分离，职责清晰
- ✅ 支持只复制不加入历史
- ✅ 支持手动添加/编辑历史消息
- ✅ 会话级保存，刷新清空
- ✅ 完整上下文传递给 LLM
- ✅ 后端无状态，易于部署
- ✅ 向后兼容现有功能

## 实现顺序

1. 后端：新增 `SlackRefineRequest` 和 `SlackRefineResponse` 数据模型
2. 后端：实现 `/slack/refine` API 端点
3. 后端：创建 `slack_refine_incoming.txt` 和 `slack_refine_draft.txt` prompt 模板
4. 前端：扩展 `SlackWorkspaceStore`，添加会话管理方法
5. 前端：创建 `RefinementPanel` 组件
6. 前端：创建 `ConfirmHistoryDialog` 组件
7. 前端：创建 `VariantCard` 组件
8. 前端：修改 `index.tsx` 主界面，集成新组件
9. 前端：实现多轮调整逻辑
10. 前端：实现手动确认历史逻辑
11. 测试：验证各种场景
12. 文档：更新用户手册
