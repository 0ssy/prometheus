from dataclasses import dataclass


@dataclass
class SBCGenericProfile:
    name: str = "sbc_generic"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["usb", "serial", "network", "gpio"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "diagnose", "flash"]
