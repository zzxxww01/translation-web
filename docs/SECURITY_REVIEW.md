# 长文翻译模块安全审查报告

**审查日期**: 2026-04-20  
**审查范围**: `/document` 功能的前后端代码、API 路由、数据持久化、并发控制

---

## 🔴 高危问题

### 1. 路径遍历防护不完整
**位置**: `src/api/routers/projects_paragraphs.py`, `translate_projects.py`

**问题**:
- `validate_path_component()` 仅在部分端点使用（translate_projects.py）
- projects_paragraphs.py 的所有端点（405-612行）**未验证** `project_id`/`section_id`/`paragraph_id`
- 攻击者可构造 `../../etc/passwd` 等路径访问任意文件

**影响**: 
- 可读取服务器任意文件
- 可覆盖项目数据
- 可导致拒绝服务

**修复**:
```python
# 在 projects_paragraphs.py 所有端点开头添加
from .translate_utils import validate_path_component

if not validate_path_component(project_id) or not validate_path_component(section_id):
    raise BadRequestException(detail="Invalid path component")
```

---

### 2. SSE 流未正确清理资源
**位置**: `src/api/routers/translate_projects.py:322-559`

**问题**:
- `translate_with_four_steps()` 在客户端断开时调用 `cancel_translation()`
- 但 `_pending_conflict_events` 和 `_conflict_resolutions` 字典可能泄漏
- 长时间运行的翻译任务可能导致内存泄漏

**影响**:
- 内存持续增长
- 服务器 OOM
- 并发翻译冲突

**修复**:
```python
# 在 finally 块中强制清理
finally:
    _pending_conflict_events.pop(project_id, None)
    _conflict_resolutions.pop(project_id, None)
    BatchTranslationService._release_active_run(project_id)
```

---

### 3. 全局状态竞态条件
**位置**: `src/api/routers/translate_projects.py:40-42`

**问题**:
```python
_pending_conflict_events: Dict[str, Dict[str, asyncio.Event]] = {}
_conflict_resolutions: Dict[str, Dict[str, Any]] = {}
```
- 全局字典无锁保护
- 多个并发请求可能导致数据竞争
- `term_key` 冲突可能导致错误的术语选择

**影响**:
- 翻译结果错误
- 术语冲突解决失败
- 进程崩溃

**修复**:
```python
import threading

_conflict_lock = threading.Lock()

# 所有访问时加锁
with _conflict_lock:
    _pending_conflict_events[project_id] = {}
```

---

## 🟡 中危问题

### 4. 错误信息泄露敏感信息
**位置**: `src/api/routers/projects_paragraphs.py:396-402`

**问题**:
```python
def _to_bad_request(error: Exception, action: str) -> BadRequestException:
    error_msg = str(error)
    # ...
    return BadRequestException(detail=f"{action} failed: {error_msg}")
```
- 直接暴露异常堆栈
- 可能泄露文件路径、API 密钥、内部逻辑

**修复**:
```python
# 生产环境应返回通用错误
if os.getenv("DEBUG") != "true":
    return BadRequestException(detail=f"{action} failed. Please contact support.")
logger.error(f"{action} failed: {error_msg}")  # 仅记录到日志
```

---

### 5. 无请求体大小限制
**位置**: `src/api/app.py:45-48`

**问题**:
```python
class LimitUploadSize(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        return await call_next(request)  # 空实现！
```
- 中间件未实际限制大小
- 攻击者可上传 GB 级文件导致 OOM

**修复**:
```python
MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100MB

class LimitUploadSize(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                return JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=413
                )
        return await call_next(request)
```

---

### 6. 文件写入无原子性保证
**位置**: `src/core/project.py:65-70`

**问题**:
```python
def _write_text(self, path: Path, content: str) -> None:
    tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, path)  # Windows 上可能失败
```
- Windows 上 `os.replace()` 在目标文件被占用时会失败
- 并发写入可能导致数据损坏

**修复**:
```python
import time

def _write_text(self, path: Path, content: str) -> None:
    tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Windows 重试逻辑
    for attempt in range(3):
        try:
            os.replace(tmp_path, path)
            return
        except OSError as e:
            if attempt == 2:
                raise
            time.sleep(0.1 * (attempt + 1))
```

---

## 🟢 低危问题

### 7. 前端 XSS 防护依赖框架
**位置**: `web/frontend/src/features/document/index.tsx`

**问题**:
- React 默认转义 `{}` 内容，但 `dangerouslySetInnerHTML` 未使用
- 术语冲突对话框直接渲染 `currentConflict.term`（714行）
- 如果后端返回恶意 HTML，可能触发 XSS

**建议**:
```typescript
// 添加 DOMPurify 清理
import DOMPurify from 'dompurify';

<strong>&ldquo;{DOMPurify.sanitize(currentConflict.term)}&rdquo;</strong>
```

---

### 8. 缺少 CORS 配置
**位置**: `src/api/app.py`

**问题**:
- 未配置 CORS 中间件
- 云服务器部署时可能无法跨域访问

**修复**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:54321").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 9. 缺少速率限制
**位置**: 所有 API 端点

