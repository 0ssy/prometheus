"""Python wrapper around the Go gitsync binary.

Provides a thin, stdlib-only interface that invokes the compiled
``gitsync`` CLI (``cloud/cmd/gitsync``) to perform git-backed remote
workspace synchronisation with CRDT-based conflict resolution.

The Go binary owns all git and CRDT logic; this module only shells out to it,
serialises state to JSON files, and exposes a small service API.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional


DEFAULT_BIN = os.environ.get(
    "GITSYNC_BIN",
    shutil.which("gitsync") or "gitsync",
)


@dataclass
class SyncState:
    """Mirror of the Go ``SyncState`` payload."""

    node: dict[str, Any] = field(default_factory=dict)
    origin: str = ""
    at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"node": self.node, "origin": self.origin, "at": self.at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        return cls(
            node=data.get("node", {}),
            origin=data.get("origin", ""),
            at=data.get("at", 0),
        )


class GitSyncService:
    """Service wrapper that drives the Go ``gitsync`` binary."""

    def __init__(self, binary: str = DEFAULT_BIN) -> None:
        self.binary = binary

    def _run(
        self,
        *,
        local: str,
        remote: str,
        branch: str,
        node_id: str,
        mode: str,
        state_file: Optional[str] = None,
    ) -> dict[str, Any]:
        cmd = [
            self.binary,
            "--local",
            local,
            "--remote",
            remote,
            "--branch",
            branch,
            "--node",
            node_id,
            "--mode",
            mode,
        ]
        if state_file:
            cmd.extend(["--state", state_file])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"gitsync {mode} failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return self._parse_output(proc.stdout)

    @staticmethod
    def _parse_output(stdout: str) -> dict[str, Any]:
        lines = stdout.splitlines()
        if not lines:
            return {}
        json_lines = []
        started = False
        for line in lines:
            if line.strip().startswith("{"):
                started = True
            if started:
                json_lines.append(line)
        if not json_lines:
            return {}
        return json.loads("\n".join(json_lines))

    def pull(self, local: str, remote: str, branch: str, node_id: str) -> dict[str, Any]:
        return self._run(
            local=local, remote=remote, branch=branch, node_id=node_id, mode="pull"
        )

    def push(self, local: str, remote: str, branch: str, node_id: str) -> dict[str, Any]:
        return self._run(
            local=local, remote=remote, branch=branch, node_id=node_id, mode="push"
        )

    def merge(
        self,
        local: str,
        remote_state: SyncState,
        node_id: str,
        branch: str = "main",
        remote: str = "",
    ) -> SyncState:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False
        ) as fh:
            json.dump(remote_state.to_dict(), fh)
            state_path = fh.name
        try:
            result = self._run(
                local=local,
                remote=remote,
                branch=branch,
                node_id=node_id,
                mode="merge",
                state_file=state_path,
            )
        finally:
            os.unlink(state_path)
        return SyncState.from_dict(result.get("node", result))

    def sync(
        self,
        local: str,
        remote: str,
        branch: str,
        node_id: str,
        remote_state: Optional[SyncState] = None,
    ) -> SyncState:
        state_path = None
        cleanup = False
        if remote_state is not None:
            fh = tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False
            )
            json.dump(remote_state.to_dict(), fh)
            fh.close()
            state_path = fh.name
            cleanup = True
        try:
            result = self._run(
                local=local,
                remote=remote,
                branch=branch,
                node_id=node_id,
                mode="sync",
                state_file=state_path,
            )
        finally:
            if cleanup and state_path:
                os.unlink(state_path)
        return SyncState.from_dict(result.get("node", result))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Git-backed CRDT workspace sync")
    parser.add_argument("--local", required=True)
    parser.add_argument("--remote", default="")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--node", default="python-wrapper")
    parser.add_argument(
        "--mode",
        choices=["sync", "pull", "push", "merge"],
        default="sync",
    )
    parser.add_argument("--state", default=None)
    args = parser.parse_args()

    service = GitSyncService()
    if args.mode == "merge" and args.state:
        with open(args.state) as f:
            remote_state = SyncState.from_dict(json.load(f))
        out = service.merge(args.local, remote_state, args.node, args.branch, args.remote)
    elif args.mode in ("pull", "push"):
        out = getattr(service, args.mode)(
            args.local, args.remote, args.branch, args.node
        )
    else:
        out = service.sync(args.local, args.remote, args.branch, args.node)
    print(json.dumps(out.to_dict(), indent=2))
