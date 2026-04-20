# Slack 回复功能 UX 重设计

**日期**: 2026-04-19  
**状态**: 已批准  
**作者**: Claude + 用户

## 背景

当前 Slack 回复功能存在严重的 UX 问题：
- 左右两栏的区分不清晰（都是选版本→调整→确认的流程）
- "修改建议回复"和"输入中文生成版本"的交互逻辑混乱
- 用户反馈"几乎不可用"

## 核心问题

用户的真实需求非常简单：
1. 对方发来英文 → 看翻译 → AI 给建议回复 → 不满意就输入我想说的中文 → 重新生成 A/B/C → 选一个
2. 我主动发起 → 输入中文 → 生成 A/B/C → 不满意就修改中文 → 重新生成 → 选一个

**关键洞察**：两种场景的流程完全一样，只是起点不同（对方消息 vs 我的想法）

## 解决方案：单栏气泡式设计

### 界面布局

```
┌─────────────────────────────────────┐
│  [对话历史区 - 可滚动]               │
│                                     │
│  ┌──────────────┐                  │
│  │ 对方的消息    │ (灰色气泡，靠左) │
│  │ [中文翻译]    │ (可展开)         │
│  └──────────────┘                  │
│                                     │
│            ┌──────────────┐        │
│            │ 我的回复      │ (蓝色) │
│            └──────────────┘        │
│                                     │
├─────────────────────────────────────┤
│  [当前回复工作区]                    │
│                                     │
│  📝 输入中文回复：                   │
│  ┌─────────────────────────────┐   │
│  │ [文本框]                     │   │
│  └─────────────────────────────┘   │
│  [生成回复 / 重新生成] 按钮          │
│                                     │
│  💡 生成的版本：                     │
│  ┌─────────────────────────────┐   │
│  │ A: ...                       │   │
│  │ [选择并发送] [仅复制]         │   │
│  ├─────────────────────────────┤   │
│  │ B: ...                       │   │
│  │ [选择并发送] [仅复制]         │   │
│  ├─────────────────────────────┤   │
│  │ C: ...                       │   │
│  │ [选择并发送] [仅复制]         │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### 交互流程

**场景 1：对方发起对话**
1. 用户粘贴对方英文 → 点击"翻译并生成建议"
2. 对方消息加入历史（灰色气泡，含中文翻译）
3. 自动生成 A/B/C 三个建议回复
4. 用户可以：
   - 直接选择一个 → 加入历史（蓝色气泡）
   - 或修改输入框中文 → 重新生成 A/B/C
5. 循环直到满意

**场景 2：我主动发起**
1. 用户在输入框输入中文 → 点击"生成回复"
2. 显示 A/B/C 三个版本
3. 选择一个 → 加入历史（蓝色气泡）
4. 或修改中文 → 重新生成

## 数据模型

### 简化的状态管理

```typescript
interface SlackWorkspaceState {
  // 当前工作区状态
  currentInput: string;              // 用户输入的中文
  currentVersions: SlackReplyVariant[]; // 生成的 A/B/C 版本
  isGenerating: boolean;             // 是否正在生成
  
  // 对话历史
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  
  // 其他
  selectedModel: string;
  
  // Actions
  setCurrentInput: (value: string) => void;
  setCurrentVersions: (versions: SlackReplyVariant[]) => void;
  setGenerating: (value: boolean) => void;
  clearWorkspace: () => void;
  
  addMessage: (role: 'me' | 'them', content: string, translation?: string) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;
  
