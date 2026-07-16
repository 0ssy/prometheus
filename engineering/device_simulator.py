"""
Gamma Device Simulator (RFC 0002)
-----------------------------------------
Extends Phase Beta's SimulatedDevice with fake firmware and a REAL
Ed25519 signature over it — so Boot Chain Analyzer gets tested against
actual cryptographic verification, not a mocked True/False.
"""

from hardware.drivers.virtual import VirtualDriver
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class SimulatedFirmwareDevice(VirtualDriver):
    name = "simulated_firmware"

    def __init__(self, device_id: str, tampered: bool = False, **kwargs):
        super().__init__(wrapped_device=None)
        self.device_id = device_id
        self.transport = "virtual"
        self.tampered = tampered
        self.firmware_bytes = b"FAKEFW:" + device_id.encode() + b"\x00" * 32

        private_key = Ed25519PrivateKey.generate()
        self.public_key_bytes = private_key.public_key().public_bytes_raw()
        self.signature = private_key.sign(self.firmware_bytes)

        if tampered:
            tampered_bytes = bytearray(self.firmware_bytes)
            tampered_bytes[10] ^= 0xFF
            self.firmware_bytes = bytes(tampered_bytes)
