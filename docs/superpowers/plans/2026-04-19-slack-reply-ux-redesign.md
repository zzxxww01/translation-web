# Slack 回复功能 UX 重设计实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Slack 回复功能从混乱的左右两栏重构为清晰的单栏气泡式设计

**Architecture:** 简化状态管理（移除 incoming/draft 分离），创建气泡式对话历史组件和统一的回复工作区组件，使用现有 API 端点

**Tech Stack:** React, TypeScript, Zustand, shadcn/ui, Tailwind CSS

---

## 文件结构

**已完成（阶段 1）：**
- ✅ Modified: `web/frontend/src/features/slack/store.ts` - 简化状态管理

**待创建（阶段 2）：**
- Create: `web/frontend/src/features/slack/components/ConversationBubbles.tsx` - 气泡式对话历史
- Create: `web/frontend/src/features/slack/components/MessageBubble.tsx` - 单个消息气泡
- Create: `web/frontend/src/features/slack/components/ReplyWorkspace.tsx` - 回复工作区
- Create: `web/frontend/src/features/slack/components/VersionCard.tsx` - 单个版本卡片

**待修改（阶段 3）：**
- Modify: `web/frontend/src/features/slack/index.tsx` - 主界面重构

**待删除（阶段 3）：**
- Delete: `web/frontend/src/features/slack/components/RefinementPanel.tsx`
- Delete: `web/frontend/src/features/slack/components/ReplySuggestions.tsx`
- Delete: `web/frontend/src/features/slack/types.ts` (RefinementSession 相关)
- Delete: `src/api/routers/slack_refine.py`
- Delete: `src/prompts/slack_refine.txt`

---

## Task 1: 创建 MessageBubble 组件

**Files:**
- Create: `web/frontend/src/features/slack/components/MessageBubble.tsx`

- [ ] **Step 1: 创建基础 MessageBubble 组件**

```tsx
import { useState } from 'react';
import { Trash2, Edit2, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ConversationMessage } from '../store';

interface MessageBubbleProps {
  message: ConversationMessage;
  onDelete: (id: string) => void;
  onEdit: (id: string, content: string) => void;
}

export function MessageBubble({ message, onDelete, onEdit }: MessageBubbleProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isTranslationExpanded, setIsTranslationExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  const isThemMessage = message.role === 'them';

  const handleSaveEdit = () => {
    if (editContent.trim() !== message.content) {
      onEdit(message.id, editContent.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      className={cn(
        'flex w-full',
        isThemMessage ? 'justify-start' : 'justify-end'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={cn(
          'relative max-w-[70%] rounded-2xl px-4 py-2.5',
          isThemMessage
            ? 'bg-muted text-foreground rounded-bl-sm'
            : 'bg-primary text-primary-foreground rounded-br-sm'
        )}
      >
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full min-h-[60px] p-2 rounded border bg-background text-foreground"
              autoFocus
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSaveEdit}>保存</Button>
              <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>取消</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
            
            {isThemMessage && message.translation && (
              <div className="mt-2 pt-2 border-t border-border/50">
                <button
                  onClick={() => setIsTranslationExpanded(!isTranslationExpanded)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  {isTranslationExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  中文翻译
                </button>
                {isTranslationExpanded && (
                  <div className="mt-1 text-sm opacity-80">{message.translation}</div>
                )}
              </div>
            )}
          </>
        )}

        {isHovered && !isEditing && (
          <div className="absolute -top-8 right-0 flex gap-1 bg-background border rounded-md shadow-sm p-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsEditing(true)}
              className="h-6 w-6 p-0"
            >
              <Edit2 size={14} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDelete(message.id)}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 size={14} />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/features/slack/components/MessageBubble.tsx
git commit -m "feat(slack): add MessageBubble component with edit/delete support"
```

---

## Task 2: 创建 ConversationBubbles 组件

**Files:**
- Create: `web/frontend/src/features/slack/components/ConversationBubbles.tsx`

- [ ] **Step 1: 创建 ConversationBubbles 组件**

