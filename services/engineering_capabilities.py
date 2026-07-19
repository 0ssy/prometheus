from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


def _forwarding_executor(executor, permissions: set[str]):
    def wrapper(payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload["_permissions"] = set(permissions)
        return executor(payload)

    return wrapper


def register_engineering_capabilities(cap_api) -> None:
    from engineering.binary_analysis import disassemble, parse_symbols, parse_sections
    from engineering.protocol_decoder import decode_ble, decode_can, decode_spi, decode_uart
    from engineering.test_gear import capture_logic_analyzer, capture_oscilloscope, inspect_pcb

    def exec_decode_uart(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        baudrate = int(payload.get("baudrate", 115200))
        return decode_uart(data, baudrate=baudrate)

    def exec_decode_spi(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        clock_hz = int(payload.get("clock_hz", 1000000))
        return decode_spi(data, clock_hz=clock_hz)

    def exec_decode_can(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return decode_can(data)

    def exec_decode_ble(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return decode_ble(data)

    def exec_disassemble(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        arch = payload.get("arch", "arm")
        return disassemble(data, arch=arch)

    def exec_parse_symbols(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return parse_symbols(data)

    def exec_parse_sections(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data", b"")
        if isinstance(data, str):
            data = data.encode()
        return parse_sections(data)

    def exec_capture_oscilloscope(payload: dict[str, Any]) -> dict[str, Any]:
        channels = int(payload.get("channels", 1))
        rate_hz = int(payload.get("rate_hz", 1000000))
        return capture_oscilloscope(channels=channels, rate_hz=rate_hz)

    def exec_capture_logic_analyzer(payload: dict[str, Any]) -> dict[str, Any]:
        channels = int(payload.get("channels", 8))
        rate_hz = int(payload.get("rate_hz", 10000000))
        return capture_logic_analyzer(channels=channels, rate_hz=rate_hz)

    def exec_inspect_pcb(payload: dict[str, Any]) -> dict[str, Any]:
        image_path = payload.get("image_path", "")
        return inspect_pcb(image_path)

    executors = {
        "engineering.protocol.decode_uart": exec_decode_uart,
        "engineering.protocol.decode_spi": exec_decode_spi,
        "engineering.protocol.decode_can": exec_decode_can,
        "engineering.protocol.decode_ble": exec_decode_ble,
        "engineering.binary.disassemble": exec_disassemble,
        "engineering.binary.symbols": exec_parse_symbols,
        "engineering.binary.sections": exec_parse_sections,
        "engineering.testgear.oscilloscope": exec_capture_oscilloscope,
        "engineering.testgear.logic_analyzer": exec_capture_logic_analyzer,
        "engineering.testgear.pcb_inspection": exec_inspect_pcb,
    }

    forward_permissions = {
        "engineering.protocol.decode_uart": {"device.read"},
        "engineering.protocol.decode_spi": {"device.read"},
        "engineering.protocol.decode_can": {"device.read"},
        "engineering.protocol.decode_ble": {"device.read"},
        "engineering.binary.disassemble": {"firmware.read"},
        "engineering.binary.symbols": {"firmware.read"},
        "engineering.binary.sections": {"firmware.read"},
        "engineering.testgear.oscilloscope": {"device.connect"},
        "engineering.testgear.logic_analyzer": {"device.connect"},
        "engineering.testgear.pcb_inspection": {"device.connect"},
    }

    target = "engineering"
    for name, executor in executors.items():
        if cap_api.exists(name):
            continue
        cap_api.register(
            name=name,
            target=target,
            description=f"Engineering capability: {name}",
            permissions=forward_permissions[name],
            executor=_forwarding_executor(executor, forward_permissions[name]),
        )
    logger.info("Registered %d engineering capabilities", len(executors))
