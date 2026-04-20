# Linux 生产环境部署指南

## 快速部署（5 分钟）

### 1. 系统要求
```bash
# Ubuntu 20.04+ / Debian 11+ / CentOS 8+
# Python 3.10+, Node.js 18+, Nginx

# 安装依赖
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip nodejs npm nginx
```

### 2. 克隆项目
```bash
cd /opt
sudo git clone https://github.com/your-org/translation-agent.git
sudo chown -R $USER:$USER translation-agent
cd translation-agent
```

### 3. 配置环境
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

**重要配置**（无需代理）:
```bash
# .env
GEMINI_API_KEY=your_real_api_key_here
GEMINI_BACKUP_API_KEY=your_backup_key_here

# 不需要配置代理（直连）
# GEMINI_HTTP_PROXY=  # 留空或删除
# GEMINI_HTTPS_PROXY=  # 留空或删除

# 生产环境配置
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://translate.your-domain.com
API_HOST=127.0.0.1  # 仅监听本地
API_PORT=54321
```

### 4. 测试启动
```bash
# 测试运行（前台）
./start.sh

# 访问 http://localhost:54321
# 确认服务正常后按 Ctrl+C 停止
```

---

## 生产部署（systemd）

### 1. 创建系统服务
```bash
# 复制 service 文件
sudo cp scripts/translation-agent.service /etc/systemd/system/

# 修改路径和用户
sudo nano /etc/systemd/system/translation-agent.service
# 修改 WorkingDirectory 和 User/Group

# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start translation-agent

# 查看状态
sudo systemctl status translation-agent

# 开机自启
sudo systemctl enable translation-agent
```

### 2. 配置 Nginx 反向代理
```bash
# 复制配置文件
sudo cp scripts/nginx.conf /etc/nginx/sites-available/translation-agent

# 修改域名
sudo nano /etc/nginx/sites-available/translation-agent
# 将 translate.your-domain.com 改为真实域名

# 启用站点
sudo ln -s /etc/nginx/sites-available/translation-agent /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 3. 配置 SSL（Let's Encrypt）
```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书（自动配置 Nginx）
sudo certbot --nginx -d translate.your-domain.com

# 自动续期（已自动配置 cron）
sudo certbot renew --dry-run
```

---

## 自动备份配置

### 1. 配置 cron 定时任务
```bash
# 赋予执行权限
chmod +x scripts/backup.sh

# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨 2 点备份）
0 2 * * * /opt/translation-agent/scripts/backup.sh >> /var/log/translation-backup.log 2>&1

# 每周日凌晨 3 点清理旧日志
0 3 * * 0 find /opt/translation-agent/logs -name "*.log" -mtime +30 -delete
```

### 2. 备份到云存储（可选）
```bash
# AWS S3
pip install awscli
aws configure
# 修改 scripts/backup.sh，取消注释 S3 部分

# 阿里云 OSS
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil
ossutil config
# 修改 scripts/backup.sh，取消注释 OSS 部分
```

---

## 监控与日志

### 1. 查看服务日志
```bash
# systemd 日志
sudo journalctl -u translation-agent -f

# 应用日志
tail -f logs/error.log
tail -f logs/access.log

# Nginx 日志
sudo tail -f /var/log/nginx/translation-agent-access.log
sudo tail -f /var/log/nginx/translation-agent-error.log
```

### 2. 健康检查
```bash
# 本地检查
curl http://localhost:54321/api/health

# 外部检查
curl https://translate.your-domain.com/api/health
```

### 3. 性能监控
```bash
# 安装 htop
sudo apt install htop

# 监控资源
htop

# 监控磁盘
df -h
du -sh projects/

# 监控网络
sudo netstat -tunlp | grep 54321
```

---

## 常见问题排查

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
# 测试 API 连接（无需代理）
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"

# 检查环境变量
source .venv/bin/activate
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"

# 确认未配置代理
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('HTTP_PROXY:', os.getenv('GEMINI_HTTP_PROXY')); print('HTTPS_PROXY:', os.getenv('GEMINI_HTTPS_PROXY'))"
```

### 问题 3: 前端无法访问
```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查防火墙
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 检查 SELinux（CentOS/RHEL）
sudo setenforce 0  # 临时禁用
sudo nano /etc/selinux/config  # 永久禁用
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
cd web/frontend
npm cache clean --force
```

---

## 性能优化

### 1. Gunicorn 工作进程数
```bash
# 推荐配置：CPU 核心数 * 2 + 1
# 4 核 CPU = 9 workers
# 修改 /etc/systemd/system/translation-agent.service
--workers 9
```

### 2. Nginx 缓存
```nginx
# 在 nginx.conf 中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
}
```

### 3. 系统优化
```bash
# 增加文件描述符限制
sudo nano /etc/security/limits.conf
# 添加：
* soft nofile 65536
* hard nofile 65536

# 优化 TCP
sudo nano /etc/sysctl.conf
# 添加：
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 10000 65000

# 应用配置
sudo sysctl -p
```

---

## 安全加固

### 1. 防火墙配置
```bash
# UFW（Ubuntu/Debian）
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 54321/tcp # 阻止直接访问应用端口

# Firewalld（CentOS/RHEL）
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 限制 SSH 访问
```bash
sudo nano /etc/ssh/sshd_config
# 修改：
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

---

## 升级流程

### 1. 备份数据
```bash
./scripts/backup.sh
```

### 2. 拉取更新
```bash
cd /opt/translation-agent
git pull origin main
```

### 3. 更新依赖
```bash
source .venv/bin/activate
pip install -r requirements.txt --upgrade

cd web/frontend
npm install
npm run build
cd ../..
```

### 4. 重启服务
```bash
sudo systemctl restart translation-agent
sudo systemctl status translation-agent
```

### 5. 验证
```bash
curl https://translate.your-domain.com/api/health
```

---

## 完整部署检查清单

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

## 技术支持

遇到问题请查看：
1. `sudo journalctl -u translation-agent -n 100`
2. `logs/error.log`
3. `/var/log/nginx/translation-agent-error.log`
4. GitHub Issues

**部署完成后，服务将在 `https://translate.your-domain.com` 可用！** 🚀
