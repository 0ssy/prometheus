#!/usr/bin/env python3
"""
Phase 11 — Prometheus Platform 1.0 validation runner.

Runs the end-to-end validation suite in ``tests/e2e/test_platform_1_0.py``
and prints a human-readable, deliverable-by-deliverable summary that mirrors
``docs/platform-1.0-checklist.md``.

Exit code is 0 only if every Platform 1.0 check passes (Go), and non-zero
otherwise (No-Go).

Usage:
    python scripts/validate_platform_1_0.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
E2E_TEST = REPO_ROOT / "tests" / "e2e" / "test_platform_1_0.py"

# Map test function names -> the Phase 11 deliverable they validate.
CHECKLIST = [
    ("test_branding", "Engineering Intelligence Platform branding"),
    ("test_desktop_app", "Native desktop app (Tauri, Windows/Linux/macOS)"),
    ("test_aether_runtime", "Aether AI Runtime"),
    ("test_titan_integration", "Titan AI Platform integration"),
    ("test_hardware_platform", "Hardware platform (20+ protocols, recovery)"),
    ("test_digital_twin", "Digital twin and knowledge platform"),
    ("test_simulation_engine", "Simulation and verification engine"),
    ("test_plugin_marketplace", "Plugin marketplace and SDK"),
    ("test_enterprise_collaboration", "Enterprise collaboration (teams/remote/billing)"),
    ("test_autonomous_workflows", "Autonomous workflows with human-in-the-loop"),
    ("test_backup_dr", "LTS, upgrade, backup, and disaster recovery"),
    ("test_e2e_workflow_success", "End-to-end workflow success >= 95%"),
]


def _run_tests() -> dict[str, str]:
    """Run the E2E suite via pytest and return {test_name: outcome}."""
    import pytest

    results: dict[str, str] = {}

    class _Collector:
        def pytest_runtest_logreport(self, report):  # noqa: N802 (pytest hook)
            if report.when != "call" and not (
                report.when == "setup" and report.outcome in ("skipped", "error")
            ):
                return
            name = report.nodeid.split("::")[-1]
            # Prefer the "call" outcome; don't overwrite a failure with later phases.
            if name not in results or report.outcome != "passed":
                results[name] = report.outcome

    exit_code = pytest.main(
        ["-q", "--no-header", str(E2E_TEST)],
        plugins=[_Collector()],
    )
    results["__exit_code__"] = str(int(exit_code))
    return results


def main() -> int:
    if not E2E_TEST.exists():
        print(f"ERROR: E2E test file not found: {E2E_TEST}", file=sys.stderr)
        return 2

    print("=" * 72)
    print(" Prometheus Platform 1.0 — Phase 11 End-to-End Validation")
    print("=" * 72)

    results = _run_tests()
    pytest_exit = int(results.pop("__exit_code__", "1"))

    symbols = {"passed": "[PASS]", "failed": "[FAIL]", "skipped": "[SKIP]", "error": "[ERR ]"}
    passed = 0
    total = len(CHECKLIST)

    print()
    for test_name, description in CHECKLIST:
        outcome = results.get(test_name, "missing")
        symbol = symbols.get(outcome, "[????]")
        if outcome == "passed":
            passed += 1
        print(f"  {symbol}  {description}")

    print()
    print("-" * 72)
    rate = (passed / total * 100) if total else 0.0
    print(f"  Deliverables validated: {passed}/{total} ({rate:.0f}%)")

    decision = "GO" if (passed == total and pytest_exit == 0) else "NO-GO"
    print(f"  Platform 1.0 Go/No-Go decision: {decision}")
    print("=" * 72)

    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
