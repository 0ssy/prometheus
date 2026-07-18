"""
Phase 11 — Prometheus Platform 1.0 end-to-end validation.

These tests validate the final-product deliverables and exit KPIs from
``architecture/roadmap.md`` (P11) and the human-facing checklist in
``docs/platform-1.0-checklist.md``.

They are intentionally *structural* and *behavioral* rather than heavy
integration tests: each checks that a Platform 1.0 subsystem is present and
usable, plus one end-to-end workflow that must succeed at the roadmap's
>= 95% threshold. This keeps the suite fast enough to run as a release gate
while still exercising the real modules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Repository root (…/prometheus). This file lives at tests/e2e/.
REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 1. Branding — Engineering Intelligence Platform
# ---------------------------------------------------------------------------
def test_branding():
    """The platform ships a coherent Prometheus name + version."""
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml missing"
    text = pyproject.read_text(encoding="utf-8")

    name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert name_match, "project name not declared in pyproject.toml"
    assert version_match, "project version not declared in pyproject.toml"

    name = name_match.group(1).lower()
    version = version_match.group(1)
    assert "prometheus" in name, f"unexpected product name: {name}"
    # Platform 1.0 line (1.0.x, 1.0.0-rc1, etc.).
    assert version.startswith("1.0"), f"not a Platform 1.0 version: {version}"


# ---------------------------------------------------------------------------
# 2. Native desktop app — Tauri (Windows / Linux / macOS)
# ---------------------------------------------------------------------------
def test_desktop_app():
    """A valid Tauri configuration exists for the native desktop shell."""
    conf = REPO_ROOT / "src-tauri" / "tauri.conf.json"
    assert conf.exists(), "src-tauri/tauri.conf.json missing"

    data = json.loads(conf.read_text(encoding="utf-8"))
    assert data.get("productName"), "tauri productName not set"
    assert data.get("version"), "tauri version not set"
    assert data.get("identifier"), "tauri bundle identifier not set"
    assert "app" in data and "windows" in data["app"], "tauri window config missing"
    assert data["app"]["windows"], "no tauri windows configured"
    # A Rust crate must back the desktop shell.
    assert (REPO_ROOT / "src-tauri" / "Cargo.toml").exists(), "src-tauri Cargo.toml missing"


# ---------------------------------------------------------------------------
# 3. Aether AI Runtime
# ---------------------------------------------------------------------------
def test_aether_runtime():
    """The Aether runtime imports and can select a provider with fallback."""
    from aether.runtime import AetherRuntime, Router

    runtime = AetherRuntime()
    assert isinstance(runtime.router, Router)

    selection = runtime.select_provider()
    assert "provider" in selection and selection["provider"]
    assert "fallback" in selection and isinstance(selection["fallback"], list)


# ---------------------------------------------------------------------------
# 4. Titan AI Platform integration
# ---------------------------------------------------------------------------
def test_titan_integration():
    """The Titan training/registry platform module is present and importable."""
    titan_dir = REPO_ROOT / "titan"
    assert titan_dir.is_dir(), "titan package directory missing"
    assert (titan_dir / "__init__.py").exists(), "titan is not a package"

    import titan  # noqa: F401
    import titan.registry  # noqa: F401  (dataset -> registry pipeline anchor)


# ---------------------------------------------------------------------------
# 5. Hardware platform — 20+ protocols + recovery workflows
# ---------------------------------------------------------------------------
def _discover_transports() -> set[str]:
    """Collect declared HAL transport identifiers from the driver sources."""
    drivers_dir = REPO_ROOT / "hardware" / "drivers"
    transports: set[str] = set()
    pattern = re.compile(r'^\s*transport\s*=\s*"([^"]+)"', re.MULTILINE)
    for path in drivers_dir.glob("*.py"):
        transports.update(pattern.findall(path.read_text(encoding="utf-8")))
    return transports


def test_hardware_platform():
    """The HAL exposes 20+ transport protocols and recovery workflows."""
    transports = _discover_transports()
    assert len(transports) >= 20, (
        f"expected >= 20 HAL protocols, found {len(transports)}: {sorted(transports)}"
    )

    # Recovery workflows must exist (mobile / BIOS-UEFI / embedded / ECU).
    recovery = REPO_ROOT / "hardware" / "recovery.py"
    assert recovery.exists(), "hardware/recovery.py missing"
    recovery_transports = {"edl", "odin", "dfu", "bios", "uefi", "ecu", "embedded_linux"}
    assert recovery_transports & transports, "no recovery-oriented transports declared"


# ---------------------------------------------------------------------------
# 6. Digital twin & knowledge platform
# ---------------------------------------------------------------------------
def test_digital_twin():
    """The digital twin builder is present and importable."""
    twin_dir = REPO_ROOT / "digital_twin"
    assert twin_dir.is_dir(), "digital_twin package directory missing"

    from digital_twin.twin import DeviceTwin, build_twin  # noqa: F401

    assert callable(build_twin)


# ---------------------------------------------------------------------------
# 7. Simulation & verification engine
# ---------------------------------------------------------------------------
def test_simulation_engine():
    """The simulation engine runs a failure-mode scenario with verification."""
    from simulation.engine import SimulationEngine

    engine = SimulationEngine()
    result = engine.simulate("dev-1", {"state": "online"}, failure_mode="disconnect")
    assert result["failure_mode"] == "disconnect"
    assert result["verification"]["passed"] is True


# ---------------------------------------------------------------------------
# 8. Plugin marketplace & SDK
# ---------------------------------------------------------------------------
def test_plugin_marketplace():
    """The marketplace and the developer SDK are both present."""
    marketplace_dir = REPO_ROOT / "marketplace"
    assert marketplace_dir.is_dir(), "marketplace package directory missing"

    import marketplace.plugin_repo  # noqa: F401
    import marketplace.governance  # noqa: F401

    assert (REPO_ROOT / "sdk").is_dir(), "sdk directory missing"


# ---------------------------------------------------------------------------
# 9. Enterprise collaboration (teams, remote hardware, billing)
# ---------------------------------------------------------------------------
def test_enterprise_collaboration():
    """The enterprise module provides teams, orgs, and cloud/remote support."""
    enterprise_dir = REPO_ROOT / "enterprise"
    assert enterprise_dir.is_dir(), "enterprise package directory missing"

    import enterprise.teams  # noqa: F401
    import enterprise.organizations  # noqa: F401
    import enterprise.cloud  # noqa: F401  (remote hardware / billing surface)


# ---------------------------------------------------------------------------
# 10. Autonomous engineering workflows with human-in-the-loop
# ---------------------------------------------------------------------------
def test_autonomous_workflows():
    """Autonomous agents exist with a human-in-the-loop proposal surface."""
    assert (REPO_ROOT / "autonomous").is_dir(), "autonomous package directory missing"
    assert (REPO_ROOT / "agents").is_dir(), "agents package directory missing"

    from autonomous.engineering_agent import EngineeringAgent  # noqa: F401
    import autonomous.proposals  # noqa: F401  (human approval checkpoints)


# ---------------------------------------------------------------------------
# 11. LTS, upgrade, backup & disaster recovery
# ---------------------------------------------------------------------------
def test_backup_dr():
    """Backup + restore tooling exists for disaster recovery."""
    scripts_dir = REPO_ROOT / "scripts"
    backup = scripts_dir / "backup.py"
    restore = scripts_dir / "restore.py"
    assert backup.exists(), "scripts/backup.py missing"
    assert restore.exists(), "scripts/restore.py missing"

    # The backup module must expose a callable backup routine.
    import importlib.util

    spec = importlib.util.spec_from_file_location("prometheus_backup", backup)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert hasattr(module, "backup") and callable(module.backup)


# ---------------------------------------------------------------------------
# 12. End-to-end workflow success >= 95%
# ---------------------------------------------------------------------------
def test_e2e_workflow_success(tmp_path):
    """Run a sample multi-step workflow and require >= 95% step success."""
    from workflow.runtime import WorkflowRuntime

    runtime = WorkflowRuntime(workflows_path=tmp_path / "workflows.json")
    workflow = runtime.create_workflow(
        name="Platform 1.0 E2E",
        steps=[
            {"action": "capability:device.connect", "description": "Connect device"},
            {"action": "capability:device.status", "description": "Identify device"},
            {"action": "agent:twin_builder", "description": "Build digital twin"},
            {"action": "capability:device.diagnose", "description": "Run diagnostics"},
            {"action": "memory:remember", "description": "Store knowledge"},
            {"action": "capability:device.read", "description": "Generate report"},
            {"action": "notify", "description": "Notify user"},
        ],
    )

    result = runtime.run(workflow["id"])
    assert result is not None, "workflow did not run"
    assert result["status"] == "completed", f"workflow status: {result['status']}"

    steps = result["steps"]
    done = sum(1 for s in steps if s["status"] == "done")
    success_rate = done / len(steps)
    assert success_rate >= 0.95, (
        f"end-to-end workflow success {success_rate:.0%} below 95% threshold"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
