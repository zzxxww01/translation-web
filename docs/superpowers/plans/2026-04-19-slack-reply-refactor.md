# Slack 回复功能重构 - 实现计划

## 概述
基于设计文档 `docs/superpowers/specs/2026-04-19-slack-reply-refactor-design.md`，本计划将分 3 个阶段实现多轮调整和手动历史确认功能。

## 阶段 1: 后端基础设施 (约 2-3 小时)

### 1.1 数据模型扩展
**文件**: `src/api/routers/slack_models.py`
- 添加 `SlackRefineRequest` 模型
  - `context_type: Literal["incoming", "draft"]`
  - `original_input: str`
  - `current_result: str`
  - `refinement_instruction: str`
  - `conversation_history: List[ConversationMessage]`
  - `model: str`
- 添加 `SlackRefineResponse` 模型
  - `refined_result: str`
  - `explanation: Optional[str]`

### 1.2 Refine Prompt
**文件**: `src/prompts/slack_refine.txt`
- 创建调整 prompt 模板
- 支持两种上下文：incoming (翻译+建议) / draft (中译英)
- 包含对话历史上下文
- 输出格式：refined_result + explanation

### 1.3 Refine API 端点
**文件**: `src/api/routers/slack_refine.py` (新建)
- `POST /slack/refine` 端点
- 调用 LLM 执行调整
- 复用现有 LLM 调用逻辑 (参考 slack_compose.py)
- 错误处理和日志

**文件**: `src/api/routers/slack.py`
- 注册 `/slack/refine` 路由

### 验收标准
- [ ] 数据模型通过类型检查
- [ ] `/slack/refine` 端点可通过 curl 测试
- [ ] 返回格式符合 SlackRefineResponse

---

## 阶段 2: 前端状态管理 (约 3-4 小时)

### 2.1 类型定义
**文件**: `web/frontend/src/features/slack/types.ts` (新建)
```typescript
export type ContextType = 'incoming' | 'draft';

export interface RefinementVariant {
  id: string;
  content: string;
  explanation?: string;
  timestamp: number;
}

export interface RefinementSession {
  contextType: ContextType;
  originalInput: string;
  variants: RefinementVariant[];
  isRefining: boolean;
}
```

### 2.2 Store 扩展
**文件**: `web/frontend/src/features/slack/store.ts`
- 添加状态字段：
  - `incomingRefinement: RefinementSession | null`
  - `draftRefinement: RefinementSession | null`
- 添加 actions：
  - `startRefinement(contextType, originalInput, initialResult)`
  - `addRefinementVariant(contextType, variant)`
  - `clearRefinement(contextType)`
  - `setRefining(contextType, isRefining)`
  - `confirmToHistory(contextType, variantId)` - 手动添加到历史

### 2.3 API 集成
**文件**: `web/frontend/src/features/slack/api.ts`
- 添加 `refineResult()` 函数
- 类型定义对齐后端 SlackRefineRequest/Response

### 验收标准
- [ ] TypeScript 编译通过
- [ ] Store actions 可在浏览器 devtools 中调用
- [ ] API 函数可发送请求到后端

---

## 阶段 3: UI 组件实现 (约 4-5 小时)

### 3.1 RefinementPanel 组件
**文件**: `web/frontend/src/features/slack/components/RefinementPanel.tsx` (新建)
- Props: `session: RefinementSession`, `onRefine`, `onConfirm`, `onClear`
- 显示所有 variants (时间倒序)
- 每个 variant 卡片：
  - 内容 + 时间戳
  - [✓ 用这个] 按钮 → 触发 `onConfirm(variantId)`
  - 可选 explanation 显示
- 底部输入框 + [继续调整] 按钮
- Loading 状态处理

### 3.2 主界面集成
**文件**: `web/frontend/src/features/slack/index.tsx`
- 左栏 (Incoming)：
  - 原有翻译+建议回复显示
  - 添加 [继续调整] 按钮 → 触发 `startRefinement('incoming', ...)`
  - 条件渲染 `<RefinementPanel session={incomingRefinement} />`
- 右栏 (Draft)：
  - 原有中译英结果显示
  - 添加 [继续调整] 按钮 → 触发 `startRefinement('draft', ...)`
  - 条件渲染 `<RefinementPanel session={draftRefinement} />`
- 移除自动添加历史逻辑，改为手动确认

### 3.3 对话历史改进
**文件**: `web/frontend/src/features/slack/components/ConversationHistory.tsx`
- 保持现有显示逻辑
- 确认手动添加流程正常工作
- (可选) 添加 [撤销] 按钮用于移除最近添加的消息

### 验收标准
- [ ] 左栏可完整走通：复制消息 → 查看翻译 → 继续调整 → 确认加入历史
- [ ] 右栏可完整走通：输入中文 → 查看英文 → 继续调整 → 确认加入历史
- [ ] 切换栏时调整会话正确保留
- [ ] 刷新页面后状态正确清空 (session-only)

---

## 测试计划

### 单元测试
- [ ] `parse_variants()` 函数测试 (后端)
- [ ] Store actions 测试 (前端)

### 集成测试
- [ ] `/slack/refine` 端点 E2E 测试
- [ ] 前端完整流程测试 (Playwright/Cypress)

### 手动测试场景
1. 左栏多轮调整 → 确认第 3 个版本 → 检查历史记录
2. 右栏多轮调整 → 确认第 2 个版本 → 检查历史记录
3. 左栏调整中途切换到右栏 → 返回左栏 → 确认会话保留
4. 刷新页面 → 确认调整会话清空
5. 只复制消息不加历史 → 确认历史为空

---

## 风险和依赖

### 风险
1. **LLM 调整质量** - 需要精心设计 refine prompt，确保调整符合用户意图
2. **状态复杂度** - 两个独立的 RefinementSession 需要仔细管理，避免状态混乱
3. **性能** - 多轮调整可能产生多次 LLM 调用，需要考虑 loading 状态和错误处理

### 依赖
- 现有 LLM 调用基础设施 (src/llm/)
- 现有 Slack 数据模型和 API
- Zustand store 架构

---

## 实施顺序建议
1. **先后端后前端** - 确保 API 可用后再开发 UI
2. **先左栏后右栏** - 左栏逻辑更复杂 (翻译+建议)，先实现可验证架构
3. **增量测试** - 每个阶段完成后立即手动测试，避免积累问题

---

## 预估工时
- 阶段 1 (后端): 2-3 小时
- 阶段 2 (状态): 3-4 小时  
- 阶段 3 (UI): 4-5 小时
- 测试和调试: 2-3 小时
- **总计**: 11-15 小时

---

## 后续优化 (不在本次范围)
- 调整历史持久化 (localStorage)
- 撤销/重做功能
- 快捷键支持
- 调整 prompt 的 A/B 测试
