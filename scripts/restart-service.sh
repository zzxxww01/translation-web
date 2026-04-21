#!/bin/bash
# Translation Agent Service Restart Script
# 用于安全地重启 translation-agent 服务

set -e

echo "=== Translation Agent 服务重启脚本 ==="
echo ""

# 1. 停止 systemd 服务
echo "[1/5] 停止 systemd 服务..."
sudo systemctl stop translation-agent 2>/dev/null || true
sleep 1

# 2. 强制清理端口占用
echo "[2/5] 清理端口 54321 占用..."
sudo fuser -k 54321/tcp 2>/dev/null || true
sleep 2

# 3. 验证端口已释放
echo "[3/5] 验证端口状态..."
if sudo lsof -i :54321 >/dev/null 2>&1; then
    echo "警告: 端口 54321 仍被占用，尝试再次清理..."
    sudo pkill -9 -f "uvicorn.*54321" 2>/dev/null || true
    sleep 2
fi

# 4. 启动服务
echo "[4/5] 启动服务..."
sudo systemctl start translation-agent
sleep 3

# 5. 检查服务状态
echo "[5/5] 检查服务状态..."
if sudo systemctl is-active --quiet translation-agent; then
    echo "✅ 服务启动成功"
    echo ""
    sudo systemctl status translation-agent --no-pager -l | head -15
    echo ""
    echo "测试 API 连接..."
    if curl -s http://localhost:54321/projects >/dev/null 2>&1; then
        echo "✅ API 响应正常"
    else
        echo "⚠️  API 暂未响应，请等待几秒后重试"
    fi
else
    echo "❌ 服务启动失败"
    echo ""
    echo "查看最近日志:"
    sudo journalctl -u translation-agent -n 20 --no-pager
    exit 1
fi

echo ""
echo "=== 重启完成 ==="
