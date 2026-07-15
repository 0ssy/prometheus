"""
Embedded Engineering Module
-----------------------------------------
Simulated embedded engineering workflows: flash firmware, read sensors,
configure RTOS, debug via JTAG, build firmware.
"""

from dataclasses import dataclass, field, asdict
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FlashResult:
    device_id: str
    firmware_path: str
    status: str
    bytes_written: int
    verification_hash: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RtOSConfig:
    device_id: str
    rtos: str
    scheduler: str
    tick_rate_hz: int
    tasks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JtagDebugResult:
    device_id: str
    core_status: str
    registers: dict
    halted: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BuildResult:
    device_id: str
    toolchain: str
    target: str
    status: str
    output_path: str
    size_bytes: int

    def to_dict(self) -> dict:
        return asdict(self)


class EmbeddedModule:
    name = "embedded"

    def execute(self, workflow: str, payload: dict) -> dict:
        if workflow == "flash_firmware":
            return self._flash_firmware(payload)
        if workflow == "read_sensor":
            return self._read_sensor(payload)
        if workflow == "configure_rtos":
            return self._configure_rtos(payload)
        if workflow == "debug_jtag":
            return self._debug_jtag(payload)
        if workflow == "build_firmware":
            return self._build_firmware(payload)
        raise ValueError(f"Unknown embedded workflow: {workflow}")

    def _flash_firmware(self, payload: dict) -> dict:
        device_id = payload.get("device_id", "")
        firmware_path = payload.get("firmware_path", "")
        if not device_id or not firmware_path:
            raise ValueError("device_id and firmware_path required")
        logger.info(f"Flashing {firmware_path} to {device_id}")
        return FlashResult(
            device_id=device_id,
            firmware_path=firmware_path,
            status="success",
            bytes_written=32768,
            verification_hash="a" * 64,
        ).to_dict()

    def _read_sensor(self, payload: dict) -> dict:
        sensor_id = payload.get("sensor_id", "unknown")
        sensor_type = payload.get("sensor_type", "temperature")
        value = payload.get("value", 25.0)
        unit = payload.get("unit", "C")
        logger.info(f"Reading sensor {sensor_id}: {value}{unit}")
        return SensorReading(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            timestamp="2026-07-15T18:00:00Z",
        ).to_dict()

    def _configure_rtos(self, payload: dict) -> dict:
        device_id = payload.get("device_id", "")
        rtos = payload.get("rtos", "FreeRTOS")
        scheduler = payload.get("scheduler", "preemptive")
        tick_rate_hz = payload.get("tick_rate_hz", 1000)
        logger.info(f"Configuring {rtos} on {device_id}")
        return RtOSConfig(
            device_id=device_id,
            rtos=rtos,
            scheduler=scheduler,
            tick_rate_hz=tick_rate_hz,
            tasks=["idle", "sensor_poll", "comm_task"],
        ).to_dict()

    def _debug_jtag(self, payload: dict) -> dict:
        device_id = payload.get("device_id", "")
        logger.info(f"JTAG debug session on {device_id}")
        return JtagDebugResult(
            device_id=device_id,
            core_status="running",
            registers={"pc": "0x08000000", "lr": "0x08000100", "sp": "0x20000000"},
            halted=False,
        ).to_dict()

    def _build_firmware(self, payload: dict) -> dict:
        device_id = payload.get("device_id", "")
        toolchain = payload.get("toolchain", "gcc-arm-none-eabi")
        target = payload.get("target", "cortex-m4")
        logger.info(f"Building firmware for {device_id} with {toolchain}")
        return BuildResult(
            device_id=device_id,
            toolchain=toolchain,
            target=target,
            status="success",
            output_path=f"/tmp/build/{device_id}.bin",
            size_bytes=65536,
        ).to_dict()
