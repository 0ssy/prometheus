from dataclasses import dataclass


@dataclass
class JetsonProfile:
    name: str = "jetson"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["usb", "network", "pcie"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "shell", "diagnose", "flash"]
