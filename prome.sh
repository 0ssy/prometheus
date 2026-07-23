#!/usr/bin/env bash
# prome — Prometheus Platform bootstrap launcher (macOS / Linux)
# Usage: ./prome.sh install | run | update | status

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cmd_install() {
  python3 -m venv "$REPO_ROOT/venv"
  "$REPO_ROOT/venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"
  command -v cmake >/dev/null 2>&1 || { echo "CMake not found. Install from https://cmake.org/"; exit 1; }
  cmake -B "$REPO_ROOT/build" -S "$REPO_ROOT/cpp"
  cmake --build "$REPO_ROOT/build" --config Release
  echo "Prometheus ready. Run: ./prome.sh run"
}

cmd_run() {
  if [ ! -d "$REPO_ROOT/venv" ]; then
    echo "venv not found. Run: ./prome.sh install"
    exit 1
  fi
  exec "$REPO_ROOT/venv/bin/python" "$REPO_ROOT/prometheus.py" "${@:-}"
}

cmd_status() {
  python3 --version
  echo "venv    : $([ -d "$REPO_ROOT/venv" ] && echo present || echo missing)"
  echo "cpp/hal : $([ -f "$REPO_ROOT/build/hal/libprom_hal_usb.so" ] && echo built || echo missing)"
  command -v cmake >/dev/null 2>&1 && cmake --version | head -n1 || echo "cmake   : not found"
}

case "${1:-}" in
  install) cmd_install ;;
  run)     cmd_run "${@:2}" ;;
  update)  cmd_install ;;
  status)  cmd_status ;;
  *)       echo "Usage: $0 install|run|update|status"; exit 1 ;;
esac
