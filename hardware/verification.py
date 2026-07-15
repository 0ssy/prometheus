from __future__ import annotations

from typing import Any

from hardware.session import DeviceSession, DeviceSessionManager
from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareVerifier:
    """Verifies driver, session, and firmware integrity."""

    def __init__(self, session_manager: DeviceSessionManager | None = None) -> None:
        self._session_manager = session_manager or DeviceSessionManager()

    def verify_driver(self, driver: HardwareDriver) -> dict[str, Any]:
        """Verify a driver instance is healthy and responsive."""
        try:
            health = driver.health()
            diagnostics = driver.diagnostics()
            return {
                "driver": driver.name,
                "transport": driver.transport,
                "verified": True,
                "health": health,
                "diagnostics": diagnostics,
            }
        except Exception as exc:
            logger.warning("Driver verification failed for %s: %s", driver.name, exc)
            return {
                "driver": driver.name,
                "transport": driver.transport,
                "verified": False,
                "error": str(exc),
            }

    def verify_session(self, session: DeviceSession) -> dict[str, Any]:
        """Verify a session is still active and valid."""
        stored = self._session_manager.get_session(session.session_id)
        if stored is None:
            return {
                "session_id": session.session_id,
                "verified": False,
                "reason": "session_not_found",
            }
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "verified": True,
            "driver_name": stored.driver_name,
            "transport": stored.transport,
        }

    def verify_firmware(self, firmware_data: bytes, signature: bytes | None = None, public_key: bytes | None = None) -> dict[str, Any]:
        """Verify firmware integrity and signature."""
        if not firmware_data:
            return {"verified": False, "reason": "empty_firmware_data"}

        if signature is not None and public_key is not None:
            try:
                from engineering.crypto_verify import verify_ed25519
                valid = verify_ed25519(public_key, signature, firmware_data)
                return {
                    "verified": valid,
                    "signature_check": "passed" if valid else "failed",
                    "size_bytes": len(firmware_data),
                }
            except Exception as exc:
                return {
                    "verified": False,
                    "signature_check": "error",
                    "error": str(exc),
                    "size_bytes": len(firmware_data),
                }

        return {
            "verified": True,
            "signature_check": "skipped",
            "size_bytes": len(firmware_data),
        }
