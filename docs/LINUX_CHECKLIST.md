# Linux 生产环境检查清单

## 🔍 部署前检查

### 1. 系统环境
```bash
# 检查 Python 版本（需要 3.10+）
python3 --version

# 检查 Node.js 版本（需要 18+）
node --version

# 检查磁盘空间（至少 50GB）
df -h

# 检查内存（至少 4GB）
free -h

# 检查 CPU 核心数
nproc
```

### 2. 网络连接
```bash
# 测试 Gemini API 连接（无需代理）
curl -I https://generativelanguage.googleapis.com

# 测试 DNS 解析
nslookup generativelanguage.googleapis.com

# 检查防火墙出站规则
sudo iptables -L OUTPUT -n -v
```

### 3. 环境变量检查
```bash
# 确认代理配置为空或未设置
cat .env | grep -i proxy

# 应该看到：
# GEMINI_HTTP_PROXY=  # 空或注释
# GEMINI_HTTPS_PROXY=  # 空或注释

# 或者完全不存在这些行
```

---

## ⚠️ 常见陷阱（Linux 特有）

### 陷阱 1: 代理环境变量污染
**问题**: 系统级代理变量会影响 Gemini SDK

```bash
# 检查系统代理
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $http_proxy
echo $https_proxy

# 如果有值，需要在 systemd service 中清除
sudo nano /etc/systemd/system/translation-agent.service

# 添加：
Environment="HTTP_PROXY="
Environment="HTTPS_PROXY="
Environment="http_proxy="
Environment="https_proxy="
```

### 陷阱 2: SELinux 阻止网络访问
**问题**: CentOS/RHEL 默认启用 SELinux

```bash
# 检查 SELinux 状态
getenforce

# 如果是 Enforcing，临时禁用测试
sudo setenforce 0

# 永久禁用（不推荐，建议配置策略）
sudo nano /etc/selinux/config
# 修改: SELINUX=permissive

# 或者配置 SELinux 策略（推荐）
sudo setsebool -P httpd_can_network_connect 1
```

### 陷阱 3: 文件权限问题
**问题**: systemd 以 www-data 用户运行，无权限访问文件

```bash
# 检查文件所有者
ls -la /opt/translation-agent

# 修复权限
sudo chown -R www-data:www-data /opt/translation-agent/projects
sudo chown -R www-data:www-data /opt/translation-agent/logs
sudo chown -R www-data:www-data /opt/translation-agent/backups

# .env 文件权限（防止泄露）
chmod 600 /opt/translation-agent/.env
```

### 陷阱 4: 端口被占用
**问题**: 54321 端口已被其他服务占用

```bash
# 查找占用进程
sudo lsof -i :54321

# 如果是旧的 translation-agent 进程
sudo systemctl stop translation-agent

# 如果是其他服务，修改端口
nano .env
# 修改: API_PORT=8080

# 同时修改 systemd service 和 nginx 配置
```

### 陷阱 5: DNS 解析失败
**问题**: 服务器无法解析 Google 域名

```bash
# 测试 DNS
nslookup generativelanguage.googleapis.com

# 如果失败，修改 DNS 服务器
sudo nano /etc/resolv.conf
# 添加：
nameserver 8.8.8.8
nameserver 8.8.4.4

# 或使用 systemd-resolved
sudo nano /etc/systemd/resolved.conf
# 修改：
[Resolve]
DNS=8.8.8.8 8.8.4.4
```

---

## 🔧 性能调优（Linux）

### 1. 系统限制
```bash
# 增加文件描述符
sudo nano /etc/security/limits.conf
# 添加：
* soft nofile 65536
* hard nofile 65536
www-data soft nofile 65536
www-data hard nofile 65536

# 重启生效
sudo reboot
```

### 2. TCP 优化
```bash
sudo nano /etc/sysctl.conf
# 添加：
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000

# 应用配置
sudo sysctl -p
```

### 3. Gunicorn 优化
```bash
# 计算最佳 worker 数量
# 公式: (2 × CPU核心数) + 1

# 4 核 CPU
--workers 9

# 8 核 CPU
--workers 17

# 修改 systemd service
sudo nano /etc/systemd/system/translation-agent.service
```

### 4. Nginx 优化
```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
worker_rlimit_nofile 65536;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # 启用 gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # 连接优化
    keepalive_timeout 65;
    keepalive_requests 100;

    # 缓冲区优化
    client_body_buffer_size 128k;
    client_max_body_size 100m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
}
```

---

## 🛡️ 安全加固（Linux）

### 1. 最小权限原则
```bash
# 创建专用用户（不使用 www-data）
sudo useradd -r -s /bin/false translation-agent

# 修改文件所有者
sudo chown -R translation-agent:translation-agent /opt/translation-agent

# 修改 systemd service
sudo nano /etc/systemd/system/translation-agent.service
# 修改：
User=translation-agent
Group=translation-agent
```

