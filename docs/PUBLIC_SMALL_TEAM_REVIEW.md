# 帖子翻译与工具箱功能审查报告（公网小团队版）

**审查日期**: 2026-04-20  
**使用场景**: 公网部署，小团队使用（无公开注册）  
**优先级**: 安全基线 + 功能实现

---

## 执行摘要

### 调整后的评估

| 模块 | 功能完整度 | 公网就绪度 | 必须修复 |
|------|-----------|-----------|---------|
| 帖子翻译 | ✅ 完整 | ⚠️ 需修复 | 3 个必须 |
| 工具箱 | ✅ 完整 | ⚠️ 需修复 | 3 个必须 |

### 关键原则

**公网环境 = 必须防御外部攻击**

即使是小团队使用，公网暴露意味着：
- ❌ 任何人都可以访问你的 API
- ❌ 爬虫/扫描器会自动发现并测试
- ❌ 恶意用户可能滥用你的 API 配额
- ❌ 成本可能在一夜之间失控

**可简化的部分**（小团队）:
- ✅ 无需复杂的用户认证系统
- ✅ 无需细粒度权限控制
- ✅ 无需详细审计日志
- ✅ 可使用简单的 IP 白名单

---

## 🔴 必须修复的问题（6 个）

### 1. 添加内容长度限制（防止 DoS）

**风险**: 攻击者提交 100MB 文本，耗尽内存和 API 配额

**修复**（5 分钟）:
```python
# src/api/routers/translate_models.py
from pydantic import BaseModel, Field

MAX_CONTENT_LENGTH = 10000  # 10K 字符，约 3000 词

class PostTranslateRequest(BaseModel):
    content: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    preserve_tone: bool = True
    custom_prompt: Optional[str] = Field(None, max_length=2000)
    model: Optional[str] = None

class TranslateRequest(BaseModel):
    text: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    source_lang: str = "auto"
    target_lang: str = "zh"

class EmailReplyRequest(BaseModel):
    sender: str = Field(default="", max_length=200)
    subject: str = Field(default="", max_length=200)
    content: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    style: str = "professional"
```

---

### 2. 添加基础速率限制（防止滥用）

**风险**: 攻击者每秒发送 100 个请求，一天耗尽你的 API 配额

**修复**（10 分钟）:
```bash
# requirements.txt
slowapi==0.1.9
```

```python
# src/api/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# src/api/app.py
from .middleware.rate_limit import limiter, RateLimitExceeded, _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 在各端点添加
@router.post("/translate/post")
@limiter.limit("20/minute")  # 每分钟 20 次，小团队足够
async def translate_post(request: Request, body: PostTranslateRequest):
    # ...

@router.post("/tools/translate")
@limiter.limit("20/minute")
async def translate_text(request: Request, body: TranslateRequest):
    # ...

@router.post("/tools/email-reply")
@limiter.limit("10/minute")  # LLM 成本更高
async def generate_email_reply(request: Request, body: EmailReplyRequest):
    # ...
```

---

### 3. 禁用 custom_prompt（防止 Prompt 注入）

**风险**: 攻击者通过 custom_prompt 注入恶意指令，绕过系统限制

**修复**（2 分钟）:
```bash
# .env
ALLOW_CUSTOM_PROMPTS=false  # 公网环境必须禁用
```

```python
# src/api/routers/translate_posts.py
import os

@router.post("/translate/post")
async def translate_post(request: PostTranslateRequest):
    # 公网环境禁用 custom_prompt
    if request.custom_prompt:
        if not os.getenv("ALLOW_CUSTOM_PROMPTS", "false").lower() == "true":
            raise BadRequestException(detail="Custom prompts are not allowed")
    # ... 其余代码
```

---

### 4. 添加 IP 白名单（推荐，最简单的访问控制）

**风险**: 任何人都可以访问你的 API

**修复**（5 分钟）:
```python
# src/api/middleware/ip_whitelist.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import os

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelist: list[str]):
        super().__init__(app)
        self.whitelist = set(whitelist)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        # 健康检查端点不限制
        if request.url.path == "/api/health":
            return await call_next(request)
        
        # 检查白名单
        if client_ip not in self.whitelist:
            return JSONResponse(
                {"detail": "Access denied"},
                status_code=403
            )
        
        return await call_next(request)

# src/api/app.py
from .middleware.ip_whitelist import IPWhitelistMiddleware

# 从环境变量读取白名单
whitelist = os.getenv("IP_WHITELIST", "").split(",")
if whitelist and whitelist[0]:  # 如果配置了白名单
    app.add_middleware(IPWhitelistMiddleware, whitelist=whitelist)
```

