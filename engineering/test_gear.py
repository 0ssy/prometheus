
def capture_oscilloscope(channels: int = 1, rate_hz: int = 1000000) -> dict:
    return {"channels": channels, "rate_hz": rate_hz, "samples": [], "status": "stub"}


def capture_logic_analyzer(channels: int = 8, rate_hz: int = 10000000) -> dict:
    return {"channels": channels, "rate_hz": rate_hz, "samples": [], "status": "stub"}


def inspect_pcb(image_path: str) -> dict:
    return {"image_path": image_path, "defects": [], "status": "stub"}
