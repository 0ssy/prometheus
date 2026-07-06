from __future__ import annotations

import pytest

from hardware.drivers.usb import USBDriver
from hardware.drivers.adb import ADBDriver
from hardware.drivers.fastboot import FastbootDriver
from hardware.drivers.network import NetworkDriver
from hardware.drivers.virtual import VirtualDriver
from hardware.drivers.base import HardwareDriver


def test_usb_driver_capabilities():
    driver = USBDriver()
    assert "connect" in driver.capabilities()
    assert "flash" in driver.capabilities()


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
