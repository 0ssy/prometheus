#!/usr/bin/env python3
"""
P11 — Platform bootstrap and seed data.

Boots the Prometheus platform and seeds the knowledge graph with
demo data when the database is fresh. Intended to be run after
first install or database reset.

Usage:
    python scripts/bootstrap.py [--db ./data/prometheus.db]
"""

from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.bootstrap import boot
from core.container import ServiceContainer


def seed_knowledge(container: ServiceContainer) -> None:
    from sqlalchemy import func

    from core.database import SessionLocal
    from knowledge.node import KnowledgeNode

    db = SessionLocal()
    try:
        count = db.query(func.count(KnowledgeNode.id)).scalar()
        if count and count > 0:
            print("Knowledge graph already seeded (%d nodes). Skipping." % count)
            return

        print("Seeding knowledge graph with demo data...")
        knowledge_engine = container.get("knowledge_engine")

        facts = [
            ("prometheus", "is_a", "Engineering Intelligence OS"),
            ("prometheus", "version", "1.0.0-rc2"),
            ("device.esp32_01", "type", "ESP32"),
            ("device.esp32_01", "status", "online"),
            ("device.esp32_01", "supports_capability", "firmware.read"),
            ("device.esp32_01", "supports_capability", "device.recover"),
            ("agent.echo", "type", "EchoAgent"),
            ("agent.echo", "status", "idle"),
            ("plugin.echo", "type", "EchoPlugin"),
            ("plugin.echo", "status", "loaded"),
        ]
        for subject, predicate, obj in facts:
            knowledge_engine.assert_fact(db, subject, predicate, obj)
        db.commit()
        print("Seeded %d facts." % len(facts))
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Bootstrap Prometheus platform")
    ap.add_argument("--db", help="SQLite database path (currently unused; uses default config)")
    args = ap.parse_args()

    print("Booting Prometheus platform...")
    container = boot(lambda: None)
    print("Platform ready.")

    seed_knowledge(container)
    print("Bootstrap complete.")


if __name__ == "__main__":
    main()
