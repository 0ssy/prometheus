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
(`python ../../prometheus.py --server`) when you run `cargo tauri dev`.

## Build the installer

```bash
cd C:\Users\josep\Downloads\prometheus\web && npm run build   # produces ../web/dist
cd src-tauri && cargo tauri build                             # NSIS .exe installer
```

The output installer lands in `src-tauri/target/release/bundle/nsis/`.

## Icons

`icons/` already contains `32x32.png`, `128x128.png`, and `icon.ico`
(generated as placeholders). To use a branded logo:

```bash
cargo tauri icon path/to/logo.png
```

## Shipping the backend with the installer (production)

The web UI talks to the FastAPI backend at `http://localhost:8000`. For a
fully self-contained installer you must bundle the Python runtime as a Tauri
**sidecar** (`tauri.conf.json` → `bundle.externalBin`) and launch it from
`src/lib.rs` with `tauri-plugin-shell`, OR document that `python prometheus.py`
must run alongside the installed app. This step is environment-specific and is
left as a documented follow-up (the sandbox has no Rust toolchain to verify a
full `cargo tauri build`).
