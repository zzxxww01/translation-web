# Slack 回复功能 UX 重设计

**日期**: 2026-04-19  
**状态**: 设计中  
**作者**: Claude + 用户  
**版本**: v2 (合并版本卡片内编辑功能)

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

**用户反馈补充**（2026-04-20）：
- 用户希望支持**两种调整方式**：
  1. 在输入框输入新中文 → 重新生成所有版本
  2. 直接在版本卡片内编辑中文 → 只更新该版本
- 两个场景（我发起/对方发起）都应生成 3 个版本（简洁/正式/友好）

## 解决方案：单栏气泡式设计 + 版本卡片内编辑

### 界面布局

```
┌─────────────────────────────────────┐
│  [对话历史区 - 可滚动]               │
│                                     │
│  ┌──────────────┐                  │
│  │ 对方的消息    │ (灰色气泡，靠左) │
│  │ [中文翻译]    │ (小字显示)       │
│  └──────────────┘                  │
│                                     │
│            ┌──────────────┐        │
│            │ 我的回复      │ (蓝色) │
│            └──────────────┘        │
│                                     │
├─────────────────────────────────────┤
│  [当前回复工作区]                    │
│                                     │
│  📝 输入内容：                       │
│  ┌─────────────────────────────┐   │
│  │ [文本框]                     │   │
│  │ 粘贴对方的英文消息，或输入你  │   │
│  │ 想说的中文...                │   │
│  └─────────────────────────────┘   │
│  [生成回复 / 重新生成] 按钮          │
│                                     │
│  💡 生成的版本：                     │
│  ┌─────────────────────────────┐   │
│  │ [简洁]              [编辑]   │   │
│  │ 中文内容 (灰色小字)           │   │
│  │ English translation...       │   │
│  │ [使用此版本] [复制]           │   │
│  ├─────────────────────────────┤   │
│  │ [正式]              [编辑]   │   │
│  │ 中文内容 (灰色小字)           │   │
│  │ English translation...       │   │
│  │ [使用此版本] [复制]           │   │
│  ├─────────────────────────────┤   │
│  │ [友好]              [编辑]   │   │
│  │ 中文内容 (灰色小字)           │   │
│  │ English translation...       │   │
│  │ [使用此版本] [复制]           │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘

编辑状态：
┌─────────────────────────────────┐
│ [简洁]                          │
│ ┌─────────────────────────────┐ │
│ │ [中文编辑框 Textarea]        │ │
│ └─────────────────────────────┘ │
│ English translation...          │
│ [保存] [取消]                   │
└─────────────────────────────────┘
```

### 交互流程

**场景 1：对方发起对话**
1. 用户粘贴对方英文 → 点击"生成回复"
2. 系统检测为英文（中文字符占比 ≤ 30%）
3. 调用 `/api/slack/process`：翻译 + 生成 3 个建议回复
4. 对方消息加入历史（灰色气泡，含中文翻译）
5. 显示 3 个版本卡片（简洁/正式/友好），每个卡片显示：
   - 风格标签 + 编辑按钮
   - 中文内容（灰色小字）
   - 英文翻译（主要内容）
   - 操作按钮（使用此版本 / 复制）
6. 用户可以：
   - **方式 A：直接选择一个版本** → 加入历史（蓝色气泡）→ 清空工作区
   - **方式 B：在输入框输入新中文** → 点击"重新生成" → 替换所有 3 个版本
   - **方式 C：点击版本卡片的"编辑"按钮** → 卡片展开显示中文编辑框 → 修改中文 → 点击"保存" → 只更新该版本的英文翻译

**场景 2：我主动发起**
1. 用户在输入框输入中文 → 点击"生成回复"
2. 系统检测为中文（中文字符占比 > 30%）
3. 调用 `/api/slack/compose`：中译英生成 3 个版本
4. 显示 3 个版本卡片（与场景 1 完全相同）
5. 用户可以使用方式 A/B/C（同场景 1）

**关键点：**
- 两个场景使用完全相同的界面和交互
- 支持三种调整方式：直接选择、重新生成、卡片内编辑
- 输入框重新生成会替换所有版本
- 卡片内编辑只更新该版本

## 数据模型

### 简化的状态管理

