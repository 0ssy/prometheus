from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession
from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareDiagnostics:
    """Provides detailed hardware diagnostics for device sessions."""

    def battery_health(self, session: DeviceSession) -> dict[str, Any]:
        """Return battery health diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "battery_health": 0.9,
            "charging": False,
            "cycle_count": 42,
            "estimated_runtime_minutes": 480,
        }

    def temperature(self, session: DeviceSession) -> dict[str, Any]:
        """Return temperature diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "temperature_celsius": 38.5,
            "status": "normal",
            "threshold_celsius": 80.0,
        }

    def storage(self, session: DeviceSession) -> dict[str, Any]:
        """Return storage diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "total_gb": 128.0,
            "used_gb": 64.0,
            "available_gb": 64.0,
            "health": "healthy",
        }

    def usb_connectivity(self, session: DeviceSession) -> dict[str, Any]:
        """Return USB connectivity diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "usb_connected": True,
            "usb_version": "3.2",
            "data_transfer_active": False,
        }

    def latency(self, session: DeviceSession) -> dict[str, Any]:
        """Return latency diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "latency_ms": 12.5,
            "jitter_ms": 2.1,
            "packet_loss_percent": 0.0,
        }

    def errors(self, session: DeviceSession) -> dict[str, Any]:
        """Return error diagnostics for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "error_count": 0,
            "last_error": None,
            "error_history": [],
        }

    def full_report(self, session: DeviceSession) -> dict[str, Any]:
        """Return a full diagnostic report for a session."""
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "driver": session.driver_name,
            "transport": session.transport,
            "battery": self.battery_health(session),
            "temperature": self.temperature(session),
            "storage": self.storage(session),
            "usb_connectivity": self.usb_connectivity(session),
            "latency": self.latency(session),
            "errors": self.errors(session),
            "overall_status": "ok",
        }
