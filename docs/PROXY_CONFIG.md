# 代理配置说明

## 概述

Translation Agent 的 Gemini API 调用支持三种网络模式：

1. **直连模式**（推荐用于生产环境）
2. **可选代理模式**（开发环境）
3. **强制代理模式**（受限网络）

---

## 直连模式（无代理）

### 适用场景
- 云服务器（AWS, 阿里云, 腾讯云等）
- 海外 VPS
- 企业专线网络
- 任何可直接访问 Google API 的环境

### 配置方法

#### 方法 1: 不配置代理（推荐）
```bash
# .env 文件中完全不包含代理配置
GEMINI_API_KEY=your_api_key_here

# 不要添加以下行：
# GEMINI_HTTP_PROXY=
# GEMINI_HTTPS_PROXY=
```

#### 方法 2: 显式清空代理
```bash
# .env
GEMINI_API_KEY=your_api_key_here
GEMINI_HTTP_PROXY=
GEMINI_HTTPS_PROXY=
```

### 验证直连
```bash
# 测试 Gemini API 连接
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"

# 应返回 JSON 响应，而非连接错误
```

---

## 可选代理模式

### 适用场景
- 本地开发环境（中国大陆）
- 需要通过代理访问 Google API

### 配置方法
```bash
# .env
GEMINI_API_KEY=your_api_key_here
GEMINI_HTTP_PROXY=http://127.0.0.1:7890
GEMINI_HTTPS_PROXY=http://127.0.0.1:7890
GEMINI_NO_PROXY=localhost,127.0.0.1
```

### 代理软件推荐
- **Clash**: `http://127.0.0.1:7890`
- **V2Ray**: `http://127.0.0.1:10809`
- **Shadowsocks**: `socks5://127.0.0.1:1080`

---

## 系统代理污染问题

### 问题描述
Linux 系统级代理变量会影响 Python 应用：

```bash
# 这些变量会被 Gemini SDK 读取
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export http_proxy=http://proxy.company.com:8080
export https_proxy=http://proxy.company.com:8080
```

### 检查方法
```bash
# 检查当前 shell 环境
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $http_proxy
echo $https_proxy

# 检查 systemd 服务环境
sudo systemctl show translation-agent -p Environment
```

### 解决方法

#### 方法 1: 清除 systemd 服务的代理变量（推荐）
```bash
sudo nano /etc/systemd/system/translation-agent.service

# 在 [Service] 部分添加：
Environment="HTTP_PROXY="
Environment="HTTPS_PROXY="
Environment="http_proxy="
Environment="https_proxy="

# 重载并重启
sudo systemctl daemon-reload
sudo systemctl restart translation-agent
```

#### 方法 2: 在启动脚本中清除
```bash
# start.sh 开头添加
unset HTTP_PROXY
unset HTTPS_PROXY
unset http_proxy
unset https_proxy

# 然后启动服务
exec gunicorn ...
```

#### 方法 3: 使用 .env 覆盖
```bash
# .env
GEMINI_HTTP_PROXY=
GEMINI_HTTPS_PROXY=
```

---

## 代码层面的处理

### Gemini SDK 代理逻辑

`src/llm/gemini.py` 中的代理处理：

```python
# 第 351-356 行
http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
if http_proxy or https_proxy:
    self.proxy_config = {
        "http": http_proxy,
        "https": https_proxy or http_proxy,
    }
```

**优先级**:
1. `GEMINI_HTTP_PROXY` / `GEMINI_HTTPS_PROXY`（应用级）
2. `HTTP_PROXY` / `HTTPS_PROXY`（系统级）
3. `http_proxy` / `https_proxy`（系统级小写）

### 禁用代理的正确方式

如果系统有代理变量，但希望 Gemini 直连：

```python
# 在 .env 中显式设置为空
GEMINI_HTTP_PROXY=
GEMINI_HTTPS_PROXY=
```

或者修改代码（不推荐）：

```python
# src/llm/gemini.py
# 注释掉系统代理读取
# http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
# https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
```

---

## 常见问题

### Q1: 为什么配置了 .env 但还是走代理？
**A**: 检查系统级代理变量是否存在：
```bash
env | grep -i proxy
```

### Q2: 如何确认当前是否使用代理？
**A**: 查看日志：
```bash
# 启动时会打印代理配置
sudo journalctl -u translation-agent | grep -i proxy
```

### Q3: 代理连接失败怎么办？
**A**: 
1. 检查代理软件是否运行
2. 检查代理端口是否正确
3. 测试代理连接：
```bash
curl -x http://127.0.0.1:7890 https://www.google.com
```

### Q4: 生产环境需要代理吗？
**A**: 
- **云服务器（海外）**: 不需要
- **云服务器（中国大陆）**: 需要（或使用国内 API 镜像）
- **企业内网**: 可能需要（取决于防火墙策略）

---

## 最佳实践

### 开发环境
```bash
# .env.development
GEMINI_API_KEY=dev_key
GEMINI_HTTP_PROXY=http://127.0.0.1:7890
GEMINI_HTTPS_PROXY=http://127.0.0.1:7890
DEBUG=true
```

### 生产环境（海外服务器）
```bash
# .env.production
GEMINI_API_KEY=prod_key
# 不配置代理
DEBUG=false
LOG_LEVEL=WARNING
```

### 生产环境（中国大陆服务器）
```bash
# .env.production
GEMINI_API_KEY=prod_key
GEMINI_HTTP_PROXY=http://internal-proxy.company.com:8080
GEMINI_HTTPS_PROXY=http://internal-proxy.company.com:8080
DEBUG=false
LOG_LEVEL=WARNING
```

---

## 故障排查

### 1. 连接超时
```bash
# 错误信息
LLMConnectionError: Failed to connect to Gemini API

# 排查步骤
1. 检查网络连接: ping generativelanguage.googleapis.com
2. 检查代理配置: env | grep -i proxy
3. 测试 API 连接: curl https://generativelanguage.googleapis.com
4. 查看详细日志: tail -f logs/error.log
```

### 2. 代理认证失败
```bash
# 错误信息
LLMProxyConfigurationError: Proxy authentication required

# 解决方法
# 在代理 URL 中包含认证信息
GEMINI_HTTP_PROXY=http://username:password@proxy.com:8080
```

### 3. SSL 证书错误
```bash
# 错误信息
SSL: CERTIFICATE_VERIFY_FAILED

# 临时解决（不推荐生产环境）
export PYTHONHTTPSVERIFY=0

# 正确解决
# 更新 CA 证书
sudo apt update
sudo apt install ca-certificates
sudo update-ca-certificates
```

---

## 总结

**Linux 生产环境（无需代理）配置**:

1. ✅ `.env` 中不配置代理变量
2. ✅ 清除系统级代理变量（systemd service）
3. ✅ 验证 API 直连可用
4. ✅ 监控日志确认无代理错误

**检查命令**:
```bash
# 1. 检查 .env
cat .env | grep -i proxy

# 2. 检查系统变量
env | grep -i proxy

# 3. 检查服务环境
sudo systemctl show translation-agent -p Environment

# 4. 测试 API
curl https://generativelanguage.googleapis.com

# 5. 查看日志
sudo journalctl -u translation-agent -n 50 | grep -i proxy
```

全部检查通过后，Gemini API 将直连，无需代理！