```typescript
interface SlackWorkspaceState {
  // 当前工作区状态
  currentInput: string;              // 用户输入的中文或英文
  currentVersions: SlackReplyVariant[]; // 生成的 3 个版本
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

### SlackReplyVariant 扩展

```typescript
interface SlackReplyVariant {
  chinese: string;      // 对应的中文内容
  english: string;      // 英文翻译
  style: 'concise' | 'formal' | 'friendly';  // 风格标签
}
```

**关键变化**：
- 每个版本都包含 `chinese` 字段（用于卡片内编辑）
- 添加 `style` 字段标识版本风格

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
├── ConversationBubbles (对话气泡区)
│   └── MessageBubble[] (单个消息气泡)
│       ├── ThemBubble (对方消息 - 灰色靠左)
│       └── MeBubble (我的消息 - 蓝色靠右)
└── ReplyWorkspace (回复工作区)
    ├── InputSection (输入区)
    │   ├── Textarea (中文/英文输入框)
    │   └── Button (生成回复/重新生成)
    └── VersionsSection (版本选择区)
        └── VersionCard[] (3 个版本卡片：简洁/正式/友好)
            ├── 风格标签 + 编辑按钮
            ├── 中文内容（灰色小字）
            ├── 英文内容（主要内容）
            ├── 编辑状态（Textarea + 保存/取消按钮）
            └── 操作按钮（使用此版本 / 复制）
```

### 组件说明

**ConversationBubbles**
- 替代现有的 ConversationHistory
- 使用气泡样式，类似聊天应用
- 对方消息：灰色背景，靠左，显示英文 + 中文翻译（小字）
- 我的消息：蓝色背景，靠右，只显示英文
- 支持悬停显示编辑/删除按钮

**ReplyWorkspace**
- 替代现有的左右两栏
- 固定在底部或下半部分
- 两种状态：
  1. 初始状态：只显示输入框 + 生成按钮
  2. 生成后：显示输入框 + 3 个版本卡片

**VersionCard（增强版）**
- 显示单个版本（简洁/正式/友好）
- **显示状态：**
  - 风格标签（左上角）+ 编辑按钮（右上角）
  - 中文内容（灰色小字，opacity: 0.6）
  - 英文翻译（主要内容）
  - 操作按钮："使用此版本" + "复制"
- **编辑状态：**
  - 卡片展开，中文区域变为 Textarea
  - 显示"保存"和"取消"按钮
  - 英文区域保持显示（不变）
  - 边框高亮（primary 色）
- **保存中状态：**
  - 半透明（opacity: 0.6）
  - 保存按钮显示 spinner
- **禁用状态：**
  - 生成中时，所有编辑按钮禁用

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
  suggested_replies: SlackReplyVariant[];  // 包含 chinese, english, style
}
```

**2. 中文翻译成英文（生成 3 个版本）**
```typescript
POST /api/slack/compose
Request: {
  content: string;
  conversation_history: ConversationMessage[];
  model?: string;
}
Response: {
  versions: SlackReplyVariant[];  // 包含 chinese, english, style
}
```

### 新增 API

**3. 单版本精修（卡片内编辑）**
```typescript
POST /api/slack/refine-version
Request: {
  chinese: string;                              // 修改后的中文内容
  style: 'concise' | 'formal' | 'friendly';    // 保持原风格
  conversation_history?: ConversationMessage[]; // 可选：对话历史
  model?: string;                               // 可选：模型选择
}
Response: {
  english: string;  // 更新后的英文翻译
}
```

**用途：** 用户在版本卡片内编辑中文后，调用此 API 只更新该版本的英文翻译

**错误处理：**
- 400：中文内容为空
- 500：翻译服务失败

## 实现顺序

### 阶段 1：数据层重构（2-3h）
1. 扩展 `SlackReplyVariant` 类型（添加 `chinese` 和 `style` 字段）
2. 更新 Store 状态模型
3. 扩展 `ConversationMessage` 类型

### 阶段 2：后端 API 开发（2-3h）
4. 新增 `/api/slack/refine-version` 端点
5. 确保现有 API 返回完整的 `SlackReplyVariant` 数据

### 阶段 3：VersionCard 组件增强（3-4h）
6. 添加编辑状态管理（isEditing, editedChinese, isSaving）
7. 实现卡片内编辑 UI（Textarea + 保存/取消按钮）
8. 集成 `useRefineVersion` hook
9. 添加视觉状态（编辑中高亮、保存中半透明）

### 阶段 4：主界面调整（2-3h）
10. 更新 `ReplyWorkspace` 组件（显示中文内容）
11. 更新 `index.tsx` 主逻辑（处理编辑中点击重新生成）
12. 调整输入框占位符文案

### 阶段 5：视觉美学优化（4-5h）
13. 导入字体（Playfair Display, IBM Plex Sans, Noto Serif SC, JetBrains Mono）
14. 定义 CSS 变量（Editorial 风格色彩方案）
15. 重构版本卡片样式（慷慨留白、细边框、柔和阴影）
16. 添加动效（淡入动画、展开过渡、悬停效果）
17. 添加背景纹理（纸张质感）

### 阶段 6：测试和优化（2-3h）
18. 端到端测试（两个场景 + 三种调整方式）
19. 边界情况测试（并发编辑、空内容、加载状态）
20. 样式细节打磨

**总预估时间**: 15-21 小时

## 技术细节

### 样式设计（Editorial/Magazine 风格）

#### 字体系统
```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-display: 'Playfair Display', serif;
  --font-body: 'IBM Plex Sans', sans-serif;
  --font-chinese: 'Noto Serif SC', serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

