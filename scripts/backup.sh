#!/bin/bash
# SentinelAI — Database Backup Script
# Usage: docker compose exec backup /backup.sh
# Schedule: Add to crontab or run via docker compose --profile backup

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-sentinelai}"
POSTGRES_USER="${POSTGRES_USER:-sentinelai}"
BACKUP_DIR="/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sentinelai_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting backup..."

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Run pg_dump
pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    --no-owner --no-acl --clean --if-exists \
    | gzip > "${BACKUP_FILE}"

# Verify backup
BACKUP_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null)
if [ "${BACKUP_SIZE}" -lt 100 ]; then
    echo "[$(date)] ERROR: Backup file too small (${BACKUP_SIZE} bytes). Possible failure."
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "[$(date)] Backup complete: ${BACKUP_FILE} ($(numfmt --to=iec ${BACKUP_SIZE}))"

# Cleanup old backups
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "sentinelai_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# List remaining backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/sentinelai_*.sql.gz 2>/dev/null || echo "  (none)"

echo "[$(date)] Backup job complete."
