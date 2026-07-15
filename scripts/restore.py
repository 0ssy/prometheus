#!/usr/bin/env python3
"""
P11 — Database restore.

Restores a previously created backup (see ``backup.py``). Validates
the backup file is a real SQLite database before swapping it in, and
keeps the current file as ``.corrupted`` if the restore target is bad.

Usage:
    python scripts/restore.py --backup ./backups/prometheus-<stamp>.db [--db ./data/prometheus.db]
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path


def _is_sqlite(path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False


def restore(backup_path: str, db_path: str) -> None:
    backup = Path(backup_path)
    if not backup.exists():
        raise SystemExit(f"Backup not found: {backup}")
    if not _is_sqlite(backup):
        raise SystemExit(f"Backup is not a valid SQLite database: {backup}")

    target = Path(db_path)
    if target.exists():
        bad = target.with_suffix(".corrupted")
        shutil.move(str(target), str(bad))
    shutil.copyfile(backup, target)
    print(f"Restored {target} from {backup}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Restore a Prometheus SQLite backup")
    ap.add_argument("--backup", required=True)
    ap.add_argument("--db", default="./data/prometheus.db")
    args = ap.parse_args()
    restore(args.backup, args.db)


if __name__ == "__main__":
    main()
