# 公网小团队部署 - 必须修复的安全问题

## 已完成的修复

### 1. 内容长度限制 ✅
- `src/api/routers/translate_models.py` - 帖子翻译模型
- `src/api/routers/tools_models.py` - 工具箱模型
- 限制：10K 字符（约 3000 词）

### 2. 速率限制 ✅
- `src/api/middleware/rate_limit.py` - 速率限制中间件
- `src/api/app.py` - 注册速率限制
- `src/api/routers/translate_posts.py` - 添加装饰器
- 限制：20 次/分钟（帖子翻译）、10 次/分钟（邮件回复）

### 3. 禁用 custom_prompt ✅
- `src/api/routers/translate_posts.py` - 添加检查逻辑
- 通过环境变量 `ALLOW_CUSTOM_PROMPTS=false` 控制

## 待完成的修复

### 4. 工具箱端点添加速率限制
需要修改以下文件：
- `src/api/routers/tools_translate.py`
- `src/api/routers/tools_email.py`
- `src/api/routers/tools_timezone.py`

### 5. 邮件输入清洗
需要修改：
- `src/api/routers/tools_email.py`

### 6. 访问控制（二选一）
- 方案 A: IP 白名单
- 方案 B: HTTP Basic Auth（Nginx 层）

## 下一步操作

1. 安装依赖：
```bash
pip install slowapi==0.1.9
```

2. 配置环境变量：
```bash
# .env
ALLOW_CUSTOM_PROMPTS=false
ENVIRONMENT=production
```

3. 继续修复剩余端点（工具箱）

4. 配置访问控制（IP 白名单或 Basic Auth）

5. 测试验证