```tsx
import { useRef, useEffect } from 'react';
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { MessageBubble } from './MessageBubble';
import type { ConversationMessage } from '../store';

interface ConversationBubblesProps {
  messages: ConversationMessage[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onRemoveMessage: (id: string) => void;
  onUpdateMessage: (id: string, content: string) => void;
  onClearAll: () => void;
}

export function ConversationBubbles({
  messages,
  isCollapsed,
  onToggleCollapse,
  onRemoveMessage,
  onUpdateMessage,
  onClearAll,
}: ConversationBubblesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && !isCollapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isCollapsed]);

  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">对话历史</h3>
          {messages.length > 0 && (
            <span className="text-xs text-muted-foreground">
              ({messages.length} 条消息)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onClearAll}
              className="h-8 text-xs"
            >
              <Trash2 size={14} className="mr-1" />
              清空
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={onToggleCollapse}
            className="h-8 w-8 p-0"
          >
            {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </Button>
        </div>
      </div>

      {!isCollapsed && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[400px]"
        >
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              暂无对话历史
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onDelete={onRemoveMessage}
                onEdit={onUpdateMessage}
              />
            ))
          )}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/features/slack/components/ConversationBubbles.tsx
git commit -m "feat(slack): add ConversationBubbles component with auto-scroll"
```

---

## Task 3: 创建 VersionCard 组件

**Files:**
- Create: `web/frontend/src/features/slack/components/VersionCard.tsx`

- [ ] **Step 1: 创建 VersionCard 组件**

```tsx
import { Copy, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { copyToClipboard } from '@/shared/utils';
import type { SlackReplyVariant } from '@/shared/types';

interface VersionCardProps {
  version: SlackReplyVariant;
  label: string;
  onSelect: () => void;
  disabled?: boolean;
}

export function VersionCard({ version, label, onSelect, disabled }: VersionCardProps) {
  const handleCopyOnly = async () => {
    const ok = await copyToClipboard(version.english);
    if (ok) {
      toast.success('已复制到剪贴板');
    } else {
      toast.error('复制失败');
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="font-medium text-sm text-muted-foreground">{label}</div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopyOnly}
            disabled={disabled}
            className="h-8"
          >
            <Copy size={14} className="mr-1" />
            仅复制
          </Button>
          <Button
            size="sm"
            onClick={onSelect}
            disabled={disabled}
            className="h-8"
          >
            <Send size={14} className="mr-1" />
            选择并发送
          </Button>
        </div>
      </div>
      <div className="text-sm whitespace-pre-wrap break-words bg-muted/50 rounded p-3">
        {version.english}
      </div>
      {version.chinese && (
        <div className="mt-2 text-xs text-muted-foreground">
          中文: {version.chinese}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/features/slack/components/VersionCard.tsx
git commit -m "feat(slack): add VersionCard component with copy and select actions"
```

---

## Task 4: 创建 ReplyWorkspace 组件

**Files:**
- Create: `web/frontend/src/features/slack/components/ReplyWorkspace.tsx`

- [ ] **Step 1: 创建 ReplyWorkspace 组件**

```tsx
import { Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { VersionCard } from './VersionCard';
import type { SlackReplyVariant } from '@/shared/types';

interface ReplyWorkspaceProps {
  currentInput: string;
  currentVersions: SlackReplyVariant[];
  isGenerating: boolean;
  onInputChange: (value: string) => void;
  onGenerate: () => void;
  onSelectVersion: (version: SlackReplyVariant) => void;
}

export function ReplyWorkspace({
  currentInput,
  currentVersions,
  isGenerating,
  onInputChange,
  onGenerate,
  onSelectVersion,
}: ReplyWorkspaceProps) {
  const hasVersions = currentVersions.length > 0;
  const buttonText = isGenerating
    ? '生成中...'
    : hasVersions
    ? '重新生成'
    : '生成回复';

  return (
    <Card className="p-6 space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">📝 输入中文回复</label>
        <Textarea
          value={currentInput}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="输入你想说的中文内容..."
          className="min-h-[100px] resize-none"
          disabled={isGenerating}
        />
        <Button
          onClick={onGenerate}
          disabled={!currentInput.trim() || isGenerating}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="mr-2 animate-spin" />
              {buttonText}
            </>
          ) : (
            <>
              <Sparkles size={16} className="mr-2" />
              {buttonText}
            </>
          )}
        </Button>
      </div>

      {hasVersions && (
        <div className="space-y-3">
          <div className="text-sm font-medium">💡 生成的版本</div>
          {currentVersions.map((version, index) => (
            <VersionCard
              key={version.english}
              version={version}
              label={String.fromCharCode(65 + index)}
              onSelect={() => onSelectVersion(version)}
              disabled={isGenerating}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/features/slack/components/ReplyWorkspace.tsx
git commit -m "feat(slack): add ReplyWorkspace component with input and version display"
```

