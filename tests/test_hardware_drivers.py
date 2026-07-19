from __future__ import annotations

import pytest

from hardware.drivers.usb import USBDriver
from hardware.drivers.serial import SerialDriver
from hardware.drivers.adb import ADBDriver
from hardware.drivers.fastboot import FastbootDriver
from hardware.drivers.network import NetworkDriver
from hardware.drivers.virtual import VirtualDriver
from hardware.usb import get_usb_manager, UsbCapability
from hardware.serial import get_serial_manager, SerialCapability


def test_usb_driver_capabilities():
    driver = USBDriver()
    assert "connect" in driver.capabilities()
    assert "flash" in driver.capabilities()


def test_serial_driver_capabilities():
    driver = SerialDriver()
    assert "connect" in driver.capabilities()
    assert "write" in driver.capabilities()
    assert "configure" in driver.capabilities()


def test_adb_driver_capabilities():
    driver = ADBDriver()
    assert "shell" in driver.capabilities()
    assert "sideload" in driver.capabilities()


def test_fastboot_driver_capabilities():
    driver = FastbootDriver()
    assert "flash" in driver.capabilities()
    assert "getvar" in driver.capabilities()


def test_network_driver_capabilities():
    driver = NetworkDriver()
    assert "ssh" in driver.capabilities()
    assert "scp" in driver.capabilities()


def test_virtual_driver_capabilities():
    driver = VirtualDriver()
    assert "simulate" in driver.capabilities()
    assert "read" in driver.capabilities()


def test_driver_execute_unknown_capability_raises():
    driver = USBDriver()
    with pytest.raises(ValueError):
        driver.execute("unsupported", {})


def test_driver_connect_disconnect():
    driver = VirtualDriver()
    assert driver.connected is False
    driver.connect()
    assert driver.connected is True
    driver.disconnect()
    assert driver.connected is False


def test_usb_driver_bridges_capability_backend():
    """The USB driver must reflect real enumerated devices, not hardcoded mocks."""
    manager = get_usb_manager()
    devices = manager.enumerate()
    assert devices, "expected at least the simulated backend devices"

    device = devices[0]
    manager.policy().allow(
        vendor_id=device.vendor_id,
        product_id=device.product_id,
        serial=device.serial_number,
        capabilities=frozenset({UsbCapability.CONNECT, UsbCapability.READ_INFO}),
    )

    driver = USBDriver.for_device(device.device_id)
    result = driver.connect()
    assert result["status"] == "connected"
    assert result["device_id"] == device.device_id

    ident = driver.identify()
    assert ident["device_id"] == device.device_id
    assert ident["vid_pid"] == device.vid_pid


def test_usb_driver_respects_permission_policy():
    """Connecting a device not allowed by policy must be denied, not faked."""
    manager = get_usb_manager()
    devices = manager.enumerate()
    device = devices[0]

    ok, _ = manager.can_access(
        UsbCapability.CONNECT, device.vendor_id, device.product_id, device.serial_number
    )
    if ok:
        return

    driver = USBDriver.for_device(device.device_id)
    result = driver.connect()
    assert result["status"] == "denied"
    assert driver.connected is False


def test_serial_driver_bridges_capability_backend():
    """The Serial driver must reflect real enumerated ports, not hardcoded mocks."""
    manager = get_serial_manager()
    ports = manager.enumerate()
    assert ports, "expected at least the simulated backend ports"

    port = ports[0]
    manager.policy().allow(
        port=port.port,
        vendor_id=port.vendor_id,
        product_id=port.product_id,
        serial=port.serial_number,
        capabilities=frozenset({SerialCapability.CONNECT, SerialCapability.READ_INFO}),
    )

    driver = SerialDriver.for_port(port.port)
    result = driver.connect()
    assert result["status"] == "connected"
    assert result["port"] == port.port

    ident = driver.identify()
    assert ident["port"] == port.port
    assert ident.get("vid_pid") == port.vid_pid


def test_serial_driver_respects_permission_policy():
    manager = get_serial_manager()
    ports = manager.enumerate()
    port = ports[0]

    ok, _ = manager.can_access(
        SerialCapability.CONNECT, port.port, port.vendor_id, port.product_id, port.serial_number
    )
    if ok:
        return

    driver = SerialDriver.for_port(port.port)
    result = driver.connect()
    assert result["status"] == "denied"
    assert driver.connected is False
