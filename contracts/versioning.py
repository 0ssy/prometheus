from __future__ import annotations


CONTRACT_VERSION = "1.0.0"


def _parse_semver(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semantic version '{version}'")
    try:
        major, minor, patch = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Invalid semantic version '{version}'") from exc
    return major, minor, patch


def is_contract_compatible(required_version: str, runtime_version: str = CONTRACT_VERSION) -> bool:
    required_major, required_minor, required_patch = _parse_semver(required_version)
    runtime_major, runtime_minor, runtime_patch = _parse_semver(runtime_version)
    if required_major != runtime_major:
        return False
    if (runtime_minor, runtime_patch) < (required_minor, required_patch):
        return False
    return True


def validate_contract_compatibility(
    required_version: str, runtime_version: str = CONTRACT_VERSION
) -> None:
    if is_contract_compatible(required_version, runtime_version):
        return
    raise RuntimeError(
        f"Incompatible contract version. Plugin requires {required_version}, "
        f"runtime provides {runtime_version}."
    )