---

## Task 5: 重写 SlackFeature 主组件

**Files:**
- Modify: `web/frontend/src/features/slack/index.tsx`

- [ ] **Step 1: 重写主组件逻辑**

完整替换 `web/frontend/src/features/slack/index.tsx` 内容为：

```tsx
import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import type { SlackReplyVariant } from '@/shared/types';
import { ConversationBubbles } from './components/ConversationBubbles';
import { ReplyWorkspace } from './components/ReplyWorkspace';
import { useComposeReply, useGenerateReply } from './hooks';
import { useSlackWorkspaceStore } from './store';

export function SlackFeature() {
  const processMutation = useGenerateReply();
  const composeMutation = useComposeReply();

  const {
    currentInput,
    currentVersions,
    isGenerating,
    conversationMessages,
    isHistoryCollapsed,
    selectedModel,
    setCurrentInput,
    setCurrentVersions,
    setGenerating,
    clearWorkspace,
    addMessage,
    removeMessage,
    updateMessage,
    clearConversation,
    toggleHistoryCollapse,
    setSelectedModel,
  } = useSlackWorkspaceStore();

  const handleGenerate = async () => {
    const input = currentInput.trim();
    if (!input) return;

    setGenerating(true);

    try {
      // 检测是否是英文（对方消息场景）
      const isEnglish = /^[a-zA-Z\s\d\p{P}]+$/u.test(input);

      if (isEnglish) {
        // 场景 1：对方发起 - 翻译并生成建议回复
        const result = await processMutation.mutateAsync({
          message: input,
          conversation_history: conversationMessages,
          model: selectedModel || undefined,
        });

        // 对方消息加入历史
        addMessage('them', input, result.translation);

        // 显示建议回复
        setCurrentVersions(result.suggested_replies ?? []);

        // 清空输入框，让用户可以输入中文调整
        setCurrentInput('');
      } else {
        // 场景 2：我发起 / 调整建议 - 中译英
        const result = await composeMutation.mutateAsync({
          content: input,
          conversation_history: conversationMessages,
          model: selectedModel || undefined,
        });

        setCurrentVersions(
          result.versions.map((v: SlackReplyVariant) => ({
            ...v,
            chinese: v.chinese || input,
          }))
        );
      }
    } catch (error) {
      toast.error('生成失败，请重试');
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectVersion = (version: SlackReplyVariant) => {
    // 加入对话历史
    addMessage('me', version.english);

    // 清空工作区
    clearWorkspace();

    toast.success('已加入对话历史');
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-5xl flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Slack 回复助手</h2>
          <p className="text-sm text-muted-foreground">
            粘贴对方英文或输入中文，生成专业回复
          </p>
        </div>
        <div className="w-64">
          <label className="block text-xs text-muted-foreground mb-1.5">
            选择模型
          </label>
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
            className="h-9 text-sm"
            disabled={isGenerating}
          />
        </div>
      </div>

      {/* 对话历史 */}
      <ConversationBubbles
        messages={conversationMessages}
        isCollapsed={isHistoryCollapsed}
        onToggleCollapse={toggleHistoryCollapse}
        onRemoveMessage={removeMessage}
        onUpdateMessage={updateMessage}
        onClearAll={clearConversation}
      />

      {/* 回复工作区 */}
      <ReplyWorkspace
        currentInput={currentInput}
        currentVersions={currentVersions}
        isGenerating={isGenerating}
        onInputChange={setCurrentInput}
        onGenerate={handleGenerate}
        onSelectVersion={handleSelectVersion}
      />
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/features/slack/index.tsx
git commit -m "refactor(slack): rewrite main component with unified workflow"
```

---

## Task 6: 清理旧代码

**Files:**
- Delete: `web/frontend/src/features/slack/components/RefinementPanel.tsx`
- Delete: `web/frontend/src/features/slack/components/ReplySuggestions.tsx`
- Delete: `web/frontend/src/features/slack/components/ConversationHistory.tsx`
- Delete: `web/frontend/src/features/slack/types.ts`
- Delete: `src/api/routers/slack_refine.py`
- Delete: `src/prompts/slack_refine.txt`
- Modify: `src/api/routers/slack.py`

