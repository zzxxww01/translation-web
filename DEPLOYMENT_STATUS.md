# Translation Agent 部署状态

## 部署信息
- **域名**: https://momo.beauty
- **部署时间**: 2026-04-21
- **部署方式**: Cloudflare Tunnel + Nginx + Systemd

## 服务状态

### 后端服务
- **服务名**: translation-agent.service
- **状态**: ✅ 运行中
- **端口**: 127.0.0.1:54321
- **管理命令**:
  ```bash
  sudo systemctl status translation-agent
  sudo systemctl restart translation-agent
  sudo journalctl -u translation-agent -f
  ```

### 前端服务
- **访问地址**: https://momo.beauty
- **状态**: ✅ 正常
- **部署位置**: /home/zxw/translation-agent/web/frontend/dist

### Nginx 反向代理
- **配置文件**: /etc/nginx/sites-available/translation-agent
- **监听端口**: 80
- **路由规则**:
  - `/` → 前端静态文件
  - `/api/` → 后端 API (127.0.0.1:54321)

### Cloudflare Tunnel
- **配置文件**: /etc/cloudflared/config.yml
- **域名**: momo.beauty
- **目标**: http://localhost:80

## API 端点测试

```bash
# 获取项目列表
curl https://momo.beauty/api/projects

# 获取可用模型
curl https://momo.beauty/api/models

# 健康检查
curl https://momo.beauty/api/health
```

## 重启服务

使用提供的脚本安全重启服务：

```bash
/home/zxw/translation-agent/scripts/restart-service.sh
```

该脚本会：
1. 停止相关服务
2. 清理端口占用
3. 验证端口状态
4. 禁用占位服务
5. 启动服务
6. 验证服务状态

## 环境配置

### .env 文件
位置: `/home/zxw/translation-agent/.env`

关键配置:
- GEMINI_API_KEY: ✅ 已配置
- VECTORENGINE_API_KEY: ✅ 已配置
- HTTP_PROXY: ✅ 已配置
- LLM_DEFAULT_MODEL: pro-official
- LLM_MODEL_LONGFORM: deepseek-relay

### LLM 提供商配置
位置: `/home/zxw/translation-agent/config/llm_providers.yaml`
状态: ✅ 已配置

## 已解决的问题

1. ✅ 端口 54321 被 momo-beauty-placeholder.service 占用
   - 解决方案: 禁用并停止占位服务
   
2. ✅ Systemd 服务启动时端口仍被占用
   - 解决方案: 添加 ExecStartPre 清理端口

3. ✅ GitHub Actions 构建失败（button.tsx 大小写问题）
   - 解决方案: 删除符号链接，统一使用 Button.tsx

4. ✅ 配置文件缺失（llm_providers.yaml）
   - 解决方案: 从 example 复制并更新配置

## 监控和日志

### 查看实时日志
```bash
sudo journalctl -u translation-agent -f
```

### 查看最近错误
```bash
sudo journalctl -u translation-agent -n 50 --no-pager | grep -i error
```

### 检查端口占用
```bash
sudo lsof -i:54321
```

## 下一步

- [ ] 配置日志轮转
- [ ] 设置监控告警
- [ ] 配置自动备份
- [ ] 性能优化和压力测试
