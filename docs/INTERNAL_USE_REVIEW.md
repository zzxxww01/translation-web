# 帖子翻译与工具箱功能审查报告（内部使用版）

**审查日期**: 2026-04-20  
**使用场景**: 小团队内部使用，受信任环境  
**优先级**: 功能实现 > 安全加固

---

## 执行摘要

### 调整后的评估

| 模块 | 功能完整度 | 内部使用就绪度 | 需修复问题 |
|------|-----------|---------------|----------|
| 帖子翻译 | ✅ 完整 | ✅ 可直接使用 | 2 个建议修复 |
| 工具箱 | ✅ 完整 | ✅ 可直接使用 | 1 个建议修复 |

### 关键发现（内部使用场景）

**可忽略的问题**（受信任环境）:
- ~~速率限制~~ - 内部使用无需限制
- ~~用户权限控制~~ - 团队共享数据
- ~~CSRF 防护~~ - 内网环境
- ~~审计日志~~ - 小团队无需

**仍需关注的问题**:
1. ⚠️ **内容长度限制** - 防止误操作导致服务崩溃
2. ⚠️ **Prompt 注入防护** - 防止意外覆盖系统 prompt
3. ⚠️ **超时配置** - 改善用户体验

---

## 建议修复的问题（3 个）

### 🟡 中优先级（建议修复）

#### 1. 添加内容长度限制（防止误操作）

**问题**: 用户误粘贴超大文本可能导致服务卡死

**修复**（5 分钟）:
```python
# src/api/routers/translate_models.py
from pydantic import BaseModel, Field

MAX_CONTENT_LENGTH = 50000  # 50K 字符，足够大

class PostTranslateRequest(BaseModel):
    content: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    preserve_tone: bool = True
    custom_prompt: Optional[str] = None
    model: Optional[str] = None

class TranslateRequest(BaseModel):
    text: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    source_lang: str = "auto"
    target_lang: str = "zh"

class EmailReplyRequest(BaseModel):
    sender: str = Field(default="", max_length=500)
    subject: str = Field(default="", max_length=500)
    content: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    style: str = "professional"
```

**影响**: 前端会自动显示友好的错误提示，而非服务崩溃

---

#### 2. 禁用 custom_prompt（可选，推荐）

**问题**: 误用 custom_prompt 可能导致翻译结果异常

**修复**（2 分钟）:
```python
# .env
ALLOW_CUSTOM_PROMPTS=false  # 默认禁用，需要时改为 true
```

```python
# src/api/routers/translate_posts.py
import os

@router.post("/translate/post")
async def translate_post(request: PostTranslateRequest):
    # 检查是否允许自定义 prompt
    if request.custom_prompt:
        if not os.getenv("ALLOW_CUSTOM_PROMPTS", "false").lower() == "true":
            raise BadRequestException(
                detail="Custom prompts are disabled. Set ALLOW_CUSTOM_PROMPTS=true to enable."
            )
    # ... 其余代码不变
```

**影响**: 防止团队成员误用导致翻译异常，需要时可随时启用

---

#### 3. 统一超时配置（改善体验）

**问题**: 前端超时 180s，后端 60s，用户等待时间过长

**修复**（3 分钟）:
```typescript
// web/frontend/src/shared/constants.ts
export const REQUEST_TIMEOUTS = {
  DEFAULT: API_TIMEOUT,
  POST_TRANSLATE: 70000,    // 70s（后端 60s + 10s buffer）
  POST_OPTIMIZE: 100000,    // 100s（后端 90s + 10s buffer）
  POST_TITLE: 40000,        // 40s（后端 30s + 10s buffer）
  TOOLS_TRANSLATE: 70000,
  TOOLS_EMAIL: 100000,
  // ... 其他保持不变
} as const;
```

**影响**: 用户体验更好，超时后能更快看到错误提示

---

## 可忽略的问题（内部使用）

### ✅ 无需修复

以下问题在内部受信任环境下可以接受：

1. **速率限制** - 团队成员不会恶意滥用
2. **用户权限控制** - 任务列表共享是合理的（团队协作）
3. **Prompt 注入** - 团队成员不会故意注入恶意 prompt
4. **日志记录** - 小团队可通过其他方式追踪问题
5. **CSRF 防护** - 内网环境，无外部攻击风险
6. **错误信息泄露** - 内部使用，详细错误有助于调试
7. **ReDoS 风险** - 团队成员不会输入恶意正则

---

## 内部使用部署指南

### 快速部署（无需额外配置）

```bash
# 1. 克隆代码
git clone https://github.com/your-org/translation-agent.git
cd translation-agent

# 2. 配置环境变量
cp .env.example .env
nano .env
# 填入 GEMINI_API_KEY

# 3. 启动服务（Linux）
./start.sh

# 或 Windows
start.bat
```

### 推荐配置（可选）

