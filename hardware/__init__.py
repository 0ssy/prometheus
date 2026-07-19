from __future__ import annotations

from hardware.hal.interface import HardwareInterface
from hardware.hal.manager import HALManager
from hardware.hal.registry import HardwareRegistry
from hardware.hal.capability_mapper import CapabilityMapper
from hardware.drivers.base import HardwareDriver
from hardware.drivers.usb import USBDriver
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
from hardware.drivers.mobile import ADBDriver, FastbootDriver
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
from hardware.session import DeviceSession, DeviceSessionManager
from hardware.diagnostics import HardwareDiagnostics
from hardware.recovery import HardwareRecovery
from hardware.usb import (
    USBManager,
    UsbDevice,
    get_usb_manager,
    UsbCapability,
    UsbPermissionPolicy,
    UsbAllowRule,
    UsbDenyRule,
)
from hardware.events import (
    HardwareEvent,
    DeviceConnectedEvent,
    DeviceDisconnectedEvent,
    DeviceUnresponsiveEvent,
    BatteryLowEvent,
    FirmwareDetectedEvent,
    DriverFailedEvent,
    SessionExpiredEvent,
)

__all__ = [
    "HardwareInterface",
    "HALManager",
    "HardwareRegistry",
    "CapabilityMapper",
    "HardwareDriver",
    "USBDriver",
    "ADBDriver",
    "FastbootDriver",
    "NetworkDriver",
    "VirtualDriver",
    "SerialDriver",
    "I2CDriver",
    "SPIDriver",
    "CANDriver",
    "LINDriver",
    "GPIODriver",
    "JTAGDriver",
    "SWDDriver",
    "PCIeDriver",
    "SATADriver",
    "NVMeDriver",
    "SDDriver",
    "MicroSDDriver",
    "MQTTDriver",
    "ModbusDriver",
    "OPCUADriver",
    "BACnetDriver",
    "I2SDriver",
    "AudioJackDriver",
    "MIDIDriver",
    "MIPIDriver",
    "CSIDriver",
    "DSIDriver",
    "HDMIDriver",
    "DisplayPortDriver",
    "NFCDriver",
    "RFIDDriver",
    "AndroidRecoveryDriver",
    "EDLDriver",
    "OdinDriver",
    "DFUDriver",
    "BIOSDriver",
    "UEFIDriver",
    "TPMDriver",
    "RouterDriver",
    "IoTDriver",
    "DroneDriver",
    "VehicleDriver",
    "ECUDriver",
    "EEPROMDriver",
    "NANDDriver",
    "NORDriver",
    "SPIFlashDriver",
    "EmbeddedLinuxDriver",
    "DeviceSession",
    "DeviceSessionManager",
    "HardwareDiagnostics",
    "HardwareRecovery",
    "USBManager",
    "UsbDevice",
    "get_usb_manager",
    "UsbCapability",
    "UsbPermissionPolicy",
    "UsbAllowRule",
    "UsbDenyRule",
    "HardwareEvent",
    "DeviceConnectedEvent",
    "DeviceDisconnectedEvent",
    "DeviceUnresponsiveEvent",
    "BatteryLowEvent",
    "FirmwareDetectedEvent",
    "DriverFailedEvent",
    "SessionExpiredEvent",
]
