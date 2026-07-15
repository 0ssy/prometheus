from dataclasses import dataclass


@dataclass
class IPhoneProfile:
    name: str = "iphone"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["usb", "nfc_rfid"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "diagnose"]
