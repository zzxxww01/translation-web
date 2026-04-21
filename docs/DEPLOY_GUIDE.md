# Translation Agent 部署指南

## 快速部署（推荐）

### 1. 准备服务器

```bash
# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 克隆代码

```bash
git clone https://github.com/your-username/translation_agent.git
cd translation_agent
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件，填入你的 API 密钥
nano .env
```

必填配置：
```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# VectorEngine API（可选）
VECTORENGINE_API_KEY=your_vectorengine_key_here
VECTORENGINE_BASE_URL=https://api.vectorengine.ai/v1
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

服务地址：
- 前端: http://your-server-ip
- API: http://your-server-ip/api

### 5. 上传现有项目数据（可选）

如果你有本地翻译项目需要迁移：

```bash
# 在本地机器执行
scp -r projects/ user@your-server:/path/to/translation_agent/

# 或使用 rsync（推荐）
rsync -avz --progress projects/ user@your-server:/path/to/translation_agent/projects/
```

---

## 手动部署（不使用 Docker）

### 1. 安装依赖

```bash
# Python 后端
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Node.js 前端
cd web/frontend
npm install
npm run build
cd ../..
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

### 3. 启动后端

```bash
# 开发模式
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# 生产模式（使用 Gunicorn）
gunicorn src.api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### 4. 配置 Nginx

```bash
sudo cp scripts/nginx.conf /etc/nginx/sites-available/translation-agent
sudo ln -s /etc/nginx/sites-available/translation-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. 配置 systemd 服务

```bash
sudo cp scripts/translation-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable translation-agent
sudo systemctl start translation-agent
```

---

## 配置说明

### 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `GEMINI_API_KEY` | Google Gemini API 密钥 | 是 |
| `VECTORENGINE_API_KEY` | VectorEngine API 密钥 | 否 |
| `VECTORENGINE_BASE_URL` | VectorEngine API 地址 | 否 |
| `RATE_LIMIT_PER_MINUTE` | API 速率限制（次/分钟） | 否（默认 60） |
| `CORS_ORIGINS` | 允许的跨域来源 | 否（默认 *） |

### Docker Compose 配置

编辑 `docker-compose.yml` 自定义配置：

```yaml
services:
  api:
    environment:
      - RATE_LIMIT_PER_MINUTE=100  # 调整速率限制
    ports:
      - "8000:8000"  # 修改端口映射
```

---

## 安全建议

### 1. 保护 API 密钥

```bash
# 设置文件权限
chmod 600 .env

# 确保 .env 不被提交到 Git
git check-ignore .env  # 应该输出 .env
```

### 2. 配置防火墙

```bash
# 只开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 3. 启用 HTTPS

使用 Let's Encrypt 免费证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 4. 限制 API 访问

编辑 `src/api/app.py` 配置速率限制：

```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]  # 调整限制
)
```

---

## 维护操作

### 查看日志

```bash
# Docker 部署
docker-compose logs -f api
docker-compose logs -f frontend

# 手动部署
tail -f logs/error.log
tail -f logs/access.log
```

### 备份数据

```bash
# 备份项目数据
tar -czf backup-$(date +%Y%m%d).tar.gz projects/ glossary/

# 备份到远程
rsync -avz projects/ backup-server:/backups/translation-agent/
```

### 更新代码

```bash
# Docker 部署
git pull
docker-compose down
docker-compose build
docker-compose up -d

# 手动部署
git pull
source .venv/bin/activate
pip install -r requirements.txt
cd web/frontend && npm install && npm run build && cd ../..
sudo systemctl restart translation-agent
```

### 清理缓存

```bash
# 清理 Python 缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 清理 Docker 缓存
docker system prune -a
```

---

## 故障排查

### API 无法启动

```bash
# 检查端口占用
sudo lsof -i :8000

# 检查日志
docker-compose logs api
```

### 前端无法访问

```bash
# 检查 Nginx 状态
sudo systemctl status nginx
sudo nginx -t

# 检查前端构建
cd web/frontend
npm run build
```

### 翻译失败

1. 检查 API 密钥是否正确
2. 检查网络连接
3. 查看 API 日志：`docker-compose logs api`

### 数据库连接失败

项目使用文件系统存储，无需数据库。检查 `projects/` 目录权限：

```bash
chmod -R 755 projects/
```

---

## 性能优化

### 1. 增加 Worker 数量

编辑 `docker-compose.yml`：

```yaml
services:
  api:
    command: gunicorn src.api.app:app --workers 8 --worker-class uvicorn.workers.UvicornWorker
```

### 2. 启用 Nginx 缓存

编辑 `scripts/nginx.conf`：

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
}
```

### 3. 使用 Redis 缓存

添加 Redis 服务到 `docker-compose.yml`：

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## 监控

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 查看系统资源
docker stats
```

### 日志监控

使用 Prometheus + Grafana 监控（可选）：

```bash
# 添加到 docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

---

## 支持

- GitHub Issues: https://github.com/your-username/translation_agent/issues
- 文档: https://github.com/your-username/translation_agent/tree/main/docs
