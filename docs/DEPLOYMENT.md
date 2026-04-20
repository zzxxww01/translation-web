# 生产部署指南

## 环境要求

### 硬件要求
- **CPU**: 4 核心以上
- **内存**: 至少 4GB RAM（推荐 8GB）
- **磁盘**: 50GB 可用空间（用于项目数据和备份）
- **网络**: 稳定的互联网连接（访问 LLM API）

### 软件要求
- **Python**: 3.10 或更高版本
- **Node.js**: 18.x 或更高版本
- **操作系统**: Windows 10+, Ubuntu 20.04+, macOS 12+

---

## 快速部署

### 1. 克隆仓库
```bash
git clone https://github.com/your-org/translation-agent.git
cd translation-agent
```

### 2. 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd web/frontend
npm install
npm run build
cd ../..
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入真实的 API 密钥
```

### 4. 启动服务
```bash
# Windows
start.bat

# Linux/macOS
./start.sh
```

---

## 生产环境配置

### 安全配置

#### 1. 修改默认端口
```bash
# .env
API_PORT=8080  # 改为非默认端口
```

#### 2. 配置 CORS 白名单
```bash
# .env
CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

#### 3. 禁用调试模式
```bash
# .env
DEBUG=false
LOG_LEVEL=WARNING
```

#### 4. 配置反向代理（Nginx）
```nginx
# /etc/nginx/sites-available/translation-agent
server {
    listen 443 ssl http2;
    server_name translate.your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 限制请求体大小
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:54321;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

#### 5. 配置防火墙
```bash
# Ubuntu/Debian
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw deny 54321/tcp  # 阻止直接访问应用端口

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

---

## 数据备份

### 自动备份（推荐）

#### Linux/macOS - 使用 cron
```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /path/to/translation-agent/scripts/backup.sh >> /var/log/translation-backup.log 2>&1
```

#### Windows - 使用任务计划程序
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天凌晨 2:00
4. 操作：启动程序 `C:\path\to\translation-agent\scripts\backup.bat`

### 手动备份
```bash
# Linux/macOS
./scripts/backup.sh

# Windows
scripts\backup.bat
```

### 备份到云存储

#### AWS S3
```bash
# 安装 AWS CLI
pip install awscli

# 配置凭证
aws configure

# 修改 scripts/backup.sh，取消注释 S3 上传部分
```

#### 阿里云 OSS
```bash
# 安装 ossutil
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64

# 配置凭证
./ossutil64 config

# 修改 scripts/backup.sh，取消注释 OSS 上传部分
```

---

## 监控与日志

### 健康检查
```bash
# 检查服务状态
curl http://localhost:54321/api/health

# 预期响应
{"status":"healthy","service":"Translation Agent API"}
```

### 日志配置
```bash
# .env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log
```

### 监控指标

#### 1. 磁盘空间
```bash
# 设置告警：可用空间 < 10GB
df -h | grep /path/to/translation-agent
```

#### 2. 内存使用
```bash
# 设置告警：内存使用 > 80%
free -m
```

#### 3. API 可用性
```bash
# 使用 Uptime Kuma 或类似工具监控
# 监控端点: https://your-domain.com/api/health
# 检查间隔: 60 秒
```

---

## 性能优化

### 1. 启用 Gzip 压缩
已在 `src/api/app.py` 中默认启用：
```python
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 2. 配置 LLM 并发
```bash
# .env
# VectorEngine 支持高并发
VECTORENGINE_API_KEY=your_key
```

### 3. 调整工作进程数
```bash
# 使用 Gunicorn 部署（推荐）
pip install gunicorn

gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:54321 \
    --timeout 300 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

---

## 故障排查

### 问题 1: 端口被占用
```bash
# Windows
netstat -ano | findstr :54321
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :54321
kill -9 <PID>
```

### 问题 2: API 密钥无效
```bash
# 检查环境变量
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```

### 问题 3: 前端无法访问后端
```bash
# 检查 CORS 配置
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     http://localhost:54321/api/health -v
```

### 问题 4: 磁盘空间不足
```bash
# 清理旧备份
find backups/ -name "projects_backup_*.tar.gz" -mtime +7 -delete

# 清理临时文件
find projects/ -name "*.tmp" -delete
```

---

## 升级指南

### 1. 备份数据
```bash
./scripts/backup.sh
```

### 2. 拉取最新代码
```bash
git pull origin main
```

### 3. 更新依赖
```bash
pip install -r requirements.txt --upgrade
cd web/frontend && npm install && npm run build
```

### 4. 重启服务
```bash
./stop.sh
./start.sh
```

---

## 安全检查清单

部署前请确认：

- [ ] 已修改默认端口
- [ ] 已配置 CORS 白名单
- [ ] 已禁用 DEBUG 模式
- [ ] 已配置 HTTPS（反向代理）
- [ ] 已配置防火墙规则
- [ ] 已设置自动备份
- [ ] 已配置监控告警
- [ ] `.env` 文件权限为 600
- [ ] API 密钥已轮换（不使用示例密钥）
- [ ] 已阅读 `SECURITY.md`

---

## 技术支持

如遇到问题，请：
1. 查看日志文件 `logs/app.log`
2. 检查 GitHub Issues
3. 联系项目维护者

---

## 许可证

本项目仅供内部协作使用，不维护社区贡献流程。
