"""Python wrapper around the Go tunnel CLI.

Provides a thin, stdlib-only interface that invokes the compiled
``tunnel`` service (``cloud/cmd/tunnel``) to manage SSH-based secure
tunnels for remote hardware access.

The Go binary owns all tunnel and SSH logic; this module only shells out to it,
parses JSON responses, and exposes a small service API.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional


DEFAULT_BIN = os.environ.get(
    "TUNNEL_BIN",
    shutil.which("tunnel") or "tunnel",
)


@dataclass
class TunnelConfig:
    """Configuration for creating a new secure tunnel."""

    ssh_addr: str
    ssh_user: str
    remote_addr: str
    ssh_password: str = ""
    ssh_key_path: str = ""


@dataclass
class TunnelStatus:
    """Mirror of the Go ``TunnelStatus`` payload."""

    id: str = ""
    local_addr: str = ""
    remote_addr: str = ""
    ssh_addr: str = ""
    ssh_user: str = ""
    created_at: str = ""
    closed_at: Optional[str] = None
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "local_addr": self.local_addr,
            "remote_addr": self.remote_addr,
            "ssh_addr": self.ssh_addr,
            "ssh_user": self.ssh_user,
            "created_at": self.created_at,
            "active": self.active,
        }
        if self.closed_at is not None:
            out["closed_at"] = self.closed_at
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TunnelStatus":
        return cls(
            id=data.get("id", ""),
            local_addr=data.get("local_addr", ""),
            remote_addr=data.get("remote_addr", ""),
            ssh_addr=data.get("ssh_addr", ""),
            ssh_user=data.get("ssh_user", ""),
            created_at=data.get("created_at", ""),
            closed_at=data.get("closed_at"),
            active=data.get("active", False),
        )


@dataclass
class CreateTunnelResult:
    """Result of a successful tunnel creation."""

    id: str = ""
    local_addr: str = ""
    remote_addr: str = ""
    ssh_addr: str = ""
    ssh_user: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreateTunnelResult":
        return cls(
            id=data.get("id", ""),
            local_addr=data.get("local_addr", ""),
            remote_addr=data.get("remote_addr", ""),
            ssh_addr=data.get("ssh_addr", ""),
            ssh_user=data.get("ssh_user", ""),
            created_at=data.get("created_at", ""),
        )


class TunnelService:
    """Service wrapper that drives the Go ``tunnel`` CLI."""

    def __init__(self, binary: str = DEFAULT_BIN) -> None:
        self.binary = binary

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        cmd = [
            self.binary,
            "--endpoint",
            endpoint,
            "--payload",
            json.dumps(payload),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"tunnel {endpoint} failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return self._parse_output(proc.stdout)

    def _get(self, endpoint: str) -> dict[str, Any]:
        cmd = [self.binary, "--endpoint", endpoint]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"tunnel {endpoint} failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return self._parse_output(proc.stdout)

    @staticmethod
    def _parse_output(stdout: str) -> dict[str, Any]:
        lines = stdout.splitlines()
        if not lines:
            return {}
        json_lines: list[str] = []
        started = False
        for line in lines:
            stripped := line.strip()
            if stripped.startswith("{"):
                started = True
            if started:
                json_lines.append(line)
        if not json_lines:
            return {}
        return json.loads("\n".join(json_lines))

    def create_tunnel(self, cfg: TunnelConfig) -> CreateTunnelResult:
        payload = {
            "ssh_addr": cfg.ssh_addr,
            "ssh_user": cfg.ssh_user,
            "ssh_password": cfg.ssh_password,
            "ssh_key_path": cfg.ssh_key_path,
            "remote_addr": cfg.remote_addr,
        }
        resp = self._post("/v1/tunnel/create", payload)
        return CreateTunnelResult.from_dict(resp)

    def close_tunnel(self, tunnel_id: str) -> dict[str, Any]:
        return self._post("/v1/tunnel/close", {"id": tunnel_id})

    def list_tunnels(self) -> list[TunnelStatus]:
        resp = self._get("/v1/tunnel/list")
        raw = resp.get("tunnels", [])
        if not isinstance(raw, list):
            return []
        out: list[TunnelStatus] = []
        for item in raw:
            if isinstance(item, dict):
                out.append(TunnelStatus.from_dict(item))
        return out

    def health(self) -> dict[str, Any]:
        resp = self._get("/health")
        return resp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SSH tunnel management service wrapper")
    parser.add_argument("--endpoint", required=False, default="")
    parser.add_argument("--payload", required=False, default=None)
    parser.add_argument(
        "--mode",
        choices=["create", "close", "list", "health"],
        default="health",
    )
    args = parser.parse_args()

    service = TunnelService()

    if args.endpoint:
        if args.mode == "create":
            payload = json.loads(args.payload) if args.payload else {}
            out = service.create_tunnel(TunnelConfig(**payload))
        elif args.mode == "close":
            payload = json.loads(args.payload) if args.payload else {}
            out = service.close_tunnel(payload.get("id", ""))
        elif args.mode == "list":
            out = [t.to_dict() for t in service.list_tunnels()]
        elif args.mode == "health":
            out = service.health()
        else:
            out = {}
    else:
        if args.mode == "create":
            raise RuntimeError("--payload is required for create mode")
        elif args.mode == "close":
            raise RuntimeError("--payload is required for close mode")
        elif args.mode == "list":
            out = [t.to_dict() for t in service.list_tunnels()]
        elif args.mode == "health":
            out = service.health()
        else:
            out = {}

    print(json.dumps(out, indent=2))
