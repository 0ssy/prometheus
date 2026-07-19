
def decode_uart(data: bytes, baudrate: int = 115200) -> dict:
    return {"protocol": "uart", "baudrate": baudrate, "frames": [], "status": "stub"}


def decode_spi(data: bytes, clock_hz: int = 1000000) -> dict:
    return {"protocol": "spi", "clock_hz": clock_hz, "frames": [], "status": "stub"}


def decode_can(data: bytes) -> dict:
    return {"protocol": "can", "frames": [], "status": "stub"}


def decode_ble(data: bytes) -> dict:
    return {"protocol": "ble", "advertisements": [], "status": "stub"}
