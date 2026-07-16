#!/usr/bin/env python3
"""
P11 — Database backup.

Snapshots the live SQLite database to a timestamped file and writes a
manifest. Intended to be invoked from Bash/PowerShell in CI or by the
backup service. Pair with ``restore.py`` and ``dr_failover.sh``.

Usage:
    python scripts/backup.py [--db ./data/prometheus.db] [--out ./backups]
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def backup(db_path: str, out_dir: str) -> Path:
    src = Path(db_path)
    if not src.exists():
        raise SystemExit(f"Database not found: {src}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dest = out / f"prometheus-{stamp}.db"
    shutil.copyfile(src, dest)
    manifest = out / f"prometheus-{stamp}.json"
    manifest.write_text(json.dumps({
        "source": str(src),
        "backup": str(dest),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description="Backup the Prometheus SQLite database")
    ap.add_argument("--db", default="./data/prometheus.db")
    ap.add_argument("--out", default="./backups")
    args = ap.parse_args()
    dest = backup(args.db, args.out)
    print(f"Backup written to {dest}")


if __name__ == "__main__":
    main()
