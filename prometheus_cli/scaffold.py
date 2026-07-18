"""Scaffolding helpers for Prometheus developer tooling.

Provides reusable functions used by the CLI to generate new plugins,
agents, and drivers from templates.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PLUGINS_DIR = PROJECT_ROOT / "plugins" / "installed"
AGENTS_DIR = PROJECT_ROOT / "agents" / "installed"
DRIVERS_DIR = PROJECT_ROOT / "drivers"
DIST_DIR = PROJECT_ROOT / "dist"


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _class_name(name: str) -> str:
    parts = re.split(r"[-_\s]+", name)
    return "".join(p.title() for p in parts if p)


def scaffold_plugin(name: str) -> Path:
    name = _normalize_name(name)
    target = PLUGINS_DIR / name
    target.mkdir(parents=True, exist_ok=True)

    cls = _class_name(name)
    init = target / "__init__.py"
    if not init.exists():
        init.write_text(
            f'"""Plugin: {name}"""\n\n'
            f"from plugins.base import PrometheusPlugin\n\n\n"
            f"class {cls}Plugin(PrometheusPlugin):\n"
            f'    name = "{name}"\n'
            f'    version = "0.1.0"\n\n'
            f"    def on_load(self) -> None:\n"
            f"        pass\n\n"
            f"    def run(self, context: dict) -> dict:\n"
            f"        raise NotImplementedError()\n",
            encoding="utf-8",
        )

    manifest = target / "manifest.json"
    if not manifest.exists():
        manifest.write_text(
            json.dumps(
                {
                    "name": name,
                    "version": "0.1.0",
                    "description": f"Prometheus plugin: {name}",
                    "entrypoint": "__init__.py",
                    "capabilities": [],
                    "permissions": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Plugin: {name}\n\n"
            f"Scaffolded by `prometheus new plugin {name}`.\n\n"
            "## Description\n\n"
            f"The `{name}` plugin extends Prometheus with custom capabilities.\n\n"
            "## Usage\n\n"
            "1. Implement the `run` method in `__init__.py`.\n"
            "2. Declare capabilities/permissions in `manifest.json`.\n"
            "3. Restart the platform or hot-reload plugins.\n",
            encoding="utf-8",
        )

    return target


def scaffold_agent(name: str) -> Path:
    name = _normalize_name(name)
    target = AGENTS_DIR / name
    target.mkdir(parents=True, exist_ok=True)

    cls = _class_name(name)
    init = target / "__init__.py"
    if not init.exists():
        init.write_text(
            f'"""Agent: {name}"""\n\n'
            f"from agents.base import PrometheusAgent\n\n\n"
            f"class {cls}Agent(PrometheusAgent):\n"
            f'    name = "{name}"\n\n'
            f"    def perform(self, task: dict, context: dict) -> dict:\n"
            f"        raise NotImplementedError()\n",
            encoding="utf-8",
        )

    manifest = target / "manifest.json"
    if not manifest.exists():
        manifest.write_text(
            json.dumps(
                {
                    "name": name,
                    "version": "0.1.0",
                    "description": f"Prometheus agent: {name}",
                    "entrypoint": "__init__.py",
                    "capabilities": [],
                    "permissions": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# Agent: {name}\n\n"
            f"Scaffolded by `prometheus new agent {name}`.\n\n"
            "## Description\n\n"
            f"The `{name}` agent performs autonomous tasks on the platform.\n\n"
            "## Usage\n\n"
            "1. Implement the `perform` method in `__init__.py`.\n"
            "2. Declare capabilities/permissions in `manifest.json`.\n"
            "3. Dispatch the agent via the agent manager.\n",
            encoding="utf-8",
        )

    return target


def scaffold_driver(name: str) -> Path:
    name = _normalize_name(name)
    target = DRIVERS_DIR / name
    target.mkdir(parents=True, exist_ok=True)

    src = target / "src"
    src.mkdir(parents=True, exist_ok=True)

    cls = _class_name(name)
    cargo = target / "Cargo.toml"
    if not cargo.exists():
        cargo.write_text(
            f"[package]\n"
            f'name = "{name.replace("-", "_")}"\n'
            f'version = "0.1.0"\n'
            f'edition = "2021"\n'
            f'description = "Prometheus hardware driver: {name}"\n\n'
            f"[lib]\n"
            f'name = "{name.replace("-", "_")}"\n'
            f'path = "src/lib.rs"\n\n'
            f"[dependencies]\n"
            f'hal_core = {{ path = "../../crates/hal_core" }}\n',
            encoding="utf-8",
        )

    lib = src / "lib.rs"
    if not lib.exists():
        lib.write_text(
            f"// Driver: {name}\n\n"
            f"use hal_core::{{Hal, ProbeResult, Transport}};\n\n"
            f"pub struct {cls}Driver;\n\n"
            f"impl Hal for {cls}Driver {{\n"
            f"    fn probe(&self, _transport: Transport, _target: &str) -> ProbeResult {{\n"
            f"        todo!(\"implement probe for {name}\")\n"
            f"    }}\n"
            f"}}\n",
            encoding="utf-8",
        )

    manifest = target / "manifest.json"
    if not manifest.exists():
        manifest.write_text(
            json.dumps(
                {
                    "name": name,
                    "version": "0.1.0",
                    "description": f"Prometheus driver: {name}",
                    "language": "rust",
                    "entrypoint": "src/lib.rs",
                    "capabilities": [],
                    "permissions": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return target
