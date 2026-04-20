#!/bin/bash
# Translation Agent - 项目数据备份脚本
# 用途：定期备份 projects/ 目录到本地或云存储

set -e

# 配置
BACKUP_DIR="${BACKUP_DIR:-./backups}"
PROJECTS_DIR="${PROJECTS_DIR:-./projects}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="projects_backup_${TIMESTAMP}.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# 压缩项目数据
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    --exclude='*.tmp' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    "$PROJECTS_DIR"

BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# 清理旧备份（保留最近 N 天）
find "$BACKUP_DIR" -name "projects_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Old backups cleaned (retention: ${RETENTION_DAYS} days)"

# 可选：上传到云存储
# 取消注释以下行并配置云存储凭证
# if command -v aws &> /dev/null; then
#     aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://your-bucket/backups/"
#     echo "[$(date)] Backup uploaded to S3"
# fi

# if command -v ossutil &> /dev/null; then
#     ossutil cp "${BACKUP_DIR}/${BACKUP_FILE}" "oss://your-bucket/backups/"
#     echo "[$(date)] Backup uploaded to OSS"
# fi

echo "[$(date)] Backup completed successfully"
