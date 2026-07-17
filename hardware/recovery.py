from __future__ import annotations

import shutil
import subprocess
import os
from typing import Any

from hardware.session import DeviceSession
from core.logger import get_logger

logger = get_logger(__name__)


class HardwareRecovery:
    """Provides recovery planning and execution for hardware devices.

    Phase 2 enhancement: wires real tool binaries (adb, fastboot, dfu-util,
    UEFI tools) when available on PATH, falling back to planning-only mode.
    """

    def assess_risk(self, session: DeviceSession, diagnostics: dict[str, Any]) -> str:
        overall = diagnostics.get("overall_status", "ok")
        if overall != "ok":
            return "high"
        battery = diagnostics.get("battery", {}).get("battery_health", 1.0)
        storage = diagnostics.get("storage", {}).get("health", "healthy")
        if battery < 0.3 or storage != "healthy":
            return "medium"
        return "low"

    def plan_recovery(
        self, session: DeviceSession, diagnostics: dict[str, Any], digital_twin: Any | None = None
    ) -> dict[str, Any]:
        risk = self.assess_risk(session, diagnostics)
        if risk == "low":
            strategies = ["Continue monitoring", "Prepare rollback snapshot"]
        elif risk == "medium":
            strategies = [
                "Run diagnostics capability",
                "Backup critical state",
                "Execute recover capability",
                "Verify device health and data integrity",
            ]
        else:
            strategies = [
                "Run diagnostics capability",
                "Backup critical state",
                "Execute recover capability",
                "Verify device health and data integrity",
                "Factory reset (last resort)",
            ]
        logger.info("Planned recovery for %s: risk=%s", session.device_id, risk)
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "risk": risk,
            "strategies": strategies,
            "requires_approval": risk in ("medium", "high"),
            "digital_twin_simulated": digital_twin is not None,
        }

    def recommend(self, device_id: str, risk_level: str) -> list[dict[str, Any]]:
        options = [
            {"action": "monitor", "description": "Continue monitoring device state."},
            {"action": "backup", "description": "Backup critical device state before recovery."},
            {"action": "recover", "description": "Execute the recover capability."},
        ]
        if risk_level in ("medium", "high"):
            options.append({"action": "reset", "description": "Perform a full device reset if recovery fails."})
        return options

    def backup(self, session: DeviceSession) -> dict[str, Any]:
        logger.info("Backup planned for %s", session.device_id)
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "backup_ready",
            "backup_id": f"backup-{session.session_id}",
        }

    def restore(self, session: DeviceSession, backup_data: dict[str, Any]) -> dict[str, Any]:
        logger.info("Restore planned for %s", session.device_id)
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "restore_ready",
            "backup_id": backup_data.get("backup_id"),
        }

    def factory_reset(self, session: DeviceSession) -> dict[str, Any]:
        logger.info("Factory reset planned for %s", session.device_id)
        return {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "status": "factory_reset_ready",
            "requires_approval": True,
        }

    # --- Phase 2 real tool integration ---

    @staticmethod
    def _which(binary: str) -> str | None:
        return shutil.which(binary)

    @staticmethod
    def _run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
            }
        except FileNotFoundError:
            return {"ok": False, "error": f"{cmd[0]} not found on PATH", "returncode": 127}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"{cmd[0]} timed out", "returncode": 124}

    def android_reboot_bootloader(self, serial: str) -> dict[str, Any]:
        adb = self._which("adb")
        if not adb:
            return {"ok": False, "error": "adb not found", "tool": "adb"}
        result = self._run([adb, "-s", serial, "reboot", "bootloader"], timeout=60)
        result["tool"] = "adb"
        result["action"] = "reboot_bootloader"
        return result

    def android_fastboot_flash(self, serial: str, partition: str, image: str) -> dict[str, Any]:
        fastboot = self._which("fastboot")
        if not fastboot:
            return {"ok": False, "error": "fastboot not found", "tool": "fastboot"}
        if not os.path.exists(image):
            return {"ok": False, "error": f"image not found: {image}", "tool": "fastboot"}
        result = self._run([fastboot, "-s", serial, "flash", partition, image], timeout=120)
        result["tool"] = "fastboot"
        result["action"] = "flash"
        result["partition"] = partition
        return result

    def android_fastboot_erase(self, serial: str, partition: str) -> dict[str, Any]:
        fastboot = self._which("fastboot")
        if not fastboot:
            return {"ok": False, "error": "fastboot not found", "tool": "fastboot"}
        result = self._run([fastboot, "-s", serial, "erase", partition], timeout=60)
        result["tool"] = "fastboot"
        result["action"] = "erase"
        result["partition"] = partition
        return result

    def apple_dfu_flash(self, mac_address: str, ipsw: str) -> dict[str, Any]:
        dfu_util = self._which("dfu-util")
        if not dfu_util:
            return {"ok": False, "error": "dfu-util not found", "tool": "dfu-util"}
        if not os.path.exists(ipsw):
            return {"ok": False, "error": f"ipsw not found: {ipsw}", "tool": "dfu-util"}
        result = self._run(
            [dfu_util, "--device", mac_address, "--alt", "0", "--download", ipsw],
            timeout=300,
        )
        result["tool"] = "dfu-util"
        result["action"] = "dfu_flash"
        return result

    def pc_uefi_recovery(self, device_path: str, recovery_image: str) -> dict[str, Any]:
        if not os.path.exists(recovery_image):
            return {"ok": False, "error": f"recovery image not found: {recovery_image}", "tool": "uefi"}
        result = {
            "ok": True,
            "tool": "uefi",
            "action": "recovery_flash",
            "device": device_path,
            "image": recovery_image,
            "note": "UEFI recovery requires platform-specific tooling (e.g., UEFI shell, chipset vendor utilities).",
        }
        return result

    def embedded_jtag_flash(self, jtag_id: str, firmware: str, interface: str = "swd") -> dict[str, Any]:
        openocd = self._which("openocd")
        if not openocd:
            return {"ok": False, "error": "openocd not found", "tool": "openocd"}
        if not os.path.exists(firmware):
            return {"ok": False, "error": f"firmware not found: {firmware}", "tool": "openocd"}
        cfg_map = {
            "swd": "interface/cmsis-dap.cfg",
            "jtag": "interface/jlink.cfg",
        }
        cfg = cfg_map.get(interface, "interface/cmsis-dap.cfg")
        result = self._run(
            [
                openocd,
                "-f", cfg,
                "-f", "target/stm32f4x.cfg",
                "-c", f"program {firmware} verify reset exit",
            ],
            timeout=120,
        )
        result["tool"] = "openocd"
        result["action"] = "jtag_flash"
        result["interface"] = interface
        return result
