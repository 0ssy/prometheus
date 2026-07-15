#!/usr/bin/env bash
# P11 — Disaster recovery failover.
#
# Automated DR drill / failover helper. It:
#   1. takes a fresh backup (scripts/backup.py)
#   2. verifies DB integrity
#   3. restarts the service by touching a failover marker
#
# Run from the repository root:
#   bash scripts/dr_failover.sh
set -euo pipefail

DB_PATH="${DB_PATH:-./data/prometheus.db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
MARKER="${MARKER:-./data/dr_failover.marker}"

echo "[dr] $(date -u +%Y-%m-%dT%H:%M:%SZ) starting failover procedure"

python3 scripts/backup.py --db "$DB_PATH" --out "$BACKUP_DIR"

echo "[dr] verifying database integrity"
if ! sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
  echo "[dr] ERROR: integrity_check failed" >&2
  exit 1
fi

echo "[dr] marking failover complete"
date -u +%Y-%m-%dT%H:%M:%SZ > "$MARKER"

echo "[dr] failover complete"
