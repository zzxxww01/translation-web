# Translation Agent 部署指南

本文档提供 Translation Agent 在 Windows 本地环境和 Linux 云服务器的完整部署指南。

---

## 目录

- [系统要求](#系统要求)
- [Windows 本地部署](#windows-本地部署)
- [Linux 云服务器部署](#linux-云服务器部署)
  - [方案 A: Cloudflare Tunnel 部署（推荐）](#方案-a-cloudflare-tunnel-部署推荐)
  - [方案 B: 传统 Nginx + SSL 部署](#方案-b-传统-nginx--ssl-部署)
- [环境配置](#环境配置)
- [安全加固](#安全加固)
- [备份与恢复](#备份与恢复)
- [监控与维护](#监控与维护)
- [故障排查](#故障排查)

---

## 系统要求

### 硬件要求
- **CPU**: 4 核心以上
- **内存**: 至少 4GB RAM（推荐 8GB）
- **磁盘**: 50GB 可用空间
- **网络**: 稳定的互联网连接（访问 LLM API）

### 软件要求
- **Python**: 3.10 或更高版本
- **Node.js**: 18.x 或更高版本
- **操作系统**: 
  - Windows: Windows 10/11
  - Linux: Ubuntu 20.04+, Debian 11+, CentOS 8+

---

## Windows 本地部署

### 1. 安装依赖

```bash
# 确保已安装 Python 3.10+ 和 Node.js 18+
python --version
node --version
```

### 2. 克隆项目

```bash
git clone https://github.com/your-org/translation-agent.git
cd translation-agent
```

### 3. 安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 安装前端依赖

```bash
cd web\frontend
npm install
npm run build
cd ..\..
```

### 5. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，填入真实的 API 密钥
notepad .env
```

必填配置：
```env
# Gemini API（必填）
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BACKUP_API_KEY=your_backup_key_here

# VectorEngine API（可选）
VECTORENGINE_API_KEY=your_vectorengine_key_here
VECTORENGINE_BASE_URL=https://api.vectorengine.ai/v1

# 应用配置
API_HOST=127.0.0.1
API_PORT=54321
DEBUG=true
LOG_LEVEL=INFO
```

### 6. 启动服务

```bash
# 使用启动脚本
start.bat

# 或手动启动
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 54321
```

### 7. 访问应用

- Web 界面: http://localhost:54321
- API 文档: http://localhost:54321/docs

### 8. 停止服务

```bash
# 使用停止脚本
stop.bat

# 或按 Ctrl+C 停止
```

---

## Linux 云服务器部署

本项目提供两种部署方案：

- **方案 A: Cloudflare Tunnel**（推荐）- 无需公网 IP，自动 HTTPS，零配置 SSL
- **方案 B: 传统 Nginx + SSL** - 需要公网 IP 和域名解析

---

### 方案 A: Cloudflare Tunnel 部署（推荐）

#### 优势
- ✅ 无需公网 IP 或开放端口
- ✅ 自动 HTTPS，无需手动配置 SSL 证书
- ✅ 内置 DDoS 防护和 CDN 加速
- ✅ 支持内网服务器部署
- ✅ 零维护成本（证书自动续期）

#### 前置要求
- Cloudflare 账号（免费）
- 域名托管在 Cloudflare

#### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip nodejs npm nginx git

# CentOS/RHEL
sudo yum install -y python3.10 python3-pip nodejs npm nginx git
```

#### 2. 安装 Cloudflare Tunnel

```bash
# 下载并安装 cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 验证安装
cloudflared --version
```

#### 3. 克隆并配置项目

```bash
cd ~
git clone https://github.com/your-org/translation-agent.git
cd translation-agent

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 前端构建
cd web/frontend
npm install
npm run build
cd ../..

# 配置环境变量
cp .env.example .env
nano .env
```

**生产环境配置**（.env）:
```bash
# API 密钥
GEMINI_API_KEY=your_real_api_key_here
GEMINI_BACKUP_API_KEY=your_backup_key_here

# 生产环境配置
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com
API_HOST=127.0.0.1
API_PORT=54321
```

#### 4. 配置 Nginx（本地反向代理）

创建配置文件 `/etc/nginx/sites-available/translation-agent`:

```nginx
server {
    listen 80;
    server_name localhost;
    
    # 前端静态文件
    location / {
        root /home/your-user/translation-agent/web/frontend/dist;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:54321/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
# 修改目录权限（让 Nginx 可以访问）
chmod o+x ~
chmod o+x ~/translation-agent
chmod -R o+rx ~/translation-agent/web/frontend/dist

# 启用站点
sudo ln -s /etc/nginx/sites-available/translation-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. 创建 systemd 服务

创建 `/etc/systemd/system/translation-agent.service`:

```ini
[Unit]
Description=Translation Agent Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/translation-agent
Environment="PATH=/home/your-user/translation-agent/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/your-user/translation-agent/.venv/bin/uvicorn src.api.app:app --host 127.0.0.1 --port 54321
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start translation-agent
sudo systemctl enable translation-agent
sudo systemctl status translation-agent
```

#### 6. 配置 Cloudflare Tunnel

```bash
# 登录 Cloudflare（会打开浏览器）
cloudflared tunnel login

# 创建 Tunnel
cloudflared tunnel create translation-agent

# 记录返回的 Tunnel ID
```

创建配置文件 `/etc/cloudflared/config.yml`:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/your-user/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:80
  - service: http_status:404
```

#### 7. 配置 DNS

```bash
# 创建 DNS 记录（自动）
cloudflared tunnel route dns translation-agent your-domain.com
```

或手动在 Cloudflare Dashboard 添加 CNAME 记录：
- Type: `CNAME`
- Name: `@` 或 `translate`
- Target: `YOUR_TUNNEL_ID.cfargotunnel.com`
- Proxy status: `Proxied`（橙色云朵）

#### 8. 启动 Cloudflare Tunnel

```bash
# 测试运行
cloudflared tunnel run translation-agent

# 验证成功后，安装为系统服务
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

#### 9. 验证部署

```bash
# 检查服务状态
sudo systemctl status translation-agent
sudo systemctl status nginx
sudo systemctl status cloudflared

# 访问应用
curl https://your-domain.com/api/
```

访问 `https://your-domain.com` 即可使用！

---

### 方案 B: 传统 Nginx + SSL 部署

#### 前置要求
- 公网 IP 地址
- 域名已解析到服务器 IP

#### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip nodejs npm nginx git

# CentOS/RHEL
sudo yum install -y python3.10 python3-pip nodejs npm nginx git
```

#### 2. 克隆项目

```bash
cd /opt
sudo git clone https://github.com/your-org/translation-agent.git
sudo chown -R $USER:$USER translation-agent
cd translation-agent
```

#### 3. 配置环境

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn  # 生产环境必须

# 前端构建
cd web/frontend
npm install
npm run build
cd ../..

# 配置环境变量
cp .env.example .env
nano .env  # 填入真实 API 密钥
```

**生产环境配置**（.env）:
```bash
# API 密钥
GEMINI_API_KEY=your_real_api_key_here
GEMINI_BACKUP_API_KEY=your_backup_key_here

# 生产环境配置
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://translate.your-domain.com
API_HOST=127.0.0.1  # 仅监听本地
API_PORT=54321

# 不需要配置代理（云服务器直连）
# GEMINI_HTTP_PROXY=  # 留空或删除
# GEMINI_HTTPS_PROXY=  # 留空或删除
```

#### 4. 测试启动

```bash
# 测试运行（前台）
./start.sh

# 访问 http://your-server-ip:54321
# 确认服务正常后按 Ctrl+C 停止
```

### 生产部署（systemd + Nginx）

#### 1. 创建 systemd 服务

创建服务文件 `/etc/systemd/system/translation-agent.service`:

```ini
[Unit]
Description=Translation Agent API Service
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/translation-agent
Environment="PATH=/opt/translation-agent/.venv/bin"
ExecStart=/opt/translation-agent/.venv/bin/gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:54321 \
    --timeout 300 \
    --access-logfile /opt/translation-agent/logs/access.log \
    --error-logfile /opt/translation-agent/logs/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 创建日志目录
mkdir -p logs
sudo chown -R www-data:www-data /opt/translation-agent

# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start translation-agent

# 查看状态
sudo systemctl status translation-agent

# 开机自启
sudo systemctl enable translation-agent
```

#### 2. 配置 Nginx 反向代理

创建配置文件 `/etc/nginx/sites-available/translation-agent`:

```nginx
server {
    listen 80;
    server_name translate.your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name translate.your-domain.com;

    # SSL 证书（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/translate.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/translate.your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 限制请求体大小
    client_max_body_size 100M;

    # 日志
    access_log /var/log/nginx/translation-agent-access.log;
    error_log /var/log/nginx/translation-agent-error.log;

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

启用站点：

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/translation-agent /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

#### 3. 配置 SSL（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书（自动配置 Nginx）
sudo certbot --nginx -d translate.your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

---

## 环境配置

### 环境变量说明

| 变量名 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| `GEMINI_API_KEY` | Google Gemini API 主密钥 | 是 | - |
| `GEMINI_BACKUP_API_KEY` | Gemini 备用密钥 | 否 | - |
| `VECTORENGINE_API_KEY` | VectorEngine API 密钥 | 否 | - |
| `VECTORENGINE_BASE_URL` | VectorEngine API 地址 | 否 | - |
| `API_HOST` | API 监听地址 | 否 | 127.0.0.1 |
| `API_PORT` | API 监听端口 | 否 | 54321 |
| `DEBUG` | 调试模式 | 否 | false |
| `LOG_LEVEL` | 日志级别 | 否 | INFO |
| `CORS_ORIGINS` | 允许的跨域来源 | 否 | * |

### LLM 配置

详细配置说明请参考：[docs/LLM模块系统手册.md](./LLM模块系统手册.md)

配置文件位置：`config/llm_providers.yaml`

---

## 安全加固

### 1. 防火墙配置

```bash
# Ubuntu/Debian (UFW)
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 54321/tcp # 阻止直接访问应用端口

# CentOS/RHEL (Firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 限制 SSH 访问

```bash
sudo nano /etc/ssh/sshd_config

# 修改配置
PermitRootLogin no
PasswordAuthentication no  # 仅允许密钥登录
Port 2222  # 修改默认端口

sudo systemctl restart sshd
```

### 3. 安装 Fail2ban

```bash
sudo apt install fail2ban

# 配置
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
# 启用 nginx-http-auth, sshd

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 4. 文件权限

```bash
# 保护环境变量文件
chmod 600 .env

# 确保 .env 不被提交到 Git
git check-ignore .env  # 应该输出 .env
```

---

## 备份与恢复

### 自动备份配置

#### Linux - 使用 cron

```bash
# 赋予执行权限
chmod +x scripts/backup.sh

# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点备份）
0 2 * * * /opt/translation-agent/scripts/backup.sh >> /var/log/translation-backup.log 2>&1

# 每周日凌晨 3 点清理旧日志
0 3 * * 0 find /opt/translation-agent/logs -name "*.log" -mtime +30 -delete
```

#### Windows - 使用任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天凌晨 2:00
4. 操作：启动程序 `C:\path\to\translation-agent\scripts\backup.bat`

### 手动备份

```bash
# Linux
./scripts/backup.sh

# Windows
scripts\backup.bat
```

### 备份到云存储

#### AWS S3

```bash
pip install awscli
aws configure
# 修改 scripts/backup.sh，取消注释 S3 部分
```

#### 阿里云 OSS

```bash
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil
ossutil config
# 修改 scripts/backup.sh，取消注释 OSS 部分
```

---

## 监控与维护

### 服务管理命令

#### Cloudflare Tunnel 部署

```bash
# 后端服务管理
sudo systemctl start translation-agent      # 启动
sudo systemctl stop translation-agent       # 停止
sudo systemctl restart translation-agent    # 重启
sudo systemctl status translation-agent     # 查看状态

# Nginx 管理
sudo systemctl reload nginx                 # 重载配置
sudo systemctl restart nginx                # 重启
sudo nginx -t                               # 测试配置

# Cloudflare Tunnel 管理
sudo systemctl start cloudflared            # 启动
sudo systemctl stop cloudflared             # 停止
sudo systemctl restart cloudflared          # 重启
sudo systemctl status cloudflared           # 查看状态

# 查看日志
sudo journalctl -u translation-agent -f     # 后端日志
sudo journalctl -u cloudflared -f           # Tunnel 日志
sudo tail -f /var/log/nginx/error.log       # Nginx 日志
```

#### 传统 Nginx + SSL 部署

```bash
# 后端服务管理
sudo systemctl start translation-agent
sudo systemctl stop translation-agent
sudo systemctl restart translation-agent

# Nginx 管理
sudo systemctl reload nginx
sudo systemctl restart nginx

# 查看日志
sudo journalctl -u translation-agent -f
sudo tail -f /var/log/nginx/translation-agent-access.log
sudo tail -f /var/log/nginx/translation-agent-error.log
```

### 健康检查

```bash
# 本地检查
curl http://localhost:54321/
curl http://localhost/api/

# 外部检查（Cloudflare Tunnel）
curl https://your-domain.com/api/

# 外部检查（传统部署）
curl https://translate.your-domain.com/api/health

# 预期响应
# 返回项目列表 JSON 数据
```

### 查看日志

```bash
# systemd 日志
sudo journalctl -u translation-agent -f
sudo journalctl -u cloudflared -f  # 仅 Cloudflare Tunnel

# Nginx 日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### 性能监控

```bash
# 监控资源
htop

# 监控磁盘
df -h
du -sh projects/

# 监控网络
sudo netstat -tunlp | grep 54321
```

### 升级流程

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取更新
git pull origin main

# 3. 更新依赖
source .venv/bin/activate
pip install -r requirements.txt --upgrade
cd web/frontend && npm install && npm run build && cd ../..

# 4. 重启服务
sudo systemctl restart translation-agent

# 5. 验证
curl https://translate.your-domain.com/api/health
```

---

## 故障排查

### Cloudflare Tunnel 相关问题

#### 问题 1: Tunnel 无法连接

```bash
# 检查 cloudflared 服务状态
sudo systemctl status cloudflared

# 查看详细日志
sudo journalctl -u cloudflared -n 50

# 测试 Tunnel 连接
cloudflared tunnel info translation-agent

# 重启 Tunnel
sudo systemctl restart cloudflared
```

#### 问题 2: 域名返回 502 错误

**原因**: Nginx 无法访问前端文件或后端服务未启动

```bash
# 检查后端服务
sudo systemctl status translation-agent
curl http://localhost:54321/

# 检查 Nginx
sudo systemctl status nginx
curl http://localhost/

# 检查文件权限
ls -la ~/translation-agent/web/frontend/dist/
chmod o+x ~
chmod o+x ~/translation-agent
chmod -R o+rx ~/translation-agent/web/frontend/dist

# 查看 Nginx 错误日志
sudo tail -50 /var/log/nginx/error.log
```

#### 问题 3: 端口 54321 被占用

```bash
# 查找占用进程
sudo lsof -i :54321

# 停止占用进程
sudo kill -9 <PID>

# 重启服务
sudo systemctl restart translation-agent
```

#### 问题 4: Cloudflare Tunnel 配置错误

```bash
# 检查配置文件
cat /etc/cloudflared/config.yml

# 验证配置
cloudflared tunnel ingress validate

# 确认 Tunnel 指向正确的服务
# 应该是: service: http://localhost:80
# 而不是: service: http://localhost:54321
```

#### 问题 5: DNS 未生效

```bash
# 检查 DNS 记录
nslookup your-domain.com

# 手动添加 CNAME 记录（如果自动添加失败）
# 在 Cloudflare Dashboard:
# Type: CNAME
# Name: @ 或 translate
# Target: YOUR_TUNNEL_ID.cfargotunnel.com
# Proxy: Enabled (橙色云朵)
```

---

### 传统部署相关问题

### 问题 1: 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u translation-agent -n 50

# 检查端口占用
sudo lsof -i :54321

# 检查权限
ls -la /opt/translation-agent
sudo chown -R www-data:www-data /opt/translation-agent/projects
```

### 问题 2: Gemini API 连接失败

```bash
# 测试 API 连接
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"

# 检查环境变量
source .venv/bin/activate
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"

# 确认未配置代理（云服务器）
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('HTTP_PROXY:', os.getenv('GEMINI_HTTP_PROXY'))"
```

### 问题 3: 前端无法访问

```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查防火墙
sudo ufw status

# 检查 SELinux（CentOS/RHEL）
sudo setenforce 0  # 临时禁用
```

### 问题 4: 磁盘空间不足

```bash
# 清理旧备份
find backups/ -name "projects_backup_*.tar.gz" -mtime +7 -delete

# 清理临时文件
find projects/ -name "*.tmp" -delete

# 清理日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理 npm 缓存
cd web/frontend && npm cache clean --force
```

### 问题 5: Windows 端口被占用

```bash
# 查找占用进程
netstat -ano | findstr :54321

# 结束进程
taskkill /PID <PID> /F
```

---

## 部署检查清单

### Windows 本地部署

- [ ] Python 3.10+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] 项目已克隆
- [ ] 虚拟环境已创建
- [ ] Python 依赖已安装
- [ ] 前端已构建
- [ ] `.env` 已配置
- [ ] Gemini API 密钥已填写
- [ ] 服务可正常启动
- [ ] Web 界面可访问

### Linux 云服务器部署 - Cloudflare Tunnel

- [ ] 系统依赖已安装（Python, Node.js, Nginx）
- [ ] cloudflared 已安装
- [ ] 项目已克隆
- [ ] 虚拟环境已创建并激活
- [ ] Python 依赖已安装
- [ ] 前端已构建
- [ ] `.env` 已配置
- [ ] Gemini API 密钥已填写
- [ ] `DEBUG=false` 已设置
- [ ] CORS 已配置为域名
- [ ] Nginx 本地反向代理已配置
- [ ] 目录权限已设置（chmod o+x）
- [ ] systemd 服务已创建并启动
- [ ] Cloudflare Tunnel 已创建
- [ ] Tunnel 配置文件已创建（/etc/cloudflared/config.yml）
- [ ] DNS 记录已添加（CNAME）
- [ ] cloudflared 服务已启动并自启
- [ ] 健康检查通过（https://your-domain.com/api/）
- [ ] 前端页面可访问

### Linux 云服务器部署 - 传统 Nginx + SSL

- [ ] 系统依赖已安装（Python, Node.js, Nginx）
- [ ] 项目已克隆到 `/opt/translation-agent`
- [ ] 虚拟环境已创建并激活
- [ ] Python 依赖已安装（含 gunicorn）
- [ ] 前端已构建
- [ ] `.env` 已配置（无代理配置）
- [ ] Gemini API 密钥已填写
- [ ] `DEBUG=false` 已设置
- [ ] CORS 白名单已配置
- [ ] systemd 服务已创建并启动
- [ ] Nginx 反向代理已配置
- [ ] SSL 证书已获取（Let's Encrypt）
- [ ] 防火墙规则已配置
- [ ] 自动备份已配置（cron）
- [ ] 日志轮转已配置
- [ ] 健康检查通过
- [ ] 服务开机自启已启用

---

## 相关文档

- [系统架构](./系统架构.md)
- [LLM 模块系统手册](./LLM模块系统手册.md)
- [代理配置说明](./PROXY_CONFIG.md)

---

## 技术支持

遇到问题请查看：
1. 日志文件：`logs/error.log`
2. systemd 日志：`sudo journalctl -u translation-agent -n 100`
3. Nginx 日志：`/var/log/nginx/translation-agent-error.log`
4. GitHub Issues

**部署完成后，服务将在 `https://translate.your-domain.com` 可用！** 🚀
