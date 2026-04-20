#!/bin/bash
# Translation Agent - Linux 停止脚本

set -e

PORT="${PORT:-54321}"

echo "========================================"
echo "  Translation Agent"
echo "  Stopping service on port ${PORT}"
echo "========================================"
echo ""

# 查找占用端口的进程
PIDS=$(lsof -ti:$PORT 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo "[INFO] No process found on port $PORT"
    exit 0
fi

echo "[INFO] Found processes: $PIDS"

# 优雅停止（SIGTERM）
for PID in $PIDS; do
    echo "[INFO] Sending SIGTERM to process $PID..."
    kill -TERM $PID 2>/dev/null || true
done

# 等待进程退出
sleep 3

# 检查是否还有进程
REMAINING=$(lsof -ti:$PORT 2>/dev/null || true)

if [ -n "$REMAINING" ]; then
    echo "[WARNING] Processes still running, forcing kill..."
    for PID in $REMAINING; do
        echo "[INFO] Sending SIGKILL to process $PID..."
        kill -9 $PID 2>/dev/null || true
    done
    sleep 1
fi

# 最终检查
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[ERROR] Failed to stop service on port $PORT"
    exit 1
else
    echo "[SUCCESS] Service stopped successfully"
fi