**问题**:
- 无全局或端点级速率限制
- 攻击者可暴力调用 `/translate` 端点耗尽 API 配额

**建议**:
```python
# 使用 slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/translate")
@limiter.limit("10/minute")
async def translate_paragraph(...):
    ...
```

---

## 📊 数据持久化问题

### 10. 无备份策略
**位置**: `projects/` 目录

**问题**:
- 所有翻译数据存储在本地文件系统
- 无自动备份、版本控制、灾难恢复

**建议**:
```bash
# 添加定时备份脚本
#!/bin/bash
# backup.sh
tar -czf "projects_backup_$(date +%Y%m%d_%H%M%S).tar.gz" projects/
# 上传到云存储（S3/OSS）
```

---

### 11. 并发写入保护不足
**位置**: `src/core/project.py:86-104`

**问题**:
- `_section_locks` 使用 LRU 淘汰策略
- 高并发时可能淘汰正在使用的锁
- 导致数据竞争

**修复**:
```python
# 改用 WeakValueDictionary 自动清理
import weakref

self._section_locks: weakref.WeakValueDictionary[str, threading.RLock] = \
    weakref.WeakValueDictionary()
```

---

## 🔧 生产环境配置

### 12. 敏感信息暴露
**位置**: `.env.example`

**问题**:
- 示例文件包含真实 API 端点（VECTORENGINE_BASE_URL）
- 代理配置可能泄露内网信息

**修复**:
```bash
# .env.example 应使用占位符
VECTORENGINE_BASE_URL=https://your-api-endpoint.com
GEMINI_HTTP_PROXY=http://your-proxy:port
```

---

### 13. 缺少健康检查超时
**位置**: `src/api/app.py:114-116`

**问题**:
```python
async def health_check():
    return {"status": "healthy"}
```
- 未检查数据库连接、LLM 可用性
- 负载均衡器可能将流量路由到故障实例

**建议**:
```python
async def health_check():
    checks = {
        "api": "healthy",
        "llm": await check_llm_health(),
        "storage": check_storage_health(),
    }
    if any(v != "healthy" for v in checks.values()):
        return JSONResponse(checks, status_code=503)
    return checks
```

---

## 🚀 部署前检查清单

### 必须修复（阻塞上线）
- [ ] **修复路径遍历漏洞**（问题 1）
- [ ] **修复 SSE 资源泄漏**（问题 2）
- [ ] **修复全局状态竞态**（问题 3）
- [ ] **实现请求体大小限制**（问题 5）

### 强烈建议
- [ ] 配置 CORS 白名单（问题 8）
- [ ] 添加速率限制（问题 9）
- [ ] 配置自动备份（问题 10）
- [ ] 清理错误信息（问题 4）

### 可选优化
- [ ] 添加前端 XSS 防护（问题 7）
- [ ] 改进文件写入重试（问题 6）
- [ ] 增强健康检查（问题 13）

---

## 📝 GitHub 发布前准备

### 1. 清理敏感信息
```bash
# 检查是否有硬编码密钥
git grep -i "api_key\|secret\|password\|token" -- '*.py' '*.ts' '*.tsx'

# 检查 git 历史
git log --all --full-history --source -- .env
```

### 2. 更新 .gitignore
```gitignore
# 已有配置良好，确保以下已包含
.env
.env.*
!.env.example
projects/*/  # 排除所有项目数据
*.db
*.sqlite
logs/
```

### 3. 添加安全文档
创建 `SECURITY.md`:
```markdown
# 安全策略

## 支持的版本
当前仅支持最新版本的安全更新。

## 报告漏洞
请发送邮件至 security@your-domain.com
请勿公开披露未修复的漏洞。

## 已知限制
- 本项目为内部协作工具，未经过专业安全审计
- 不建议暴露到公网
- 建议在受信任网络内使用
```

### 4. 添加部署文档
创建 `docs/DEPLOYMENT.md`:
```markdown
# 生产部署指南

## 环境要求
- Python 3.10+
- Node.js 18+
- 至少 4GB RAM
- 50GB 磁盘空间（用于项目数据）

## 安全配置
1. 修改默认端口（54321 → 自定义）
2. 配置反向代理（Nginx/Caddy）
3. 启用 HTTPS
4. 配置防火墙规则
5. 定期备份 projects/ 目录

## 监控
- 监控 /api/health 端点
- 设置磁盘空间告警（< 10GB）
- 监控内存使用（> 80% 告警）
```

---

## 总结

**整体评估**: 代码质量良好，但存在 **3 个高危安全问题** 必须在上线前修复。

**优点**:
- 异常处理完善（error_handlers.py）
- 文件写入使用原子操作
- 前端使用 React 自动转义

**主要风险**:
- 路径遍历漏洞可导致任意文件读写
- SSE 流资源泄漏可导致内存耗尽
- 全局状态竞态可导致数据错误

**建议优先级**:
1. **立即修复**: 问题 1, 2, 3, 5
2. **上线前完成**: 问题 4, 8, 9, 10
3. **后续优化**: 问题 6, 7, 11, 13

**预计修复时间**: 2-3 天（包含测试）