#### 色彩方案
```css
:root {
  --color-primary: #1a2332;        /* 深墨蓝 - 主要文字 */
  --color-secondary: #f5f1e8;      /* 暖米色 - 背景 */
  --color-accent: #d4a574;         /* 金色 - 强调和交互 */
  --color-muted: #8b8680;          /* 灰褐色 - 次要文字 */
  --color-border: #e0dcd3;         /* 浅褐色 - 边框 */
  --color-surface: #ffffff;        /* 纯白 - 卡片背景 */
}
```

#### 版本卡片样式
```css
.version-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(26, 35, 50, 0.04);
  transition: all 300ms ease-out;
}

.version-card.editing {
  border-color: var(--color-accent);
  box-shadow: 0 4px 16px rgba(212, 165, 116, 0.15);
  transform: scale(1.02);
}

.version-card.saving {
  opacity: 0.6;
}

.style-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
  background: transparent;
  padding: 4px 12px;
  border-radius: 4px;
}
```

#### 气泡样式
```css
.bubble-them {
  background: hsl(var(--muted));
  border-radius: 16px 16px 16px 4px;
  max-width: 70%;
  align-self: flex-start;
  padding: 16px 20px;
}

.bubble-me {
  background: var(--color-primary);
  color: var(--color-surface);
  border-radius: 16px 16px 4px 16px;
  max-width: 70%;
  align-self: flex-end;
  padding: 16px 20px;
}
```

#### 动效设计
```css
/* 版本卡片淡入 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.version-card:nth-child(1) {
  animation: fadeInUp 400ms ease-out 0ms both;
}

.version-card:nth-child(2) {
  animation: fadeInUp 400ms ease-out 100ms both;
  margin-left: 16px; /* 不对称布局 */
}

.version-card:nth-child(3) {
  animation: fadeInUp 400ms ease-out 200ms both;
}

/* 按钮悬停效果 */
.button-primary {
  position: relative;
  overflow: hidden;
}

.button-primary::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--color-accent);
  transition: width 200ms ease-out;
}

.button-primary:hover::after {
  width: 100%;
}

/* 保存成功反馈 */
@keyframes successPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 2px 8px rgba(26, 35, 50, 0.04);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 4px 20px rgba(212, 165, 116, 0.3);
  }
}

.version-card.save-success {
  animation: successPulse 500ms ease-out;
}
```

#### 背景纹理
```css
.workspace-container {
  background: var(--color-secondary);
  position: relative;
}

.workspace-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
}
```

### 关键交互细节

1. **输入框的智能状态**
   - 占位符文案：`"粘贴对方的英文消息，或输入你想说的中文..."`
   - 不再根据内容动态变化提示（统一提示更简洁）
   - 生成后清空输入框，让用户可以输入新内容

2. **按钮文案变化**
   - 初始状态："生成回复"
   - 已有版本："重新生成"
   - 生成中："生成中..." (禁用)

