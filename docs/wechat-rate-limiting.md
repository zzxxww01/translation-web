# 微信格式化 API 速率限制建议

## 为什么需要速率限制

`/wechat/format` 端点处理 Markdown 转换和图片下载，属于计算密集型操作。没有速率限制可能导致：

- **资源耗尽**：大量并发请求消耗 CPU/内存/带宽
- **DoS 攻击**：恶意用户发送大量请求使服务不可用
- **成本失控**：图床上传和外部 API 调用产生费用

## 推荐方案

### 方案 1：使用 slowapi（推荐）

```bash
pip install slowapi
```

```python
# src/api/app.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# src/api/routers/wechat_format.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/wechat/format")
@limiter.limit("10/minute")  # 每分钟 10 次
async def format_for_wechat(request: WechatFormatRequest):
    ...
```

### 方案 2：使用 Nginx 限流

```nginx
# nginx.conf
http {
    limit_req_zone $binary_remote_addr zone=wechat_api:10m rate=10r/m;
    
    server {
        location /api/wechat/format {
            limit_req zone=wechat_api burst=5 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

### 方案 3：使用云服务商限流

- **AWS API Gateway**：内置速率限制和配额管理
- **Cloudflare**：Rate Limiting Rules
- **阿里云 API 网关**：流量控制策略

## 推荐限制值

| 场景 | 限制 | 说明 |
|------|------|------|
| 开发环境 | 30/分钟 | 宽松限制，方便测试 |
| 生产环境（免费用户） | 10/分钟 | 防止滥用 |
| 生产环境（付费用户） | 60/分钟 | 根据业务需求调整 |
| 突发流量 | burst=5 | 允许短时间内超出限制 |

## 实施优先级

1. **立即实施**：如果服务已公开访问
2. **中期实施**：如果仅内部使用或有其他认证机制
3. **长期优化**：根据实际流量调整限制值

## 监控建议

- 记录被限流的请求（IP、时间、频率）
- 设置告警：限流触发次数异常增加
- 定期审查限流日志，识别恶意行为
