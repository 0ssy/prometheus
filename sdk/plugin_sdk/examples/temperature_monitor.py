from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

from sdk.plugin_sdk.decorators import capability, plugin, requires_permission
from sdk.plugin_sdk.interfaces import PluginContext, PluginResult

logger = get_logger(__name__)


@plugin
class TemperatureMonitor:
    name = "temperature_monitor"
    version = "1.0.0"
    description = "Simulated ambient and core temperature monitoring."
    author = "Olympus SDK"
    capabilities = ["read_temperature"]
    dependencies = []
    entrypoint = "sdk.plugin_sdk.examples.temperature_monitor:TemperatureMonitor"

    def initialize(self, context: PluginContext) -> None:
        self.context = context
        logger.info("TemperatureMonitor initialized")

    @capability
    @requires_permission("sensor.read")
    def read_temperature(self, sensor_id: str = "core-0") -> PluginResult:
        """Read a simulated temperature sensor value."""
        return PluginResult.ok(
            {
                "sensor_id": sensor_id,
                "temperature_c": 42.3,
                "humidity_percent": 38.1,
                "timestamp": context_now(),
            },
            read_by=self.manifest.name,
        )

    def health(self) -> dict[str, Any]:
        return {"plugin": self.manifest.name, "status": "healthy", "capabilities": self.manifest.capabilities}


def context_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
