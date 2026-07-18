"""Packaging and signing helpers for Prometheus developer tooling.

Creates signed zip packages of plugins, agents, and drivers using a
SHA256-based signature and verifies their integrity on load.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from prometheus_cli.scaffold import DIST_DIR

SIGNATURE_FILE = "SIGNATURE.json"

_ALGO = "sha256"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sign_manifest(member_hashes: dict[str, str], secret: str) -> str:
    payload = json.dumps(member_hashes, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256()
    h.update(secret.encode("utf-8"))
    h.update(payload.encode("utf-8"))
    return h.hexdigest()


def _resolve_target(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (DIST_DIR.parent if DIST_DIR else Path.cwd()) / p
    return p


def resolve_package_path(path: str | Path) -> Path:
    return _resolve_target(path)


def pack(path: str | Path, secret: str | None = None, dist_dir: Path | None = None) -> Path:
    """Create a signed zip package of the component at `path`.

    Returns the path to the produced ``.zip`` package in the dist directory.
    """
    source = _resolve_target(path)
    if not source.exists():
        raise FileNotFoundError(f"not found: {source}")

    out_dir = dist_dir or DIST_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    package_name = source.name
    zip_path = out_dir / f"{package_name}.zip"

    secret = secret or _default_secret()

    member_hashes: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in sorted(source.rglob("*")):
            if fp.is_file():
                arcname = str(fp.relative_to(source))
                zf.write(fp, arcname=arcname)
                member_hashes[arcname] = _sha256_file(fp)

        signature = {
            "algorithm": _ALGO,
            "component": package_name,
            "members": member_hashes,
            "signature": _sign_manifest(member_hashes, secret),
        }
        zf.writestr(SIGNATURE_FILE, json.dumps(signature, indent=2) + "\n")

    return zip_path


def verify(path: str | Path, secret: str | None = None) -> dict:
    """Verify a signed package. Returns a result dict.

    Keys: ``ok`` (bool), ``component``, ``member_count``, ``errors`` (list).
    """
    zip_path = _resolve_target(path)
    if not zip_path.exists():
        return {"ok": False, "errors": [f"not found: {zip_path}"]}

    secret = secret or _default_secret()
    errors: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        if SIGNATURE_FILE not in names:
            return {"ok": False, "errors": [f"missing {SIGNATURE_FILE} signature"]}

        try:
            signature = json.loads(zf.read(SIGNATURE_FILE).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"ok": False, "errors": [f"invalid signature file: {exc}"]}

        expected = signature.get("signature")
        members = signature.get("members", {})
        computed = _sign_manifest(members, secret)
        if not expected or not hmac_compare(computed, expected):
            errors.append("signature mismatch — package tampered or wrong key")

        for arcname, expected_hash in members.items():
            if arcname not in names:
                errors.append(f"missing member: {arcname}")
                continue
            data = zf.read(arcname)
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected_hash:
                errors.append(f"hash mismatch for {arcname}")

    return {
        "ok": len(errors) == 0,
        "component": signature.get("component"),
        "member_count": len(members),
        "algorithm": signature.get("algorithm", _ALGO),
        "errors": errors,
    }


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time comparison of two hex signatures."""
    return hashlib.compare_digest(a, b)


def _default_secret() -> str:
    """Returns the platform's packaging signing secret.

    Falls back to a deterministic default when no secret is configured so
    that locally produced and verified packages remain consistent.
    """
    try:
        from core.config import config

        secret = getattr(config, "package_signing_secret", None)
        if secret:
            return str(secret)
    except Exception:  # noqa: BLE001
        pass
    return "prometheus-dev-signing-secret"
