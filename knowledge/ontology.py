from __future__ import annotations


class OntologyRegistry:
    def __init__(self):
        self._parents: dict[str, str] = {}
        self._bootstrap_defaults()

    def register(self, child: str, parent: str) -> None:
        self._parents[child] = parent

    def is_a(self, child: str, ancestor: str) -> bool:
        current = child
        seen = set()
        while current in self._parents and current not in seen:
            if current == ancestor:
                return True
            seen.add(current)
            current = self._parents[current]
        return current == ancestor

    def lineage(self, child: str) -> list[str]:
        lineage = [child]
        current = child
        seen = set()
        while current in self._parents and current not in seen:
            seen.add(current)
            parent = self._parents[current]
            lineage.append(parent)
            current = parent
        return lineage

    def _bootstrap_defaults(self) -> None:
        self.register("AndroidDevice", "Device")
        self.register("Phone", "AndroidDevice")
        self.register("Capability", "Entity")
        self.register("CommunicationCapability", "Capability")
        self.register("USBCapability", "CommunicationCapability")
        self.register("ADBCapability", "USBCapability")
