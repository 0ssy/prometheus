"""ADB (Android Debug Bridge) capability — Hardware API.

The manager discovers Android devices, tracks connect/disconnect via a
hot-plug monitor, enforces the ADB permission policy, and exposes the core
ADB operations: shell, logcat, push, pull, install apk, reboot, recovery,
sideload. Real discovery/execution uses the `adb` CLI when present; otherwise
a deterministic simulated device is used so the platform and its tests run
anywhere.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.event_bus import event_bus as default_event_bus
from core.logger import get_logger
from hardware.events import DeviceConnectedEvent, DeviceDisconnectedEvent
from hardware.adb.permissions import AdbCapability, AdbPermissionPolicy

logger = get_logger(__name__)


@dataclass
class AdbDevice:
    serial: str
    state: str = "device"
    model: Optional[str] = None
    product: Optional[str] = None
    device: Optional[str] = None
    android_version: Optional[str] = None
    sdk: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
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
            "model": self.model,
            "product": self.product,
            "device": self.device,
            "android_version": self.android_version,
            "sdk": self.sdk,
            "vendor_id": f"0x{self.vendor_id:04x}" if self.vendor_id is not None else None,
            "product_id": f"0x{self.product_id:04x}" if self.product_id is not None else None,
            "connected": self.connected,
        }


def _build_simulated_devices() -> list[AdbDevice]:
    return [
        AdbDevice(
            serial="adb-1234567890",
            state="device",
            model="Pixel Simulator",
            product="sdk_gphone64_x86_64",
            device="simulator",
            android_version="14",
            sdk="34",
            vendor_id=0x18D1,
            product_id=0x4EE7,
        )
    ]


class ADBManager:
    """Hardware API for the ADB capability."""

    def __init__(self, event_bus: Any = None, policy: Optional[AdbPermissionPolicy] = None) -> None:
        self._event_bus = event_bus or default_event_bus
        self._policy = policy if policy is not None else AdbPermissionPolicy(default_allow=False)
        self._devices: dict[str, AdbDevice] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 2.0
        self._real_backend = shutil.which("adb") is not None
        if self._real_backend:
            logger.info("ADB capability: using real backend (adb CLI found)")
        else:
            logger.info("ADB capability: adb CLI not found; using simulated")

    # -- discovery -------------------------------------------------------

    def enumerate(self) -> list[AdbDevice]:
        if self._real_backend:
            devices = self._enumerate_real()
        else:
            devices = _build_simulated_devices()
        with self._lock:
            self._devices = {d.serial: d for d in devices}
        return list(self._devices.values())

    def _enumerate_real(self) -> list[AdbDevice]:
        try:
            out = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except Exception as exc:  # pragma: no cover - depends on host
            logger.warning(f"ADB real enumeration failed: {exc}")
            return _build_simulated_devices()

        devices: list[AdbDevice] = []
        for line in out.stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            model = product = device = None
            for kv in parts[2:]:
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    if k == "model":
                        model = v
                    elif k == "product":
                        product = v
                    elif k == "device":
                        device = v
            devices.append(
                AdbDevice(
                    serial=serial,
                    state=state,
                    model=model,
                    product=product,
                    device=device,
                    vendor_id=0x18D1 if state == "device" else None,
                    product_id=0x4EE7 if state == "device" else None,
                )
            )
        return devices

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._devices.values()]

    def get(self, serial: str) -> Optional[AdbDevice]:
        with self._lock:
            return self._devices.get(serial)

    # -- permissions -----------------------------------------------------

    def policy(self) -> AdbPermissionPolicy:
        return self._policy

    def can_access(
        self,
        capability: AdbCapability,
        serial: str,
        vendor_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        return self._policy.check(capability, serial, vendor_id, product_id)

    # -- operations ------------------------------------------------------

    def _requires(self, serial: str, capability: AdbCapability) -> Optional[str]:
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

    def shell(self, serial: str, command: str) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.SHELL)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "shell", command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {"status": "ok", "serial": serial, "output": out.stdout, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "command": command, "output": ""}

    def logcat(self, serial: str, lines: int = 100) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.LOGCAT)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "logcat", "-d", "-t", str(lines)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {"status": "ok", "serial": serial, "log": out.stdout}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {
            "status": "simulated",
            "serial": serial,
            "log": f"[simulated logcat for {serial}, {lines} lines]",
        }

    def push(self, serial: str, local: str, remote: str) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.PUSH)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "push", local, remote],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "local": local, "remote": remote}

    def pull(self, serial: str, remote: str, local: str) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.PULL)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "pull", remote, local],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "remote": remote, "local": local}

    def install(self, serial: str, apk_path: str) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.INSTALL)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "install", apk_path],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "apk": apk_path}

    def reboot(self, serial: str, mode: str = "normal") -> dict[str, Any]:
        cap = AdbCapability.RECOVERY if mode in ("recovery",) else AdbCapability.REBOOT
        deny = self._requires(serial, cap)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                cmd = ["adb", "-s", serial, "reboot"]
                if mode == "recovery":
                    cmd.append("recovery")
                elif mode == "bootloader":
                    cmd.append("bootloader")
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "mode": mode}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "mode": mode}

    def sideload(self, serial: str, ota_path: str) -> dict[str, Any]:
        deny = self._requires(serial, AdbCapability.SIDELOAD)
        if deny:
            return {"status": "denied", "reason": deny}
        if self._real_backend:
            try:
                out = subprocess.run(
                    ["adb", "-s", serial, "sideload", ota_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return {"status": "ok" if out.returncode == 0 else "error", "serial": serial, "stderr": out.stderr}
            except Exception as exc:  # pragma: no cover - depends on host
                return {"status": "error", "error": str(exc)}
        return {"status": "simulated", "serial": serial, "ota": ota_path}

    # -- hot-plug monitoring --------------------------------------------

    def start_monitor(self, interval: float = 2.0) -> None:
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_interval = interval
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="adb-monitor", daemon=True
        )
        self._monitor_thread.start()
        logger.info("ADB hot-plug monitor started")

    def stop_monitor(self) -> None:
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self._monitor_interval + 1.0)
            self._monitor_thread = None
        logger.info("ADB hot-plug monitor stopped")

    def poll_once(self) -> None:
        previous = set(self._devices.keys())
        current_devices = self.enumerate()
        current = {d.serial for d in current_devices}
        dev_by_serial = {d.serial: d for d in current_devices}
        for serial in current - previous:
            dev = dev_by_serial.get(serial)
            if dev:
                self._event_bus.publish(
                    DeviceConnectedEvent(device_id=serial, transport="adb")
                )
                logger.info(f"ADB device connected: {dev.label()}")
        for serial in previous - current:
            self._event_bus.publish(DeviceDisconnectedEvent(device_id=serial))
            logger.info(f"ADB device disconnected: {serial}")

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


_default_manager: Optional[ADBManager] = None


def get_adb_manager() -> ADBManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ADBManager()
    return _default_manager
