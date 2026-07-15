from __future__ import annotations

from typing import Any

from hardware.hal.manager import HALManager
from hardware.hal.registry import HardwareRegistry
from hardware.hal.capability_mapper import CapabilityMapper
from hardware.drivers.base import HardwareDriver
from core.logger import get_logger

logger = get_logger(__name__)


class EpsilonHAL:
    """Epsilon Hardware Abstraction Layer bridge.

    Wraps the lower-level hardware HAL and exposes it to the rest of the
    Prometheus Core platform. No code outside this module talks directly to
    USB, Bluetooth, ADB, or other transports.
    """

    def __init__(self, authorizer=None) -> None:
        self._manager = HALManager()
        self._registry = HardwareRegistry.instance()
        self._mapper = CapabilityMapper()
        self._drivers: dict[str, type[HardwareDriver]] = {}
        self._active_drivers: dict[str, HardwareDriver] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._authorizer = authorizer
        self._register_default_drivers()

    def _register_default_drivers(self) -> None:
        """Register default driver classes with the registry."""
        from hardware.drivers.usb import USBDriver
        from hardware.drivers.adb import ADBDriver
        from hardware.drivers.fastboot import FastbootDriver
        from hardware.drivers.network import NetworkDriver
        from hardware.drivers.virtual import VirtualDriver
        from hardware.drivers.serial import SerialDriver
        from hardware.drivers.bus import (
            I2CDriver,
            SPIDriver,
            CANDriver,
            LINDriver,
            GPIODriver,
            JTAGDriver,
            SWDDriver,
        )
        from hardware.drivers.pcie import (
            PCIeDriver,
            SATADriver,
            NVMeDriver,
            SDDriver,
            MicroSDDriver,
        )
        from hardware.drivers.iot_protocol import (
            MQTTDriver,
            ModbusDriver,
            OPCUADriver,
            BACnetDriver,
        )
        from hardware.drivers.audio import I2SDriver, AudioJackDriver, MIDIDriver
        from hardware.drivers.video import (
            MIPIDriver,
            CSIDriver,
            DSIDriver,
            HDMIDriver,
            DisplayPortDriver,
        )
        from hardware.drivers.nfc_rfid import NFCDriver, RFIDDriver
        from hardware.drivers.recovery import (
            AndroidRecoveryDriver,
            EDLDriver,
            OdinDriver,
            DFUDriver,
            BIOSDriver,
            UEFIDriver,
            TPMDriver,
            RouterDriver,
            IoTDriver,
            DroneDriver,
            VehicleDriver,
            ECUDriver,
            EEPROMDriver,
            NANDDriver,
            NORDriver,
            SPIFlashDriver,
            EmbeddedLinuxDriver,
        )

        default_drivers = [
            USBDriver,
            ADBDriver,
            FastbootDriver,
            NetworkDriver,
            VirtualDriver,
            SerialDriver,
            I2CDriver,
            SPIDriver,
            CANDriver,
            LINDriver,
            GPIODriver,
            JTAGDriver,
            SWDDriver,
            PCIeDriver,
            SATADriver,
            NVMeDriver,
            SDDriver,
            MicroSDDriver,
            MQTTDriver,
            ModbusDriver,
            OPCUADriver,
            BACnetDriver,
            I2SDriver,
            AudioJackDriver,
            MIDIDriver,
            MIPIDriver,
            CSIDriver,
            DSIDriver,
            HDMIDriver,
            DisplayPortDriver,
            NFCDriver,
            RFIDDriver,
            AndroidRecoveryDriver,
            EDLDriver,
            OdinDriver,
            DFUDriver,
            BIOSDriver,
            UEFIDriver,
            TPMDriver,
            RouterDriver,
            IoTDriver,
            DroneDriver,
            VehicleDriver,
            ECUDriver,
            EEPROMDriver,
            NANDDriver,
            NORDriver,
            SPIFlashDriver,
            EmbeddedLinuxDriver,
        ]
        for driver_cls in default_drivers:
            self._registry.register(driver_cls)
            self._drivers[driver_cls.name] = driver_cls

        self._register_default_profiles()

    def _register_default_profiles(self) -> None:
        from hardware.profiles.windows import WindowsProfile
        from hardware.profiles.linux import LinuxProfile
        from hardware.profiles.android import AndroidProfile
        from hardware.profiles.esp32 import ESP32Profile
        from hardware.profiles.raspberry_pi import RaspberryPiProfile
        from hardware.profiles.arduino import ArduinoProfile
        from hardware.profiles.jetson import JetsonProfile
        from hardware.profiles.stm32 import STM32Profile
        from hardware.profiles.iphone import IPhoneProfile
        from hardware.profiles.sbc_generic import SBCGenericProfile

        for profile_cls in [
            WindowsProfile,
            LinuxProfile,
            AndroidProfile,
            ESP32Profile,
            RaspberryPiProfile,
            ArduinoProfile,
            JetsonProfile,
            STM32Profile,
            IPhoneProfile,
            SBCGenericProfile,
        ]:
            profile = profile_cls()
            self._profiles[profile.name] = {
                "primary_drivers": profile.primary_drivers,
                "capabilities": profile.capabilities,
            }

    def register_interface(self, name: str, driver_cls: type[HardwareDriver]) -> None:
        if self._authorizer is not None:
            result = self._authorizer.authorize("system", "hardware.register", name, {"hardware.register"})
            if not result.allowed:
                raise PermissionError(result.reason)
        self._registry.register(driver_cls)
        self._drivers[name.lower()] = driver_cls

    def list_interfaces(self) -> list[dict[str, Any]]:
        result = []
        for name in self._registry.list_registered():
            capabilities = self._registry.discover_capabilities(name)
            result.append({"name": name, "capabilities": capabilities})
        return result

    def get_interface(self, name: str) -> type[HardwareDriver]:
        return self._registry.get(name)

    def instantiate_driver(self, name: str, **kwargs: Any) -> HardwareDriver:
        if self._authorizer is not None:
            result = self._authorizer.authorize("system", "device.connect", name, {"device.connect"})
            if not result.allowed:
                raise PermissionError(result.reason)
        driver_cls = self.get_interface(name)
        driver = driver_cls(**kwargs)
        self._manager.register_interface(name, driver)
        return driver

    def discover_capabilities(self, driver_name: str) -> list[str]:
        return self._registry.discover_capabilities(driver_name)

    def store_driver(self, device_id: str, driver: HardwareDriver) -> None:
        """Persist an active driver instance keyed by device_id."""
        self._active_drivers[device_id] = driver

    def get_driver(self, device_id: str) -> HardwareDriver | None:
        """Retrieve a stored driver instance by device_id."""
        return self._active_drivers.get(device_id)

    def remove_driver(self, device_id: str) -> None:
        """Remove a stored driver instance."""
        self._active_drivers.pop(device_id, None)

    def list_active_drivers(self) -> list[str]:
        return list(self._active_drivers.keys())

    def register_profile(self, profile_name: str, profile: dict[str, Any]) -> None:
        self._profiles[profile_name] = profile

    def get_profile(self, profile_name: str) -> dict[str, Any] | None:
        return self._profiles.get(profile_name)

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())
