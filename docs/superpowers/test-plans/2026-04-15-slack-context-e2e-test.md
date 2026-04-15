# Slack 对话上下文功能 - 端到端测试计划

**日期**: 2026-04-15  
**功能**: Slack 对话历史上下文支持  
**测试类型**: 手动端到端测试

---

## 测试环境准备

### 1. 启动后端服务

```bash
cd C:\Users\DELL\Desktop\translation_agent
python -m uvicorn src.api.app:app --reload --port 54321
```

**验证点**:
- 服务启动成功，显示 "Application startup complete"
- 访问 http://localhost:54321/docs 可以看到 API 文档
- `/slack/process` 和 `/slack/compose` 端点存在

### 2. 启动前端服务

在新终端窗口：

```bash
cd C:\Users\DELL\Desktop\translation_agent\web\frontend
npm run dev
```

**验证点**:
- 前端启动成功，显示本地访问地址（通常是 http://localhost:5173）
- 浏览器打开后可以看到应用界面
- 导航到 Slack 功能页面

### 3. 检查网络连接

打开浏览器开发者工具（F12）:
- Network 标签页准备好监控 API 请求
- Console 标签页检查是否有错误

---

## 测试场景

### 场景 1: 对方发起对话（基础流程）

**目标**: 验证接收对方消息、生成回复、自动加入历史的完整流程

**步骤**:

1. 在左栏"对方的话"输入框粘贴：
   ```
   Hey, about the PR you submitted yesterday
   ```

2. 点击"英译中 + 建议回复"按钮

3. **验证点**:
   - [ ] 对话历史区域出现，显示 `[对方] Hey, about the PR you submitted yesterday`
   - [ ] 左栏显示中文翻译
   - [ ] 显示 A/B/C 三个建议回复，每个都有英文和中文
   - [ ] 建议回复内容合理（例如询问具体问题、确认收到等）

4. 选择建议回复 B 并点击复制

5. **验证点**:
   - [ ] Toast 提示"已复制并加入对话历史"
   - [ ] 对话历史区域新增 `[我] <选择的回复内容>`
   - [ ] 左栏输入框和结果区域清空

6. **网络验证**:
   - 打开 Network 标签，找到 `/slack/process` 请求
   - 查看 Request Payload，确认包含 `conversation_history: []`（第一次为空）
   - 查看 Response，确认返回了 `translation` 和 `suggested_replies`

---

### 场景 2: 我发起对话（反向流程）

**目标**: 验证从中文草稿生成英文版本并加入历史

**步骤**:

1. 点击"清空对话"按钮清空历史

2. 在右栏"我想说的话"输入框输入：
   ```
   关于那个 PR 我有个问题想问一下
   ```

3. 点击"生成英文版本"按钮

4. **验证点**:
   - [ ] 显示 A/B/C 三个英文版本
   - [ ] 版本 A 最随意（例如 "Got a question about that PR"）
   - [ ] 版本 B 标准职场风格（例如 "I have a question about that PR"）
   - [ ] 版本 C 稍正式（例如 "I'd like to ask a question about that PR"）

5. 选择版本 B 并点击复制

6. **验证点**:
   - [ ] Toast 提示"已复制并加入对话历史"
   - [ ] 对话历史区域显示 `[我] <英文版本 B 的内容>`
   - [ ] 右栏输入框清空

7. 在左栏输入对方的回复：
   ```
   Sure, what's the question?
   ```

8. 点击"英译中 + 建议回复"

9. **验证点**:
   - [ ] 对话历史区域显示两条消息（我的 + 对方的）
   - [ ] 建议回复基于上下文生成（例如提到具体问题，而不是泛泛的回复）

10. **网络验证**:
    - 查看第二次 `/slack/process` 请求
    - Request Payload 应包含 `conversation_history` 数组，有一条 `role: "me"` 的消息

---

### 场景 3: 批量粘贴多条消息

**目标**: 验证一次性粘贴多行消息的拆分和处理

**步骤**:

1. 清空对话历史

2. 在左栏输入多行消息（模拟从 Slack 复制多条）：
   ```
   Hey there
   I reviewed your code
   Looks good overall
   Just a few minor comments
   ```

3. 点击"英译中 + 建议回复"

