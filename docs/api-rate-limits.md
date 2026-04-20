# API 速率限制配置

## 概述

本文档记录了所有 API 端点的速率限制配置。速率限制使用 `slowapi` 库实现，基于客户端 IP 地址进行限流。

## 速率限制策略

### 翻译相关端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| POST /api/projects/batch-translate-section | 5/分钟 | 批量翻译章节 |
| POST /api/projects/translate-full-document | 3/分钟 | 全文档翻译 |
| POST /api/projects/translate-with-four-steps | 3/分钟 | 四步翻译流程 |
| POST /api/confirmation/start | 5/分钟 | 启动确认翻译 |
| POST /api/confirmation/confirm | 30/分钟 | 确认段落翻译 |
| POST /api/confirmation/term-update | 30/分钟 | 更新术语 |
| POST /api/confirmation/retranslate | 20/分钟 | 重新翻译段落 |
| GET /api/confirmation/export | 10/分钟 | 导出翻译 |
| GET /api/confirmation/export-bilingual | 10/分钟 | 导出双语文档 |

### 段落翻译端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| POST /api/projects/{id}/paragraphs/batch-translate | 30/分钟 | 批量翻译段落 |
| POST /api/projects/{id}/paragraphs/{index}/translate | 30/分钟 | 翻译单个段落 |
| PUT /api/projects/{id}/paragraphs/{index} | 30/分钟 | 更新段落翻译 |
| POST /api/projects/{id}/paragraphs/{index}/confirm | 30/分钟 | 确认段落 |
| POST /api/projects/{id}/paragraphs/{index}/retranslate | 30/分钟 | 重新翻译 |
| POST /api/projects/{id}/paragraphs/word-meaning | 60/分钟 | 查询词义 |

### 项目管理端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| GET /api/projects | 100/分钟 | 列出所有项目 |
| POST /api/projects | 20/分钟 | 创建项目 |
| GET /api/projects/{id} | 100/分钟 | 获取项目详情 |
| PUT /api/projects/{id} | 20/分钟 | 更新项目 |
| DELETE /api/projects/{id} | 10/分钟 | 删除项目 |

### 术语表端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| GET /api/glossary | 100/分钟 | 获取全局术语表 |
| POST /api/glossary | 60/分钟 | 添加术语 |
| PUT /api/glossary/terms/{original} | 60/分钟 | 更新术语 |
| DELETE /api/glossary/terms/{original} | 60/分钟 | 删除术语 |
| POST /api/glossary/batch | 20/分钟 | 批量操作术语 |
| POST /api/projects/{id}/glossary | 60/分钟 | 添加项目术语 |
| POST /api/projects/{id}/glossary/match | 60/分钟 | 匹配术语 |

### Slack 集成端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| POST /api/slack/refine | 30/分钟 | Slack 消息精炼 |
| POST /api/slack/refine/continue | 30/分钟 | 继续精炼 |
| POST /api/slack/refine/confirm | 30/分钟 | 确认精炼结果 |

### 微信格式化端点

| 端点 | 速率限制 | 说明 |
|------|---------|------|
| POST /api/wechat/format | 100/分钟 | 微信格式化 |

## 实现细节

### 配置文件

速率限制器在 `src/api/middleware/rate_limit.py` 中初始化：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
```

### 使用方式

在路由端点上添加装饰器：

```python
from fastapi import Request
from src.api.middleware.rate_limit import limiter

@router.post("/endpoint")
@limiter.limit("30/minute")
async def endpoint(http_request: Request, ...):
    pass
```

### 参数命名约定

- FastAPI 的 `Request` 参数统一命名为 `http_request`
- 避免与 Pydantic 模型的 `request` 参数冲突
- `http_request` 参数必须是第一个参数（路径参数除外）

## 错误响应

当超过速率限制时，API 返回 429 状态码：

```json
{
  "error": "Rate limit exceeded: 30 per 1 minute"
}
```

## 调整建议

根据实际使用情况，可能需要调整以下端点的限制：

1. **高频查询端点**：如果用户反馈查询受限，可适当提高 GET 端点限制
2. **批量操作端点**：批量操作通常耗时较长，当前限制可能需要根据服务器性能调整
3. **AI 翻译端点**：考虑 AI API 的配额和成本，当前限制较为保守

## 监控建议

建议监控以下指标：

- 429 错误率
- 各端点的请求频率分布
- 单个 IP 的请求模式
- AI API 的使用量和成本
