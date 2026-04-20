#!/bin/bash
# Translation Agent - Linux 启动脚本
# 用途：生产环境启动服务

set -e

# 配置
PYTHON_CMD="${PYTHON_CMD:-python3}"
PORT="${PORT:-54321}"
HOST="${HOST:-127.0.0.1}"
WORKERS="${WORKERS:-4}"
RELOAD=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            RELOAD="--reload"
            shift
            ;;
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --workers=*)
            WORKERS="${1#*=}"
            shift
            ;;
        --host=*)
            HOST="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  Translation Agent"
echo "  Starting service on ${HOST}:${PORT}"
echo "========================================"
echo ""

# 检查 Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "[ERROR] Python not found!"
    echo "Please install Python 3.10+ from your package manager"
    exit 1
fi

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "[INFO] Using virtual environment: .venv"
    source .venv/bin/activate
    PYTHON_CMD=".venv/bin/python"
fi

# 检查 uvicorn
if ! $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
    echo "[ERROR] uvicorn not installed"
    echo "Installing: $PYTHON_CMD -m pip install uvicorn"
    $PYTHON_CMD -m pip install uvicorn
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found!"
    echo "Please copy .env.example to .env and configure your API keys."
    echo ""
fi

# 构建前端
FRONTEND_DIR="web/frontend"
FRONTEND_DIST="${FRONTEND_DIR}/dist"

if [ ! -f "${FRONTEND_DIST}/index.html" ]; then
    echo "[INFO] Frontend not built. Building..."
    cd $FRONTEND_DIR

    if [ ! -d "node_modules" ]; then
        echo "[INFO] Installing frontend dependencies..."
        npm install
    fi

    echo "[INFO] Building frontend..."
    npm run build
    cd ../..
    echo ""
else
    echo "[INFO] Frontend is up-to-date. Skipping build."
    echo ""
fi

# 检查端口占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[WARNING] Port $PORT is already in use"
    read -p "Kill existing process? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[INFO] Killing process on port $PORT..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo "[ERROR] Cannot start server, port is occupied"
        exit 1
    fi
fi

# 创建必要目录
mkdir -p projects logs backups

# 启动服务
echo ""
echo "[INFO] Starting server..."
echo "[INFO] API:      http://${HOST}:${PORT}/api"
echo "[INFO] Web UI:   http://${HOST}:${PORT}"
echo "[INFO] API Docs: http://${HOST}:${PORT}/docs"
echo ""
echo "Press Ctrl+C to stop."
echo "========================================"
echo ""

# 生产环境使用 gunicorn（如果已安装）
if command -v gunicorn &> /dev/null && [ -z "$RELOAD" ]; then
    echo "[INFO] Using Gunicorn with $WORKERS workers"
    exec gunicorn src.api.app:app \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind ${HOST}:${PORT} \
        --timeout 300 \
        --keep-alive 5 \
        --graceful-timeout 10 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info
else
    # 开发环境或未安装 gunicorn 时使用 uvicorn
    echo "[INFO] Using Uvicorn (single worker)"
    exec $PYTHON_CMD -m uvicorn src.api.app:app \
        --host $HOST \
        --port $PORT \
        --timeout-keep-alive 5 \
        --timeout-graceful-shutdown 10 \
        --limit-concurrency 100 \
        --limit-max-requests 1000 \
        $RELOAD
fi
