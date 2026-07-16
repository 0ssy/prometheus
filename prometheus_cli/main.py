"""Prometheus Engineering Intelligence Platform — CLI entry point.

Usage:
  python -m prometheus_cli                      # start full system + dashboard
  python -m prometheus_cli status               # print branded status banner
  python -m prometheus_cli demo                 # run happy-path demo
  python -m prometheus_cli test
  python -m prometheus_cli test --file tests/test_epsilon_service.py
"""

from __future__ import annotations

import sys

from prometheus_cli.commands import (
    run_demo,
    run_extensions,
    run_full_system,
    run_install,
    run_safe,
    run_server,
    run_status,
    run_terminal,
    run_tests,
)


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
    test_parser = sub.add_parser("test", help="run pytest suite")
    test_parser.add_argument("--file", default=None, help="optional test file/directory")

    args = parser.parse_args()

    if args.command == "install":
        return run_install(args.package)
    if args.command == "extensions":
        return run_extensions()

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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
