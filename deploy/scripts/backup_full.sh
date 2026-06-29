#!/usr/bin/env bash
# ===========================================================================
# Cluster-level backup. Two layers:
#   1. Logical dump (pg_dump custom format) — portable, restorable anywhere.
#   2. PITR base backup — combined with continuous WAL archiving for
#      point-in-time recovery (run WAL-G / pgBackRest separately for WAL).
#
# Run as nextora_admin. Encrypt + ship to object storage with retention.
# Schedule via Celery Beat or an external cron / k8s CronJob.
# ===========================================================================
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL required}"
: "${BACKUP_BUCKET:?BACKUP_BUCKET required}"   # e.g. s3://nextora-backups
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_FILE="/tmp/nextora_${TS}.dump"

echo "[backup] pg_dump (custom format, compressed)..."
pg_dump --format=custom --compress=9 --no-owner --no-privileges \
        --file="${DUMP_FILE}" "${DATABASE_URL}"

echo "[backup] encrypting..."
# age/gpg envelope encryption — key managed by the secret manager.
gpg --batch --yes --encrypt --recipient "${BACKUP_GPG_RECIPIENT}" "${DUMP_FILE}"

echo "[backup] uploading to ${BACKUP_BUCKET}..."
aws s3 cp "${DUMP_FILE}.gpg" "${BACKUP_BUCKET}/logical/nextora_${TS}.dump.gpg"

echo "[backup] cleanup..."
rm -f "${DUMP_FILE}" "${DUMP_FILE}.gpg"

echo "[backup] done. PITR WAL archiving is handled by WAL-G (separate daemon)."
