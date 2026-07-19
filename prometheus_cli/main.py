"""Prometheus Engineering Intelligence Platform — CLI entry point.

Usage:
  python -m prometheus_cli                      # start full system + dashboard
  python -m prometheus_cli status               # print branded status banner
  python -m prometheus_cli demo                 # run happy-path demo
  python -m prometheus_cli test
  python -m prometheus_cli test --file tests/test_epsilon_service.py
  python -m prometheus_cli launch               # launch full platform (backend + Go + cloud + frontend)
  python -m prometheus_cli launch --distributed # + Go distributed services
  python -m prometheus_cli launch --cloud       # + Go cloud services
"""

from __future__ import annotations

import sys

from prometheus_cli.commands import (
    run_demo,
    run_extensions,
    run_full_system,
    run_install,
    run_new,
    run_pack,
    run_verify,
    run_safe,
    run_server,
    run_status,
    run_terminal,
    run_tests,
    run_usb,
    run_serial,
)
from prometheus_cli.launch import main as run_launch


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="prometheus",
        description="Prometheus Engineering Intelligence Platform — unified entry point",
    )
    parser.add_argument(
        "--terminal", action="store_true",
        help="terminal-only mode: boot the platform and drop into a live shell",
    )
    parser.add_argument(
        "--developer", action="store_true",
        help="developer workspace: full system + registered service dump",
    )
    parser.add_argument(
        "--server", action="store_true",
        help="headless server mode: serve the API, never open a browser",
    )
    parser.add_argument(
        "--safe-mode", action="store_true",
        help="boot with minimal services (no plugins/agents)",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="print branded platform status banner")
    demo_parser = sub.add_parser("demo", help="run happy-path demo")
    demo_parser.add_argument("--db", default=None, help="override database path (empty for ephemeral in-memory)")
    install_parser = sub.add_parser("install", help="install an SDK package (robotics/android/cad/vision/drone)")
    install_parser.add_argument("package", help="SDK package name to install")
    sub.add_parser("extensions", help="list installed SDK packages")
    new_parser = sub.add_parser("new", help="scaffold a new plugin, agent, or driver")
    new_parser.add_argument("kind", choices=["plugin", "agent", "driver"], help="type of scaffold")
    new_parser.add_argument("name", help="name of the new component")
    pack_parser = sub.add_parser("pack", help="create a signed package of a plugin/agent/driver")
    pack_parser.add_argument("path", help="path to the plugin, agent, or driver directory")
    verify_parser = sub.add_parser("verify", help="verify a signed package")
    verify_parser.add_argument("path", help="path to the .zip package to verify")
    test_parser = sub.add_parser("test", help="run pytest suite")
    test_parser.add_argument("--file", default=None, help="optional test file/directory")
    usb_parser = sub.add_parser("usb", help="USB capability: list/info/monitor/allow/deny devices")
    usb_parser.add_argument("usb_args", nargs=argparse.REMAINDER, help="usb subcommand and options")
    serial_parser = sub.add_parser("serial", help="Serial capability: list/info/connect/disconnect/monitor/allow/deny")
    serial_parser.add_argument("serial_args", nargs=argparse.REMAINDER, help="serial subcommand and options")
    launch_parser = sub.add_parser("launch", help="launch the full platform with one command")
    launch_parser.add_argument("--distributed", action="store_true", help="start Go distributed services")
    launch_parser.add_argument("--cloud", action="store_true", help="start Go cloud services")
    launch_parser.add_argument("--frontend", action="store_true", help="start Vite dev server")
    launch_parser.add_argument("--all", action="store_true", help="start every subsystem")
    launch_parser.add_argument("--workers", type=int, default=1, help="number of local Go workers")

    args = parser.parse_args()

    if args.command == "install":
        return run_install(args.package)
    if args.command == "extensions":
        return run_extensions()
    if args.command == "new":
        return run_new(args.kind, args.name)
    if args.command == "pack":
        return run_pack(args.path)
    if args.command == "verify":
        return run_verify(args.path)

    if not args.command:
        if args.terminal:
            run_terminal()
            return 0
        if args.developer:
            run_developer()
            return 0
        if args.server:
            run_server()
            return 0
        if args.safe_mode:
            run_safe()
            return 0
        run_full_system()
        return 0

    if args.command == "status":
        return run_status()
    if args.command == "demo":
        run_demo(db_path=args.db)
        return 0
    if args.command == "test":
        return run_tests(args.file)
    if args.command == "usb":
        return run_usb(args.usb_args)
    if args.command == "serial":
        return run_serial(args.serial_args)
    if args.command == "launch":
        return run_launch(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
