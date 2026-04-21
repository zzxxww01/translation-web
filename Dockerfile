FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Gunicorn（生产环境）
RUN pip install --no-cache-dir gunicorn

# 复制应用代码
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY start.sh .
RUN chmod +x start.sh

# 创建数据目录
RUN mkdir -p projects glossary data logs backups

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:54321/api/health || exit 1

EXPOSE 54321

CMD ["./start.sh"]