### 2. AppArmor 配置（Ubuntu/Debian）
```bash
# 创建 AppArmor 配置
sudo nano /etc/apparmor.d/opt.translation-agent

# 内容：
#include <tunables/global>

/opt/translation-agent/bin/python3 {
  #include <abstractions/base>
  #include <abstractions/python>

  /opt/translation-agent/** r,
  /opt/translation-agent/projects/** rw,
  /opt/translation-agent/logs/** rw,
  /opt/translation-agent/backups/** rw,

  deny /etc/shadow r,
  deny /root/** rw,
}

# 加载配置
sudo apparmor_parser -r /etc/apparmor.d/opt.translation-agent
```

### 3. 日志审计
```bash
# 安装 auditd
sudo apt install auditd

# 配置审计规则
sudo nano /etc/audit/rules.d/translation-agent.rules
# 添加：
-w /opt/translation-agent/.env -p wa -k translation-env
-w /opt/translation-agent/projects -p wa -k translation-data

# 重载规则
sudo augenrules --load

# 查看审计日志
sudo ausearch -k translation-env
```

---

## 📊 监控配置

### 1. Prometheus + Grafana（可选）
```bash
# 安装 Prometheus
sudo apt install prometheus

# 配置抓取端点
sudo nano /etc/prometheus/prometheus.yml
# 添加：
scrape_configs:
  - job_name: 'translation-agent'
    static_configs:
      - targets: ['localhost:54321']

# 在应用中暴露 metrics（需要添加代码）
pip install prometheus-client
```

### 2. 日志聚合（Loki）
```bash
# 安装 Promtail
wget https://github.com/grafana/loki/releases/download/v2.9.0/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
sudo mv promtail-linux-amd64 /usr/local/bin/promtail

# 配置
sudo nano /etc/promtail/config.yml
```

### 3. 告警配置
```bash
# 磁盘空间告警
echo '#!/bin/bash
USAGE=$(df -h /opt/translation-agent | awk "NR==2 {print \$5}" | sed "s/%//")
if [ $USAGE -gt 80 ]; then
    echo "Disk usage is ${USAGE}%" | mail -s "Translation Agent Disk Alert" admin@example.com
fi' | sudo tee /usr/local/bin/check-disk.sh

sudo chmod +x /usr/local/bin/check-disk.sh

# 添加到 cron
echo "0 * * * * /usr/local/bin/check-disk.sh" | crontab -
```

---

## 🧪 部署后测试

### 1. 功能测试
```bash
# 健康检查
curl https://translate.your-domain.com/api/health

# 创建测试项目
curl -X POST https://translate.your-domain.com/api/projects \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Project","source":"Hello World"}'

# 测试翻译
curl -X POST https://translate.your-domain.com/api/projects/test/sections/test/paragraphs/test/translate \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. 性能测试
```bash
# 安装 Apache Bench
sudo apt install apache2-utils

# 并发测试（100 请求，10 并发）
ab -n 100 -c 10 https://translate.your-domain.com/api/health

# 负载测试（使用 wrk）
sudo apt install wrk
wrk -t4 -c100 -d30s https://translate.your-domain.com/api/health
```

### 3. 安全测试
```bash
# 测试路径遍历防护
curl -X POST https://translate.your-domain.com/api/projects/../../../etc/passwd/sections/test/paragraphs/test/translate

# 应返回 400 错误

# 测试请求体大小限制
dd if=/dev/zero of=large.txt bs=1M count=101
curl -X POST https://translate.your-domain.com/api/projects/test/upload -F "file=@large.txt"

# 应返回 413 错误
```

---

## 📋 最终检查清单

### 系统配置
- [ ] Python 3.10+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] Nginx 已安装并配置
- [ ] 磁盘空间 > 50GB
- [ ] 内存 > 4GB

### 应用配置
- [ ] 虚拟环境已创建
- [ ] 依赖已安装（含 gunicorn）
- [ ] 前端已构建
- [ ] `.env` 已配置
- [ ] Gemini API 密钥已填写
- [ ] **代理配置已清空或删除**
- [ ] `DEBUG=false`
- [ ] CORS 白名单已配置

### 服务配置
- [ ] systemd service 已创建
- [ ] 服务已启动并运行
- [ ] 开机自启已启用
- [ ] 日志正常输出

### 网络配置
- [ ] Nginx 反向代理已配置
- [ ] SSL 证书已获取
- [ ] 防火墙规则已配置
- [ ] DNS 解析正常
- [ ] **系统代理变量已清除**

### 安全配置
- [ ] 文件权限已设置（600 for .env）
- [ ] SELinux/AppArmor 已配置
- [ ] Fail2ban 已安装
- [ ] SSH 已加固

### 备份与监控
- [ ] 自动备份已配置（cron）
- [ ] 日志轮转已配置
- [ ] 健康检查通过
- [ ] 监控告警已配置

### 测试验证
- [ ] 健康检查通过
- [ ] 翻译功能正常
- [ ] 路径遍历防护有效
- [ ] 请求体限制有效
- [ ] SSL 证书有效

---

## 🚀 部署完成

所有检查通过后，服务已准备好投入生产使用！

**访问地址**: `https://translate.your-domain.com`

**下一步**:
1. 通知团队成员访问地址
2. 配置定期备份验证
3. 设置监控告警通知
4. 准备应急响应流程