4. **验证点**:
   - [ ] 对话历史区域显示 4 条 `[对方]` 消息
   - [ ] 每条消息独立显示，内容正确
   - [ ] 翻译和建议基于最后一条消息（"Just a few minor comments"）
   - [ ] 建议回复考虑了整体上下文（例如感谢 review、询问具体意见等）

5. **网络验证**:
   - Request Payload 的 `message` 字段应该是最后一条："Just a few minor comments"
   - `conversation_history` 应该为空（因为是第一次调用）

---

### 场景 4: 对话历史管理 - 编辑消息

**目标**: 验证编辑历史消息的功能

**步骤**:

1. 确保对话历史中有至少 2 条消息

2. 点击第一条消息的内容区域

3. **验证点**:
   - [ ] 消息进入编辑模式，显示 textarea
   - [ ] textarea 中显示当前消息内容
   - [ ] 显示"保存"和"取消"按钮

4. 修改消息内容，例如改为：
   ```
   Modified message content
   ```

5. 点击"保存"按钮

6. **验证点**:
   - [ ] 消息内容更新为新内容
   - [ ] 退出编辑模式
   - [ ] 消息仍然保持原有的角色标签（[我] 或 [对方]）

7. 再次点击消息，点击"取消"按钮

8. **验证点**:
   - [ ] 退出编辑模式
   - [ ] 消息内容未改变

---

### 场景 5: 对话历史管理 - 删除消息

**目标**: 验证删除单条消息的功能

**步骤**:

1. 确保对话历史中有至少 3 条消息

2. 将鼠标悬停在第二条消息上

3. **验证点**:
   - [ ] 消息右侧出现 [×] 删除按钮（hover 时显示）

4. 点击 [×] 按钮

5. **验证点**:
   - [ ] 该消息从列表中移除
   - [ ] 其他消息保持不变
   - [ ] 消息顺序正确（第一条和第三条仍然存在）

---

### 场景 6: 对话历史管理 - 清空对话

**目标**: 验证清空所有历史的功能

**步骤**:

1. 确保对话历史中有多条消息

2. 点击对话历史区域右上角的"清空对话"按钮

3. **验证点**:
   - [ ] 所有消息被清空
   - [ ] 对话历史区域消失（因为没有消息时不显示）
   - [ ] Toast 提示"对话历史已清空"

4. 在左栏输入新消息并分析

5. **验证点**:
   - [ ] 对话历史区域重新出现
   - [ ] 只显示新添加的消息
   - [ ] 之前的历史确实已清空

---

### 场景 7: 折叠/展开对话历史

**目标**: 验证对话历史的折叠展开功能

**步骤**:

1. 确保对话历史中有至少 3 条消息

2. 点击对话历史区域标题"对话历史 (N 条消息)"

3. **验证点**:
   - [ ] 消息列表折叠，只显示标题栏
   - [ ] 图标从向上箭头变为向下箭头
   - [ ] 标题仍显示消息数量

4. 再次点击标题

5. **验证点**:
   - [ ] 消息列表展开，显示所有消息
   - [ ] 图标从向下箭头变为向上箭头

6. 在折叠状态下添加新消息

7. **验证点**:
   - [ ] 消息数量更新（例如从 3 变为 4）
   - [ ] 列表保持折叠状态

---

### 场景 8: 上下文连贯性验证

**目标**: 验证 LLM 确实使用了对话历史生成上下文相关的回复

**步骤**:

1. 清空对话历史

2. 右栏输入：
   ```
   我们下周一开会讨论这个设计方案
   ```

3. 生成英文版本，选择版本 B 并复制（加入历史）

4. 左栏输入对方回复：
   ```
   Sounds good, what time works for you?
   ```

5. 点击"英译中 + 建议回复"

6. **验证点**:
   - [ ] 建议回复提到具体时间（例如 "How about 2pm?" 或 "10am works for me"）
   - [ ] 回复延续了"会议"这个话题
   - [ ] 不是泛泛的回复（如果没有上下文，可能只会说 "Let me check"）

7. 选择一个回复并复制

8. 左栏输入：
   ```
   Perfect, I'll send a calendar invite
   ```

9. 点击"英译中 + 建议回复"

