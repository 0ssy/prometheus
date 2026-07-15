from dataclasses import dataclass


@dataclass
class STM32Profile:
    name: str = "stm32"
    primary_drivers: list[str] = None
    capabilities: list[str] = None

    def __post_init__(self):
        if self.primary_drivers is None:
            self.primary_drivers = ["serial", "stm32"]
        if self.capabilities is None:
            self.capabilities = ["connect", "disconnect", "read", "write", "flash", "diagnose"]