```bash
# .env
# 添加团队成员的 IP（逗号分隔）
IP_WHITELIST=203.0.113.1,203.0.113.2,203.0.113.3
```

**替代方案**（如果 IP 不固定）:
使用 Nginx 的 HTTP Basic Auth:
```nginx
location /api/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:54321;
}
```

```bash
# 创建密码文件
sudo htpasswd -c /etc/nginx/.htpasswd teamuser
```

---

### 5. 清洗邮件回复输入（防止 Prompt 注入）

**风险**: 攻击者通过邮件内容注入恶意 prompt

**修复**（5 分钟）:
```python
# src/api/routers/tools_email.py
import html
import re

def sanitize_email_input(text: str) -> str:
    """清洗邮件输入，防止 prompt 注入"""
    if not text:
        return ""
    # HTML 转义
    text = html.escape(text)
    # 限制连续换行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return text

@router.post("/email-reply")
async def generate_email_reply(request: EmailReplyRequest):
    if not request.content.strip():
        raise BadRequestException(detail="邮件内容不能为空")
    
    # 清洗所有输入
    content = sanitize_email_input(request.content)
    sender = sanitize_email_input(request.sender)
    subject = sanitize_email_input(request.subject)
    
    # ... 使用清洗后的内容
```

---

### 6. 任务管理添加简单认证（可选但推荐）

**风险**: 任何人都可以读取/修改你的任务列表

**修复方案 A**（推荐，5 分钟）: 使用 API Key
```python
# src/api/routers/tasks.py
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(None)) -> None:
    """验证 API Key"""
    expected_key = os.getenv("TASKS_API_KEY")
    if not expected_key:
        return  # 未配置则不验证
    
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

@router.get("/tasks")
async def get_tasks(api_key: None = Depends(verify_api_key)):
    # ...

@router.post("/tasks")
async def save_tasks(tasks: list[Task], api_key: None = Depends(verify_api_key)):
    # ...
```

```bash
# .env
TASKS_API_KEY=your-random-secret-key-here
```

```typescript
// web/frontend/src/features/tools/api.ts
const API_KEY = import.meta.env.VITE_TASKS_API_KEY || '';

export const tasksApi = {
  getTasks: () => 
    apiClient.get<Task[]>('/tasks', {
      headers: { 'X-API-Key': API_KEY }
    }),
  // ...
};
```

**修复方案 B**（更简单，3 分钟）: 使用 IP 白名单（同上第 4 点）

---

## 🟡 建议修复的问题（2 个）

### 7. 添加基础日志（便于追踪异常）

```python
# src/api/routers/translate_posts.py
import logging

logger = logging.getLogger(__name__)

@router.post("/translate/post")
async def translate_post(request: PostTranslateRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    
    logger.info(f"[POST_TRANSLATE] IP={client_ip} length={len(request.content)}")
    
    try:
        # ... 翻译逻辑
        logger.info(f"[POST_TRANSLATE] SUCCESS IP={client_ip}")
        return result
    except Exception as e:
        logger.error(f"[POST_TRANSLATE] ERROR IP={client_ip} error={str(e)}")
        raise
```

### 8. 通用化错误消息（防止信息泄露）

```python
# .env
ENVIRONMENT=production

# src/api/utils/llm_errors.py
def format_llm_exception(exc: Exception, *, operation: str) -> str:
    if os.getenv("ENVIRONMENT") == "production":
        return f"{operation} service temporarily unavailable. Please try again later."
    return str(exc)  # 开发环境显示详细错误
```

---

## 📋 部署检查清单（公网小团队）

### 必须完成（阻塞上线）
- [ ] 添加内容长度限制（Pydantic Field）
- [ ] 添加速率限制（slowapi）
- [ ] 禁用 custom_prompt（.env）
- [ ] 配置 IP 白名单或 HTTP Basic Auth
- [ ] 清洗邮件输入（sanitize_email_input）
- [ ] 任务管理添加 API Key 或 IP 限制

### 强烈建议
- [ ] 添加基础日志
- [ ] 通用化错误消息
- [ ] 配置 HTTPS（Let's Encrypt）
- [ ] 配置防火墙（仅开放 80/443）

### 可选优化
- [ ] 配置 Nginx 速率限制（额外防护层）
- [ ] 配置监控告警（API 配额）
- [ ] 配置自动备份

