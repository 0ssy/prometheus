from dataclasses import dataclass


@dataclass
class AndroidProfile:
    name: str = "android"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["adb", "fastboot", "usb"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "shell", "push", "pull", "flash", "reboot"]