3. **版本卡片编辑逻辑**
   - 点击"编辑"按钮 → 卡片展开，中文区域变为 Textarea
   - 用户修改中文 → 点击"保存" → 调用 `/api/slack/refine-version`
   - 保存成功 → 只更新该版本的英文翻译，其他版本不变
   - 风格标签保持显示（虽然内容已被用户修改）

4. **并发编辑处理**
   - 允许同时编辑多个版本卡片（每个卡片独立状态）
   - 用户编辑版本时点击"重新生成" → 关闭所有编辑状态，替换所有版本

5. **"复制"按钮的用途**
   - 用户想复制但不想加入对话历史
   - 或者想在外部修改后再发送

### 边界情况处理

- **API 调用失败：** 显示 toast 错误提示，保留用户输入，卡片保持编辑状态
- **空内容：** 
  - 输入框为空时，禁用"生成"按钮
  - 版本卡片编辑时，中文为空或仅空格，禁用"保存"按钮
- **生成中：** 
  - 禁用输入框
  - 禁用所有版本卡片的编辑按钮
  - 生成按钮显示 spinner
- **选择版本后：** 立即清空工作区（currentInput 和 currentVersions）
- **编辑中点击重新生成：** 关闭所有卡片的编辑状态，然后执行生成逻辑

### VersionCard 组件状态机

```typescript
interface VersionCardState {
  isEditing: boolean;        // 是否处于编辑状态
  editedChinese: string;     // 编辑中的中文内容
  isSaving: boolean;         // 是否正在保存
}

// 状态转换：
// 显示状态 --[点击编辑]--> 编辑状态
// 编辑状态 --[点击取消]--> 显示状态
// 编辑状态 --[点击保存]--> 保存中状态 --[API成功]--> 显示状态
// 保存中状态 --[API失败]--> 编辑状态（显示错误）
```

## 预期效果

- ✅ **交互流程清晰**：对话历史 + 工作区，符合聊天工具直觉
- ✅ **功能灵活**：支持三种调整方式（直接选择、重新生成、卡片内编辑）
- ✅ **视觉清晰**：气泡样式明确区分对方和我的消息
- ✅ **精细控制**：卡片内编辑允许用户微调单个版本，无需重新生成所有版本
- ✅ **视觉独特**：Editorial/Magazine 风格，使用独特字体和精致排版，避免通用 AI 界面感
- ✅ **动效流畅**：版本卡片淡入、编辑展开、保存反馈等动效提升体验
- ✅ **两个场景统一**：我发起和对方发起使用完全相同的界面和交互逻辑

## 成功标准

### 功能完整性
- ✅ 用户可以在版本卡片内直接编辑中文
- ✅ 保存后只更新该版本的英文翻译
- ✅ 输入框可以随时重新生成所有版本
- ✅ 两个场景（我发起/对方发起）使用相同交互
- ✅ 对话历史正确记录消息和翻译

### 用户体验
- ✅ 交互流程清晰，无需学习即可理解
- ✅ 编辑和重新生成的区别明确
- ✅ 加载和错误状态有清晰反馈
- ✅ 视觉风格独特，有记忆点
- ✅ 动效自然流畅，不卡顿

### 技术质量
- ✅ 代码结构清晰，组件职责单一
- ✅ 类型定义完整，无 TypeScript 错误
- ✅ API 调用有完善的错误处理
- ✅ 动画性能良好，无卡顿
- ✅ 响应式布局适配不同屏幕尺寸

## 实现优先级

### P0（核心功能）
1. VersionCard 编辑状态和保存逻辑
2. 新增 `/api/slack/refine-version` API
3. 输入框重新生成时关闭所有编辑状态
4. 基础错误处理和加载状态
5. SlackReplyVariant 类型扩展（chinese, style 字段）

### P1（视觉优化）
1. 字体导入和 CSS 变量定义
2. 版本卡片样式重构（Editorial 风格）
3. 输入框和按钮样式优化
4. 页面整体布局调整（留白和间距）
5. 气泡样式优化

### P2（动效增强）
1. 版本卡片淡入动画
2. 编辑状态展开过渡
3. 按钮悬停效果
4. 保存成功反馈动画

### P3（细节打磨）
1. 背景纹理添加
2. 风格标签样式精修
3. 响应式布局优化
4. 无障碍支持（ARIA 标签）
