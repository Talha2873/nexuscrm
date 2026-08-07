#!/usr/bin/env bash
# ==========================================================
# NexusCRM PostgreSQL backup helper.
# Invoked by the `database_backup` Celery beat task and by cron.
# ==========================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="${BACKUP_DIR}/nexuscrm_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "==> Dumping database ${POSTGRES_DB:-nexuscrm} to ${OUTFILE}"
PGPASSWORD="${POSTGRES_PASSWORD:-nexuscrm}" pg_dump \
  -h "${POSTGRES_HOST:-db}" \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-nexuscrm}" \
  -d "${POSTGRES_DB:-nexuscrm}" \
  --no-owner --no-privileges | gzip -9 > "${OUTFILE}"

echo "==> Pruning backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -name 'nexuscrm_*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -delete

echo "==> Backup complete: ${OUTFILE}"
