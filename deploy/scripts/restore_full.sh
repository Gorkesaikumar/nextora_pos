#!/usr/bin/env bash
# ===========================================================================
# Cluster-level restore from a logical dump produced by backup_full.sh.
# For point-in-time recovery (PITR) use WAL-G `backup-fetch` + recovery target
# instead — documented in docs/runbooks/restore.md.
#
# DANGER: this restores into TARGET_DATABASE_URL. Confirm the target first.
# Always rehearse restores regularly — an untested backup is not a backup.
# ===========================================================================
set -euo pipefail

: "${TARGET_DATABASE_URL:?TARGET_DATABASE_URL required}"
DUMP_ENC="${1:?Usage: restore_full.sh <encrypted-dump.gpg>}"

echo "[restore] target = ${TARGET_DATABASE_URL}"
read -r -p "Type the target DB name to confirm restore: " CONFIRM
[ -n "${CONFIRM}" ] || { echo "Aborted."; exit 1; }

echo "[restore] decrypting..."
gpg --batch --yes --decrypt --output /tmp/restore.dump "${DUMP_ENC}"

echo "[restore] pg_restore (clean, single transaction)..."
pg_restore --clean --if-exists --no-owner --no-privileges \
           --single-transaction \
           --dbname="${TARGET_DATABASE_URL}" /tmp/restore.dump

rm -f /tmp/restore.dump
echo "[restore] complete. Re-run 'manage.py apply_rls' if restoring to a new cluster."