10. **验证点**:
    - [ ] 建议回复表示确认或感谢（例如 "Thanks!" 或 "Sounds good"）
    - [ ] 回复简短，因为对话接近结束
    - [ ] 不会再问时间或会议细节（因为已经确定）

11. **网络验证**:
    - 查看最后一次 `/slack/process` 请求
    - `conversation_history` 应包含至少 3 条消息
    - 消息角色交替（me, them, me, them）

---

### 场景 9: 刷新页面行为

**目标**: 验证会话级保存（刷新清空）

**步骤**:

1. 确保对话历史中有多条消息

2. 刷新浏览器页面（F5 或 Ctrl+R）

3. **验证点**:
   - [ ] 页面重新加载
   - [ ] 对话历史区域不显示（因为已清空）
   - [ ] 左右栏输入框为空
   - [ ] 没有显示之前的翻译或建议

4. **说明**: 这是预期行为，对话历史是会话级的，不持久化到 localStorage

---

### 场景 10: 向后兼容性验证

**目标**: 验证不传 conversation_history 参数时后端仍正常工作

**步骤**:

1. 使用 API 测试工具（Postman、curl 或浏览器 Console）

2. 发送请求到 `/slack/process`（不带 conversation_history）:

```bash
curl -X POST http://localhost:54321/slack/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you review my PR?"}'
```

或在浏览器 Console 中：

```javascript
fetch('http://localhost:54321/slack/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: "Can you review my PR?" })
}).then(r => r.json()).then(console.log)
```

3. **验证点**:
   - [ ] 请求成功返回 200 状态码
   - [ ] 返回包含 `translation` 和 `suggested_replies`
   - [ ] 建议回复合理（无状态模式）

4. 发送请求到 `/slack/compose`（不带 conversation_history）:

```bash
curl -X POST http://localhost:54321/slack/compose \
  -H "Content-Type: application/json" \
  -d '{"content": "我明天会完成这个任务"}'
```

5. **验证点**:
   - [ ] 请求成功返回 200 状态码
   - [ ] 返回包含 `versions` 数组（A/B/C 三个版本）

---

### 场景 11: 错误处理

**目标**: 验证各种错误情况的处理

**步骤 11.1: 空消息**

1. 左栏输入框留空
2. 点击"英译中 + 建议回复"
3. **验证点**:
   - [ ] 按钮无响应或显示错误提示
   - [ ] 不会发送 API 请求

**步骤 11.2: 网络错误**

1. 停止后端服务（Ctrl+C）
2. 在左栏输入消息并点击分析
3. **验证点**:
   - [ ] Toast 显示错误提示（例如"生成失败，请重试"）
   - [ ] 不会崩溃或卡住
   - [ ] 可以重新启动后端后重试

**步骤 11.3: LLM 返回格式错误**

（这个需要模拟，可以通过修改后端代码临时返回错误格式）

---

## 自动化检查

虽然主要是手动测试，但可以运行以下自动化检查：

### 1. 类型检查

```bash
cd C:\Users\DELL\Desktop\translation_agent\web\frontend
npm run build
```

**验证点**:
- [ ] TypeScript 编译无错误
- [ ] 所有类型定义正确

### 2. 后端类型检查

```bash
cd C:\Users\DELL\Desktop\translation_agent
python -m mypy src/api/routers/slack_models.py
python -m mypy src/api/routers/slack_process.py
python -m mypy src/api/routers/slack_compose.py
```

**验证点**:
- [ ] Mypy 检查通过，无类型错误

### 3. Prompt 模板占位符检查

```bash
cd C:\Users\DELL\Desktop\translation_agent
grep "conversation_history_section" src/prompts/slack_process.txt
grep "conversation_history_section" src/prompts/slack_compose.txt
```

**验证点**:
- [ ] 两个文件都包含 `{conversation_history_section}` 占位符
- [ ] 占位符位置正确（在 context_section 之后，message/content 之前）

### 4. 数据模型一致性检查

手动对比：
- 前端 `ConversationMessage` 类型（`web/frontend/src/shared/types/index.ts`）
- 后端 `ConversationMessage` 模型（`src/api/routers/slack_models.py`）