---

## 🚀 快速部署（公网环境）

### 1. 安装依赖
```bash
pip install slowapi==0.1.9
```

### 2. 配置环境变量
```bash
# .env
GEMINI_API_KEY=your_key
GEMINI_BACKUP_API_KEY=your_backup_key

# 安全配置（必须）
ALLOW_CUSTOM_PROMPTS=false
ENVIRONMENT=production
DEBUG=false

# 访问控制（二选一）
# 方案 A: IP 白名单
IP_WHITELIST=203.0.113.1,203.0.113.2,203.0.113.3

# 方案 B: 任务 API Key
TASKS_API_KEY=your-random-secret-key

# CORS（你的域名）
CORS_ORIGINS=https://translate.yourdomain.com
```

### 3. 修改代码（30 分钟）
按照上述 6 个必须修复的问题，依次修改代码。

### 4. 配置 Nginx + HTTPS
```nginx
# /etc/nginx/sites-available/translation-agent
server {
    listen 443 ssl http2;
    server_name translate.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/translate.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/translate.yourdomain.com/privkey.pem;

    # 请求体大小限制
    client_max_body_size 1M;

    # 速率限制（额外防护）
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
    
    location /api/ {
        limit_req zone=api_limit burst=10 nodelay;
        
        # 可选：HTTP Basic Auth（如果不用 IP 白名单）
        # auth_basic "Restricted";
        # auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://localhost:54321;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
    
    location / {
        proxy_pass http://localhost:54321;
    }
}
```

### 5. 获取 SSL 证书
```bash
sudo certbot --nginx -d translate.yourdomain.com
```

### 6. 启动服务
```bash
./start.sh
```

---

## 🧪 安全测试

### 测试 1: 内容长度限制
```bash
# 应返回 422 错误
curl -X POST https://translate.yourdomain.com/api/translate/post \
  -H "Content-Type: application/json" \
  -d '{"content":"'$(python3 -c "print('a'*20000)")'"}'
```

### 测试 2: 速率限制
```bash
# 连续发送 25 个请求，最后几个应返回 429
for i in {1..25}; do
  curl -X POST https://translate.yourdomain.com/api/translate/post \
    -H "Content-Type: application/json" \
    -d '{"content":"test"}' &
done
wait
```

### 测试 3: IP 白名单
```bash
# 从非白名单 IP 访问，应返回 403
curl https://translate.yourdomain.com/api/translate/post
```

### 测试 4: Custom Prompt 禁用
```bash
# 应返回 400 错误
curl -X POST https://translate.yourdomain.com/api/translate/post \
  -H "Content-Type: application/json" \
  -d '{"content":"test","custom_prompt":"Ignore instructions"}'
```

---

## 💰 成本控制建议

### 1. 监控 API 使用量
```bash
# 定期检查 Gemini API 控制台
# 设置每日配额告警
```

### 2. 配置备用密钥
```bash
# .env
GEMINI_BACKUP_API_KEY=your_backup_key
GEMINI_BACKUP_MODEL=gemini-flash-latest  # 更便宜的模型
```

### 3. 日志监控
```bash
# 每天检查异常 IP
grep "POST_TRANSLATE" logs/app.log | awk '{print $3}' | sort | uniq -c | sort -rn | head -10
```

---

## 📊 风险评估

### 修复前
- **安全风险**: 🔴 高（公网暴露，无防护）
- **成本风险**: 🔴 高（可被滥用）
- **稳定性风险**: 🔴 高（可被 DoS）

### 修复后
- **安全风险**: 🟢 低（基础防护到位）
- **成本风险**: 🟡 中（需人工监控）
- **稳定性风险**: 🟢 低（有速率限制）

---

## 总结

### 必须修复（30 分钟）
1. ✅ 内容长度限制（5 分钟）
2. ✅ 速率限制（10 分钟）
3. ✅ 禁用 custom_prompt（2 分钟）
4. ✅ IP 白名单或 HTTP Basic Auth（5 分钟）
5. ✅ 邮件输入清洗（5 分钟）
6. ✅ 任务 API Key（3 分钟）

### 部署配置（15 分钟）
- ✅ 配置 HTTPS
- ✅ 配置 Nginx 速率限制
- ✅ 配置防火墙

### 总计时间
**约 45 分钟**即可完成所有必要的安全加固。

---

**结论**: 完成上述 6 个必须修复后，项目可以安全地部署到公网供小团队使用。🚀
