from __future__ import annotations


from core.logger import get_logger

logger = get_logger(__name__)


class CapabilityMapper:
    """Maps hardware capabilities to Prometheus capability names."""

    def __init__(self) -> None:
        self._mappings: dict[str, dict[str, str]] = {}

    def register_mapping(self, interface_name: str, capability_map: dict[str, str]) -> None:
        """Register a capability mapping for an interface."""
        self._mappings[interface_name] = capability_map
        logger.info(f"Registered capability mapping for interface: {interface_name}")

    def map_interface_capabilities(self, interface_name: str, capabilities: list[str]) -> list[str]:
        """Map a list of interface capabilities to Prometheus capability names."""
        mapping = self._mappings.get(interface_name, {})
        return [mapping.get(cap, cap) for cap in capabilities]

    def get_prometheus_capabilities(self, interface_name: str) -> list[str]:
        """Return the mapped Prometheus capabilities for an interface."""
        return list(self._mappings.get(interface_name, {}).values())
