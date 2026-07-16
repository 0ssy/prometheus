"""Bootstrap sequences and branded output for the Prometheus CLI."""


_LABEL_WIDTH = 21

_BOOT_LOGO = """  ____  ____  ____  ____  ____  ____  __  __  _____
 |  _ \\|  _ \\|  _ \\|  _ \\|  _ \\|  _ \\|  \\/  \\/  __  |
 | |_) | |_) | |_) | |_) | |_) | |_) | |\\/| | |  | |
 |  __/|  __/|  __/|  __/|  __/|  __/| |  | | |__| |
 |_|   |_|   |_|   |_|   |_|   |_|   |_|  |_|\\_____/"""


def banner_line(label: str, value: str) -> str:
    return f"{label:<{_LABEL_WIDTH}}{value}"


def print_banner(snapshot: dict) -> None:
    from core.config import config

    print()
    print("Prometheus Engineering Intelligence Platform")
    print(f"Version {config.version}")
    print()

    print(banner_line("Platform", snapshot["kernel"]))
    print(banner_line("Knowledge", snapshot["knowledge"]))
    print(banner_line("Simulation", snapshot["simulation"]))
    print(banner_line("Reasoning", snapshot["reasoning"]))
    print(banner_line("Hardware", snapshot["hardware"]))
    print()
    print(banner_line("Connected Devices", str(snapshot["devices"])))
    print(banner_line("Agents", str(snapshot["agents"])))
    print(banner_line("Plugins", str(snapshot["plugins"])))
    print(banner_line("Capabilities", str(snapshot["capabilities"])))
    print(banner_line("Knowledge Facts", str(snapshot["knowledge_facts"])))
    print()
    print("Ready.")
    print()


def print_boot_logo(version: str) -> None:
    print()
    print(_BOOT_LOGO)
    print("Engineering Intelligence Platform")
    print(f"v{version}")
    print()
