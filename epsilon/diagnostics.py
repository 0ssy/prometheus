from __future__ import annotations


class DiagnosticsEngine:
    def assess(self, device_snapshot: dict) -> dict:
        battery = device_snapshot.get("battery_health", 1.0)
        storage = device_snapshot.get("storage_health", 1.0)
        thermal = device_snapshot.get("thermal_state", "normal")
        connectivity = device_snapshot.get("connectivity", "online")
        overall = "ok"
        if battery < 0.4 or storage < 0.4 or thermal == "hot" or connectivity != "online":
            overall = "degraded"
        return {
            "battery": battery,
            "storage": storage,
            "thermal_state": thermal,
            "connectivity": connectivity,
            "overall": overall,
        }
