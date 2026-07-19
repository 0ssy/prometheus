
def disassemble(data: bytes, arch: str = "arm") -> dict:
    return {"arch": arch, "instructions": [], "status": "stub"}


def parse_symbols(data: bytes) -> dict:
    return {"symbols": [], "status": "stub"}


def parse_sections(data: bytes) -> dict:
    return {"sections": [], "status": "stub"}