  setSelectedModel: (model: string) => void;
}
```

### ConversationMessage 扩展

```typescript
interface ConversationMessage {
  id: string;
  role: 'me' | 'them';
  content: string;           // 英文内容
  translation?: string;      // 对方消息的中文翻译（可选）
  timestamp: number;
}
```

**关键变化**：
- 移除 `incomingText/draftText/incomingRefinement/draftRefinement` 等复杂状态
- 统一为 `currentInput` 和 `currentVersions`
- 对话历史中对方的消息包含 `translation` 字段

## UI 组件结构

```
SlackFeature (主容器)
├── Header (标题 + 模型选择器)
├── ConversationBubbles (对话气泡区 - 新组件)
│   └── MessageBubble[] (单个消息气泡)
│       ├── ThemBubble (对方消息 - 灰色靠左)
│       └── MeBubble (我的消息 - 蓝色靠右)
└── ReplyWorkspace (回复工作区 - 新组件)
    ├── InputSection (输入区)
    │   ├── Textarea (中文输入框)
    │   └── Button (生成回复/重新生成)
    └── VersionsSection (版本选择区)
        └── VersionCard[] (A/B/C 三个版本卡片)
            ├── 英文内容
            ├── Button (选择并发送)
            └── Button (仅复制)
```

### 新组件说明

**ConversationBubbles**
- 替代现有的 ConversationHistory
- 使用气泡样式，类似聊天应用
- 对方消息：灰色背景，靠左，显示英文 + 可展开的中文翻译
- 我的消息：蓝色背景，靠右，只显示英文
- 支持悬停显示编辑/删除按钮

**ReplyWorkspace**
- 替代现有的左右两栏
- 固定在底部或下半部分
- 两种状态：
  1. 初始状态：只显示输入框 + 生成按钮
  2. 生成后：显示输入框 + A/B/C 版本卡片

**VersionCard**
- 显示单个版本（A/B/C）
- 两个操作按钮：
  - "选择并发送"：加入对话历史 + 清空工作区
  - "仅复制"：复制到剪贴板，不加入历史

## API 端点

### 使用现有 API

**1. 翻译对方消息 + 生成建议回复**
```typescript
POST /api/slack/process
Request: {
  message: string;
  conversation_history: ConversationMessage[];
  model?: string;
}
Response: {
  translation: string;
  suggested_replies: SlackReplyVariant[];
}
```

**2. 中文翻译成英文**
```typescript
POST /api/slack/compose
Request: {
  content: string;
  conversation_history: ConversationMessage[];
  model?: string;
}
Response: {
  versions: SlackReplyVariant[];
}
```

### 移除的 API

- `/slack/refine` - 不再需要（不做单版本细修）

## 实现顺序

### 阶段 1：数据层重构（2-3h）
1. 简化 Store 状态模型
2. 扩展 ConversationMessage 类型

### 阶段 2：UI 组件开发（4-5h）
3. 创建 ConversationBubbles 组件
4. 创建 ReplyWorkspace 组件

### 阶段 3：主界面重构（2-3h）
5. 重写 SlackFeature 主组件
6. 清理旧代码

### 阶段 4：测试和优化（1-2h）
7. 端到端测试
8. 样式优化

**总预估时间**: 9-13 小时

## 技术细节

### 样式设计

```css
.bubble-them {
  background: hsl(var(--muted));
  border-radius: 16px 16px 16px 4px;
  max-width: 70%;
  align-self: flex-start;
}

.bubble-me {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-radius: 16px 16px 4px 16px;
  max-width: 70%;
  align-self: flex-end;
}
```

### 关键交互细节

1. **输入框的智能状态**
   - 对方发起：自动填充建议回复的中文意思
   - 我发起：空白，等待用户输入
   - 重新生成：保留用户修改的内容

2. **按钮文案变化**
   - 初始状态："生成回复"
   - 已有版本："重新生成"
   - 生成中："生成中..." (禁用)

3. **"仅复制"按钮的用途**
   - 用户想复制但不想加入对话历史
   - 或者想在外部修改后再发送

### 边界情况处理

- API 调用失败：显示错误提示，保留用户输入
- 空输入：禁用生成按钮
- 生成中：禁用所有操作按钮
- 选择版本后：立即清空工作区

## 预期效果

- ✅ 交互流程清晰：对话历史 + 工作区，符合聊天工具直觉
- ✅ 功能简化：移除不必要的"细修单个版本"功能
- ✅ 视觉清晰：气泡样式明确区分对方和我的消息
- ✅ 灵活性：支持"直接选"和"反复调整"两种使用方式