**验证点**:
- [ ] `role` 字段类型一致（前端 `'them' | 'me'`，后端 `Literal["them", "me"]`）
- [ ] `content` 字段都是 string
- [ ] 前端额外的 `id` 和 `timestamp` 字段不会发送到后端（只用于 UI）

---

## 测试检查清单

### 功能完整性

- [ ] 对方发起对话流程正常
- [ ] 我发起对话流程正常
- [ ] 批量粘贴多条消息正常拆分
- [ ] 编辑历史消息功能正常
- [ ] 删除单条消息功能正常
- [ ] 清空对话功能正常
- [ ] 折叠/展开功能正常
- [ ] 刷新页面清空历史
- [ ] 向后兼容（不传 conversation_history）

### 上下文连贯性

- [ ] LLM 生成的回复考虑了对话历史
- [ ] 多轮对话保持话题连贯
- [ ] 建议回复不重复之前说过的内容

### UI/UX

- [ ] 对话历史区域布局合理
- [ ] 消息角色标签清晰（[我] / [对方]）
- [ ] Hover 效果正常（删除按钮显示）
- [ ] Toast 提示信息准确
- [ ] 加载状态显示（按钮 loading）
- [ ] 响应式布局（不同屏幕尺寸）

### 网络和性能

- [ ] API 请求参数正确
- [ ] API 响应格式正确
- [ ] 网络错误处理正常
- [ ] 20 条消息的历史传输无明显延迟

### 代码质量

- [ ] TypeScript 类型检查通过
- [ ] Python 类型检查通过
- [ ] Prompt 模板占位符正确
- [ ] 数据模型前后端一致

---

## 已知限制和注意事项

1. **会话级保存**: 对话历史不持久化，刷新页面会清空。这是设计决策，符合需求。

2. **历史长度**: 前端不限制历史长度，依赖 LLM 的 context window。如果超限，会返回错误。

3. **复制后未发送**: 如果用户复制回复后没有实际发送，历史会不准确。用户可以手动删除。

4. **多行拆分**: 按 `\n` 拆分，空行自动过滤。如果消息本身包含换行，会被拆分成多条。

5. **网络依赖**: 需要 Gemini API 可用。如果出现 SSL 错误（如 MEMORY.md 中提到的），需要先解决网络问题。

---

## 测试报告模板

测试完成后，填写以下报告：

```markdown
# Slack 对话上下文功能测试报告

**测试日期**: 2026-04-15  
**测试人员**: [姓名]  
**环境**: Windows 11, Python 3.14, Node.js [版本]

## 测试结果总览

- 总测试场景: 11
- 通过: [ ]
- 失败: [ ]
- 阻塞: [ ]

## 场景测试结果

| 场景 | 状态 | 备注 |
|------|------|------|
| 场景 1: 对方发起对话 | ✅/❌ | |
| 场景 2: 我发起对话 | ✅/❌ | |
| 场景 3: 批量粘贴 | ✅/❌ | |
| 场景 4: 编辑消息 | ✅/❌ | |
| 场景 5: 删除消息 | ✅/❌ | |
| 场景 6: 清空对话 | ✅/❌ | |
| 场景 7: 折叠展开 | ✅/❌ | |
| 场景 8: 上下文连贯性 | ✅/❌ | |
| 场景 9: 刷新页面 | ✅/❌ | |
| 场景 10: 向后兼容 | ✅/❌ | |
| 场景 11: 错误处理 | ✅/❌ | |

## 发现的问题

### 问题 1: [标题]
- **严重程度**: 高/中/低
- **描述**: 
- **复现步骤**: 
- **预期行为**: 
- **实际行为**: 

## 性能观察

- API 响应时间: 
- 前端渲染性能: 
- 内存使用: 

## 建议

1. 
2. 

## 结论

[ ] 功能可以发布  
[ ] 需要修复问题后重新测试  
[ ] 需要重大改进
```

---

## 快速测试脚本

如果需要快速验证基本功能，可以运行以下最小测试集：

1. 启动服务（后端 + 前端）
2. 场景 1: 对方发起对话（验证基础流程）
3. 场景 3: 批量粘贴（验证拆分逻辑）
4. 场景 8: 上下文连贯性（验证核心功能）
5. 场景 10: 向后兼容（验证不破坏现有功能）

如果这 5 个场景都通过，说明核心功能正常。