- [ ] **Step 1: 删除前端旧组件**

```bash
git rm web/frontend/src/features/slack/components/RefinementPanel.tsx
git rm web/frontend/src/features/slack/components/ReplySuggestions.tsx
git rm web/frontend/src/features/slack/components/ConversationHistory.tsx
git rm web/frontend/src/features/slack/types.ts
```

- [ ] **Step 2: 删除后端 refine 端点**

```bash
git rm src/api/routers/slack_refine.py
git rm src/prompts/slack_refine.txt
```

- [ ] **Step 3: 从主路由移除 refine router**

修改 `src/api/routers/slack.py`，移除导入和注册：

```python
# 移除这行
from .slack_refine import router as slack_refine_router

# 移除这行
app.include_router(slack_refine_router)
```

- [ ] **Step 4: 提交清理**

```bash
git add src/api/routers/slack.py
git commit -m "refactor(slack): remove unused refinement components and API"
```

---

## Task 7: 端到端测试

- [ ] **Step 1: 启动服务**

```bash
# 后端
python -m uvicorn src.api.main:app --reload

# 前端
cd web/frontend && npm run dev
```

- [ ] **Step 2: 测试场景 1 - 对方发起**

1. 粘贴英文消息到输入框
2. 点击"生成回复"
3. 验证：对方消息加入历史（灰色气泡，靠左，含翻译）
4. 验证：显示 A/B/C 三个建议回复
5. 修改输入框中文
6. 点击"重新生成"
7. 验证：显示新的 A/B/C 版本
8. 点击"选择并发送"
9. 验证：我的回复加入历史（蓝色气泡，靠右），工作区清空

- [ ] **Step 3: 测试场景 2 - 我主动发起**

1. 输入中文
2. 点击"生成回复"
3. 验证：显示 A/B/C 英文版本
4. 点击"仅复制"
5. 验证：复制成功提示，历史不变
6. 点击"选择并发送"
7. 验证：我的回复加入历史，工作区清空

- [ ] **Step 4: 测试边界情况**

1. 空输入 → 生成按钮禁用
2. 生成中 → 所有按钮禁用
3. 编辑历史消息 → 保存成功
4. 删除历史消息 → 删除成功
5. 清空历史 → 全部清空
6. 展开/折叠对话历史 → 正常工作

---

## Task 8: 样式优化

- [ ] **Step 1: 优化气泡样式**

检查 `MessageBubble.tsx`：
- 气泡圆角正确（16px，底部小角 4px）
- 最大宽度 70%
- 悬停效果流畅
- 编辑/删除按钮位置合理

- [ ] **Step 2: 优化响应式布局**

检查主容器：
- 小屏幕单栏布局
- 大屏幕最大宽度 5xl 居中

- [ ] **Step 3: 优化加载状态**

检查 `ReplyWorkspace`：
- 生成中 spinner 动画
- 按钮禁用状态明显

- [ ] **Step 4: 提交样式优化**

```bash
git add web/frontend/src/features/slack/components/*.tsx
git commit -m "style(slack): optimize bubble styles and responsive layout"
```

---

## 自审清单

**规格覆盖：**
- ✅ 单栏气泡式布局
- ✅ 对方消息（灰色，靠左，含翻译）
- ✅ 我的消息（蓝色，靠右）
- ✅ 统一的回复工作区
- ✅ A/B/C 版本显示
- ✅ 选择并发送 / 仅复制
- ✅ 重新生成功能
- ✅ 编辑/删除历史消息
- ✅ 两种场景（对方发起 / 我发起）

**占位符检查：**
- ✅ 无 TBD/TODO
- ✅ 所有代码块完整
- ✅ 所有文件路径明确

**类型一致性：**
- ✅ ConversationMessage 接口统一
- ✅ SlackReplyVariant 类型一致
- ✅ 函数签名匹配

---

## 预估时间

- Task 1-4: 创建新组件 - 3-4h
- Task 5: 重写主组件 - 1-2h
- Task 6: 清理旧代码 - 0.5h
- Task 7: 端到端测试 - 1h
- Task 8: 样式优化 - 1h

**总计**: 6.5-8.5 小时
