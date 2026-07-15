from dataclasses import dataclass, field


@dataclass
class WindowsProfile:
    name: str = "windows"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["usb", "network", "pcie"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "diagnose", "flash"]
