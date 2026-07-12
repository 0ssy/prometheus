# Prometheus — Native Desktop (Tauri)

This folder contains the Tauri v2 shell that wraps the Prometheus web UI so
the operating system launches as a **native window** instead of a browser tab.

```
Terminal ──▶ Python (prometheus.py) ──▶ FastAPI ──▶ Tauri ──▶ React UI
```

## Prerequisites

- [Rust](https://www.rust-lang.org/tools/install) (stable, ≥ 1.77)
- [Microsoft WebView2](https://developer.microsoft.com/microsoft-edge/webview2/)
  (preinstalled on Windows 10/11)
- Node 18+ and Python 3.11+ on `PATH`

## Develop

```bash
cd C:\Users\josep\Downloads\prometheus
python prometheus.py --server        # starts FastAPI on :8000 (headless)
cd src-tauri && cargo tauri dev      # opens the native Prometheus window
```

`beforeDevCommand` in `tauri.conf.json` also auto-starts the backend
(`python ../prometheus.py --server`) when you run `cargo tauri dev`.

## Build the installer

```bash
# one-time: create the build venv and install the PyInstaller freezer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt pyinstaller

# build the self-contained installer — beforeBuildCommand builds the SPA
# and the frozen Python sidecar automatically
cd src-tauri && cargo tauri build
```

The output installer (`Prometheus_0.6.0_x64-setup.exe`) lands in
`src-tauri/target/release/bundle/nsis/`. It bundles the frozen backend, so the
installed app runs with **no system Python** on `PATH`.

## Icons

`icons/` already contains `32x32.png`, `128x128.png`, and `icon.ico`
(generated as placeholders). To use a branded logo:

```bash
cargo tauri icon path/to/logo.png
```

## Shipping the backend with the installer (production)

The web UI talks to the FastAPI backend at `http://localhost:8000`. The installer
is **fully self-contained**: the Python runtime is frozen into a single
executable (`scripts/build_app_exe.py`, via PyInstaller) and bundled as a Tauri
**sidecar** (`tauri.conf.json` → `bundle.externalBin` =
`["binaries/prometheus"]`). `src/lib.rs` launches that sidecar with
`tauri-plugin-shell` on startup and terminates it when the app exits, so the
installed app needs **no system Python** on `PATH`.

The freeze step is wired into the Tauri build: `tauri.conf.json` →
`beforeBuildCommand` runs `python ../scripts/pre_tauri_build.py`, which builds
the SPA and locates the project Python (preferring `venv`) to write the
sidecar to `src-tauri/binaries/prometheus-x86_64-pc-windows-msvc.exe` (the
target-triple suffix Tauri requires for an `externalBin` sidecar). The
`pre_tauri_build.py` helper resolves the interpreter cross-platform so the same
`beforeBuildCommand` works on Windows and Unix CI hosts.

> **Windows-only packaging.** The installed bundle target is `nsis`
> (`tauri.conf.json` → `bundle.targets`), which is Windows-only. Building the
> installer therefore requires a Windows host with Rust ≥ 1.77, Node 18+,
> Python 3.11+ on `PATH`, Microsoft WebView2 (preinstalled on Windows
> 10/11), **NSIS** (`makensis` on `PATH`), and a `venv` with `pyinstaller`
> installed (created once: `python -m venv venv && pip install -r
> requirements.txt pyinstaller`). The full `cargo tauri build` has been
> verified end-to-end and produces
> `target/release/bundle/nsis/Prometheus_0.6.0_x64-setup.exe`. Linux (AppImage)
> and macOS (dmg) desktop packaging are deferred post-RC1.
