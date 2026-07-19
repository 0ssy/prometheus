"""
Engineering Capabilities registration and execution tests.
Validates all RC7 engineering discipline capabilities are registered
and callable through the CapabilityApi.
"""

import pytest

from core.capabilities import CapabilityManager
from core.event_bus import InMemoryEventBus


@pytest.fixture
def capability_api():
    return CapabilityManager(event_bus=InMemoryEventBus())


class TestEngineeringCapabilitiesRegistration:
    PROTOCOL_CAPABILITIES = [
        "engineering.protocol.decode_uart",
        "engineering.protocol.decode_spi",
        "engineering.protocol.decode_can",
        "engineering.protocol.decode_ble",
    ]

    BINARY_CAPABILITIES = [
        "engineering.binary.disassemble",
        "engineering.binary.symbols",
        "engineering.binary.sections",
    ]

    TESTGEAR_CAPABILITIES = [
        "engineering.testgear.oscilloscope",
        "engineering.testgear.logic_analyzer",
        "engineering.testgear.pcb_inspection",
    ]

    def test_protocol_decoders_registered(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.PROTOCOL_CAPABILITIES:
            assert capability_api.exists(name), f"Missing capability: {name}"

    def test_binary_analysis_registered(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.BINARY_CAPABILITIES:
            assert capability_api.exists(name), f"Missing capability: {name}"

    def test_test_gear_registered(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.TESTGEAR_CAPABILITIES:
            assert capability_api.exists(name), f"Missing capability: {name}"

    def test_all_engineering_capabilities_discoverable(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        discovered = capability_api.discover(target="engineering")
        names = {c["name"] for c in discovered}
        expected = set(self.PROTOCOL_CAPABILITIES + self.BINARY_CAPABILITIES + self.TESTGEAR_CAPABILITIES)
        assert expected.issubset(names)

    def test_protocol_permissions(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.PROTOCOL_CAPABILITIES:
            cap = capability_api._capabilities[name]
            assert cap.permissions == {"device.read"}

    def test_binary_permissions(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.BINARY_CAPABILITIES:
            cap = capability_api._capabilities[name]
            assert cap.permissions == {"firmware.read"}

    def test_test_gear_permissions(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        for name in self.TESTGEAR_CAPABILITIES:
            cap = capability_api._capabilities[name]
            assert cap.permissions == {"device.connect"}


class TestEngineeringCapabilitiesExecution:
    def test_decode_uart_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.protocol.decode_uart",
            {"data": b"\x00\x01\x02", "baudrate": 9600},
            {"device.read"},
        )
        assert result["protocol"] == "uart"
        assert result["baudrate"] == 9600
        assert result["status"] == "stub"

    def test_decode_spi_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.protocol.decode_spi",
            {"data": b"\x00\x01\x02", "clock_hz": 5000000},
            {"device.read"},
        )
        assert result["protocol"] == "spi"
        assert result["clock_hz"] == 5000000
        assert result["status"] == "stub"

    def test_decode_can_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.protocol.decode_can",
            {"data": b"\x00\x01\x02"},
            {"device.read"},
        )
        assert result["protocol"] == "can"
        assert result["status"] == "stub"

    def test_decode_ble_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.protocol.decode_ble",
            {"data": b"\x00\x01\x02"},
            {"device.read"},
        )
        assert result["protocol"] == "ble"
        assert result["status"] == "stub"

    def test_disassemble_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.binary.disassemble",
            {"data": b"\x00\x01\x02", "arch": "riscv"},
            {"firmware.read"},
        )
        assert result["arch"] == "riscv"
        assert result["status"] == "stub"

    def test_parse_symbols_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.binary.symbols",
            {"data": b"\x00\x01\x02"},
            {"firmware.read"},
        )
        assert result["status"] == "stub"
        assert result["symbols"] == []

    def test_parse_sections_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.binary.sections",
            {"data": b"\x00\x01\x02"},
            {"firmware.read"},
        )
        assert result["status"] == "stub"
        assert result["sections"] == []

    def test_oscilloscope_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.testgear.oscilloscope",
            {"channels": 2, "rate_hz": 2500000},
            {"device.connect"},
        )
        assert result["channels"] == 2
        assert result["rate_hz"] == 2500000
        assert result["status"] == "stub"

    def test_logic_analyzer_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.testgear.logic_analyzer",
            {"channels": 16, "rate_hz": 50000000},
            {"device.connect"},
        )
        assert result["channels"] == 16
        assert result["rate_hz"] == 50000000
        assert result["status"] == "stub"

    def test_pcb_inspection_executes(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        result = capability_api.execute(
            "engineering.testgear.pcb_inspection",
            {"image_path": "/tmp/pcb.png"},
            {"device.connect"},
        )
        assert result["image_path"] == "/tmp/pcb.png"
        assert result["defects"] == []
        assert result["status"] == "stub"

    def test_missing_permission_denies_protocol(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        with pytest.raises(PermissionError):
            capability_api.execute(
                "engineering.protocol.decode_uart",
                {"data": b"\x00"},
                set(),
            )

    def test_missing_permission_denies_binary(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        with pytest.raises(PermissionError):
            capability_api.execute(
                "engineering.binary.disassemble",
                {"data": b"\x00"},
                set(),
            )

    def test_missing_permission_denies_testgear(self, capability_api):
        from services.engineering_capabilities import register_engineering_capabilities

        register_engineering_capabilities(capability_api)
        with pytest.raises(PermissionError):
            capability_api.execute(
                "engineering.testgear.oscilloscope",
                {"channels": 1},
                set(),
            )
