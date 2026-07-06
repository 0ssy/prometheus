from __future__ import annotations

from typing import Any


class KernelRegistry:
    def __init__(self):
        self._entries: dict[str, Any] = {}

    def register(self, name: str, value: Any) -> None:
        self._entries[name] = value

    def get(self, name: str) -> Any:
        if name not in self._entries:
            raise KeyError(f"Kernel registry has no entry '{name}'")
        return self._entries[name]

    def list_entries(self) -> list[str]:
        return sorted(self._entries.keys())
