from dataclasses import dataclass


@dataclass
class ArduinoProfile:
    name: str = "arduino"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["serial", "usb"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "flash", "diagnose"]
