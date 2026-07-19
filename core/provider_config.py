"""
Provider configuration persistence.

Stores user-configured LLM providers in ~/.prometheus/providers.json.
"""

import json
import os
from pathlib import Path

PROVIDERS_DIR = Path.home() / ".prometheus"
PROVIDERS_FILE = PROVIDERS_DIR / "providers.json"


def _ensure_dir() -> None:
    PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)


def load_providers() -> list[dict]:
    _ensure_dir()
    if not PROVIDERS_FILE.exists():
        return []
    try:
        data = json.loads(PROVIDERS_FILE.read_text())
        return data.get("providers", []) if isinstance(data, dict) else []
    except Exception:
        return []


def save_providers(providers: list[dict]) -> None:
    _ensure_dir()
    PROVIDERS_FILE.write_text(json.dumps({"providers": providers}, indent=2))


def add_provider(provider: dict) -> list[dict]:
    providers = load_providers()
    existing = [i for i, p in enumerate(providers) if p.get("id") == provider.get("id")]
    if existing:
        providers[existing[0]] = provider
    else:
        providers.append(provider)
    save_providers(providers)
    return providers


def remove_provider(provider_id: str) -> list[dict]:
    providers = [p for p in load_providers() if p.get("id") != provider_id]
    save_providers(providers)
    return providers
