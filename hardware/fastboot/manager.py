"""Fastboot capability — Hardware API.

The manager discovers devices in fastboot mode, tracks connect/disconnect via
a hot-plug monitor, enforces the fastboot permission policy, and exposes the
core fastboot operations: getvar, unlock, lock, flash, erase, boot, reboot.
Real discovery/execution uses the `fastboot` CLI when present; otherwise a
deterministic simulated device is used so the platform and its tests run
anywhere.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.event_bus import event_bus as default_event_bus
from core.logger import get_logger
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from hardware.fastboot.permissions import FastbootCapability, FastbootPermissionPolicy

logger = get_logger(__name__)


@dataclass
class FastbootDevice:
    serial: str
    state: str = "fastboot"
    product: Optional[str] = None
    model: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    unlocked: bool = False
    connected: bool = True

    def label(self) -> str:
        if self.model and self.product:
            return f"{self.model} ({self.product})"
        if self.model:
            return self.model
        if self.product:
            return self.product
        return self.serial

    def to_dict(self) -> dict[str, Any]:
        return {
            "serial": self.serial,
            "state": self.state,
            "product": self.product,
            "model": self.model,
            "vendor_id": f"0x{self.vendor_id:04x}" if self.vendor_id is not None else None,
            "product_id": f"0x{self.product_id:04x}" if self.product_id is not None else None,
            "unlocked": self.unlocked,
            "connected": self.connected,
        }


def _build_simulated_devices() -> list[FastbootDevice]:
    return [
        FastbootDevice(
            serial="fastboot-abcdef123456",
            state="fastboot",
            product="fastboot_simulator",
            model="Simulator",
            vendor_id=0x18D1,
            product_id=0x4EE7,
            unlocked=False,
        )
    ]


class FastbootManager:
    """Hardware API for the Fastboot capability."""

    def __init__(self, event_bus: Any = None, policy: Optional[FastbootPermissionPolicy] = None) -> None:
        self._event_bus = event_bus or default_event_bus
        self._policy = policy if policy is not None else FastbootPermissionPolicy(default_allow=False)
        self._devices: dict[str, FastbootDevice] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 2.0
        self._real_backend = shutil.which("fastboot") is not None
        if self._real_backend:
            logger.info("Fastboot capability: using real backend (fastboot CLI found)")
        else:
            logger.info("Fastboot capability: fastboot CLI not found; using simulated")

    # -- discovery -------------------------------------------------------

    def enumerate(self) -> list[FastbootDevice]:
        if self._real_backend:
            devices = self._enumerate_real()
        else:
            devices = _build_simulated_devices()
        with self._lock:
            self._devices = {d.serial: d for d in devices}
        return list(self._devices.values())

    def _enumerate_real(self) -> list[FastbootDevice]:
        try:
            out = subprocess.run(
                ["fastboot", "devices"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except Exception as exc:  # pragma: no cover - depends on host
            logger.warning(f"Fastboot real enumeration failed: {exc}")
            return _build_simulated_devices()

        devices: list[FastbootDevice] = []
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "fastboot"
            devices.append(
                FastbootDevice(
                    serial=serial,
                    state=state,
                    vendor_id=0x18D1 if state == "fastboot" else None,
                    product_id=0x4EE7 if state == "fastboot" else None,
                )
            )
        return devices

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._devices.values()]

    def get(self, serial: str) -> Optional[FastbootDevice]:
        with self._lock:
            return self._devices.get(serial)

    # -- permissions -----------------------------------------------------

    def policy(self) -> FastbootPermissionPolicy:
        return self._policy

    def can_access(
        self,
        capability: FastbootCapability,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        return self._policy.check(capability, serial, vendor_id, product_id)

    # -- operations ------------------------------------------------------

    def _requires(self, serial: str, capability: FastbootCapability) -> Optional[str]:
        with self._lock:
            dev = self._devices.get(serial)
        if dev is None:
            devs = self.enumerate()
            dev = next((d for d in devs if d.serial == serial), None)
        vid = dev.vendor_id if dev else None
        pid = dev.product_id if dev else None
        ok, why = self.can_access(capability, serial, vid, pid)
        if not ok:
            return why
        return None

    def getvar(self, serial: str, variable: str = "all") -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.GETVAR)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "getvar", variable],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {
                    "status": "ok",
                    "serial": serial,
                    "variable": variable,
                    "output": out.stdout,
                    "stderr": out.stderr,
                }
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {
            "status": "simulated",
            "serial": serial,
            "variable": variable,
            "value": "simulated-value",
        }

    def unlock(self, serial: str) -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.UNLOCK)
        if deny:
            return {"status": "denied", "reason": deny}
        with self._lock:
            dev = self._devices.get(serial)
            if dev is not None:
                dev.unlocked = True
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "flashing", "unlock"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "unlocked": True}

    def lock(self, serial: str) -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.LOCK)
        if deny:
            return {"status": "denied", "reason": deny}
        with self._lock:
            dev = self._devices.get(serial)
            if dev is not None:
                dev.unlocked = False
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "flashing", "lock"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "unlocked": False}

    def flash(self, serial: str, partition: str, image: str) -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.FLASH)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "flash", partition, image],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "partition": partition, "image": image}

    def erase(self, serial: str, partition: str) -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.ERASE)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "erase", partition],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "partition": partition}

    def boot(self, serial: str, image: str) -> dict[str, Any]:
        deny = self._requires(serial, FastbootCapability.BOOT)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["fastboot", "-s", serial, "boot", image],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "image": image}

    def reboot(self, serial: str, mode: str = "normal") -> dict[str, Any]:
        cap = FastbootCapability.REBOOT
        deny = self._requires(serial, cap)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                cmd = ["fastboot", "-s", serial, "reboot"]
                if mode == "bootloader":
                    cmd.append("bootloader")
                elif mode == "recovery":
                    cmd.append("recovery")
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "mode": mode}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "mode": mode}

    # -- hot-plug monitoring --------------------------------------------

    def start_monitor(self, interval: float = 2.0) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_interval = interval
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="fastboot-monitor", daemon=True
        )
        self._monitor_thread.start()
        logger.info("Fastboot hot-plug monitor started")

    def stop_monitor(self) -> None:
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self._monitor_interval + 1.0)
            self._monitor_thread = None
        logger.info("Fastboot hot-plug monitor stopped")

    def poll_once(self) -> None:
        previous = set(self._devices.keys())
        current_devices = self.enumerate()
        current = {d.serial for d in current_devices}
        dev_by_serial = {d.serial: d for d in current_devices}
        for serial in current - previous:
            dev = dev_by_serial.get(serial)
            if dev:
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=serial, transport="fastboot")
                )
                logger.info(f"Fastboot device connected: {dev.label()}")
        for serial in previous - current:
            self._event_bus.publish(DeviceDisconnectedEvent(device_id=serial))
            logger.info(f"Fastboot device disconnected: {serial}")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            self._stop_event.wait(self._monitor_interval)

    def on_change(self, handler: Callable[[str, bool], None]) -> None:
        def _connected(ev: DeviceConnectedEvent) -> None:
            handler(ev.device_id, True)

        def _disconnected(ev: DeviceDisconnectedEvent) -> None:
            handler(ev.device_id, False)

        self._event_bus.subscribe("hardware.device.connected", _connected)
        self._event_bus.subscribe("hardware.device.disconnected", _disconnected)


_default_manager: Optional[FastbootManager] = None


def get_fastboot_manager() -> FastbootManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = FastbootManager()
    return _default_manager