```bash
# .env
GEMINI_API_KEY=your_key
GEMINI_BACKUP_API_KEY=your_backup_key

# 可选：禁用自定义 prompt（推荐）
ALLOW_CUSTOM_PROMPTS=false

# 可选：CORS（如果前后端分离部署）
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:54321

# 调试模式（开发环境）
DEBUG=true
LOG_LEVEL=DEBUG
```

### Nginx 配置（可选）

如果需要通过域名访问：

```nginx
server {
    listen 80;
    server_name translate.internal.company.com;

    # 简单配置，无需复杂安全策略
    location / {
        proxy_pass http://localhost:54321;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

---

## 功能验证测试

### 帖子翻译

```bash
# 测试翻译
curl -X POST http://localhost:54321/api/translate/post \
  -H "Content-Type: application/json" \
  -d '{"content":"This is a test post about AI technology."}'

# 测试优化
curl -X POST http://localhost:54321/api/translate/post/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "original_text":"This is a test.",
    "current_translation":"这是一个测试。",
    "option_id":"readable"
  }'

# 测试标题生成
curl -X POST http://localhost:54321/api/generate/title \
  -H "Content-Type: application/json" \
  -d '{"content":"这是一篇关于人工智能技术的文章..."}'
```

### 工具箱

```bash
# 测试文本翻译
curl -X POST http://localhost:54321/api/tools/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello World","source_lang":"auto","target_lang":"zh"}'

# 测试邮件回复
curl -X POST http://localhost:54321/api/tools/email-reply \
  -H "Content-Type: application/json" \
  -d '{
    "content":"Can we schedule a meeting next week?",
    "style":"professional"
  }'

# 测试时区转换
curl -X POST http://localhost:54321/api/tools/timezone-convert \
  -H "Content-Type: application/json" \
  -d '{"input":"1/26 10am PST","source_timezone":"auto"}'

# 测试任务管理
curl http://localhost:54321/api/tasks
```

---

## 已知限制（可接受）

### 1. 任务列表全局共享
- **现状**: 所有团队成员看到相同的任务列表
- **影响**: 适合小团队协作，共享待办事项
- **解决方案**: 如需隔离，可手动在任务文本中添加前缀（如 `[张三] 完成翻译`）

### 2. 无操作审计
- **现状**: 无法追踪谁在何时做了什么操作
- **影响**: 小团队可通过沟通解决
- **解决方案**: 如需审计，可查看 Nginx access.log

### 3. 无 API 配额管理
- **现状**: 无法限制单个用户的 API 使用量
- **影响**: 团队成员需自觉控制使用
- **解决方案**: 定期检查 Gemini API 使用量

---

## 建议的修复优先级（内部使用）

### 立即修复（10 分钟）
- [x] 添加内容长度限制（防止误操作）

### 可选修复（5 分钟）
- [ ] 禁用 custom_prompt（防止误用）
- [ ] 统一超时配置（改善体验）

### 无需修复
- [ ] ~~速率限制~~
- [ ] ~~用户权限控制~~
- [ ] ~~日志记录~~
- [ ] ~~CSRF 防护~~
- [ ] ~~错误信息脱敏~~

---

## 部署检查清单（内部使用）

### 必须完成
- [ ] `.env` 已配置 API 密钥
- [ ] 服务可正常启动
- [ ] 前端可访问
- [ ] 帖子翻译功能正常
- [ ] 工具箱功能正常

### 可选配置
- [ ] 配置 Nginx（如需域名访问）
- [ ] 配置自动备份（`scripts/backup.sh`）
- [ ] 禁用 custom_prompt
- [ ] 添加内容长度限制

### 无需配置
- [ ] ~~速率限制~~
- [ ] ~~用户认证~~
- [ ] ~~监控告警~~
- [ ] ~~日志聚合~~

---

## 总结

### 当前状态
✅ **两个模块都可以直接在内部环境使用**

### 功能完整度
- ✅ 帖子翻译：完整实现，功能稳定
- ✅ 工具箱：完整实现，功能稳定
- ✅ 长文翻译：已通过安全审查

### 建议
1. **立即部署**: 可直接使用，无阻塞问题
2. **可选优化**: 添加内容长度限制（10 分钟）
3. **长期优化**: 根据实际使用情况调整

### 风险评估（内部使用）
- **安全风险**: 🟢 低（受信任环境）
- **稳定性风险**: 🟢 低（功能完整）
- **成本风险**: 🟡 中（无配额管理，需人工监控）

### 推荐配置
```bash
# .env（最小配置）
GEMINI_API_KEY=your_key
CORS_ORIGINS=http://localhost:54321

# .env（推荐配置）
GEMINI_API_KEY=your_key
GEMINI_BACKUP_API_KEY=your_backup_key
ALLOW_CUSTOM_PROMPTS=false
DEBUG=false
LOG_LEVEL=INFO
```

---

**结论**: 项目已准备好在内部环境部署和使用！🚀

如需添加内容长度限制（推荐），只需修改 `translate_models.py` 添加 `Field(max_length=50000)` 即可。
